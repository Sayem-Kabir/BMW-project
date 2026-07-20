"""Vector store backends for Module 5A — native Chroma, HTTP Chroma, or local JSON."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np

from ml.assistant.config import (
    COLLECTION_NAME,
    DEFAULT_CHROMA_HOST,
    DEFAULT_CHROMA_PORT,
    DEFAULT_PERSIST_DIR,
)

logger = logging.getLogger(__name__)

TENANT = "default_tenant"
DATABASE = "default_database"


class VectorStoreBackend(ABC):
    backend_name: str

    @abstractmethod
    def reset(self, collection_name: str) -> None: ...

    @abstractmethod
    def add(
        self,
        collection_name: str,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None: ...

    @abstractmethod
    def query(
        self,
        collection_name: str,
        *,
        query_embedding: list[float],
        k: int,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def count(self, collection_name: str) -> int: ...


class LocalJsonVectorStore(VectorStoreBackend):
    """File-backed store for local dev/tests when ``chromadb`` is unavailable."""

    backend_name = "local_json"

    def __init__(self, persist_directory: str | Path) -> None:
        self.root = Path(persist_directory)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, collection_name: str) -> Path:
        return self.root / f"{collection_name}.json"

    def _load(self, collection_name: str) -> dict[str, Any]:
        path = self._path(collection_name)
        if not path.is_file():
            return {"ids": [], "documents": [], "embeddings": [], "metadatas": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, collection_name: str, payload: dict[str, Any]) -> None:
        self._path(collection_name).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    def reset(self, collection_name: str) -> None:
        path = self._path(collection_name)
        if path.exists():
            path.unlink()

    def add(
        self,
        collection_name: str,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        payload = self._load(collection_name)
        payload["ids"].extend(ids)
        payload["documents"].extend(documents)
        payload["embeddings"].extend(embeddings)
        payload["metadatas"].extend(metadatas)
        self._save(collection_name, payload)

    def query(
        self,
        collection_name: str,
        *,
        query_embedding: list[float],
        k: int,
    ) -> list[dict[str, Any]]:
        payload = self._load(collection_name)
        if not payload["embeddings"]:
            return []

        matrix = np.asarray(payload["embeddings"], dtype=float)
        query = np.asarray(query_embedding, dtype=float)
        matrix_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
        query_norm = query / (np.linalg.norm(query) + 1e-9)
        scores = matrix_norm @ query_norm
        top = np.argsort(scores)[::-1][:k]

        hits: list[dict[str, Any]] = []
        for rank in top:
            hits.append(
                {
                    "content": payload["documents"][rank],
                    "metadata": payload["metadatas"][rank],
                    "distance": float(1.0 - scores[rank]),
                }
            )
        return hits

    def count(self, collection_name: str) -> int:
        return len(self._load(collection_name)["ids"])


class ChromaHttpVectorStore(VectorStoreBackend):
    """Chroma v2 REST client — no native ``chromadb`` package required."""

    backend_name = "chroma_http"

    def __init__(self, host: str = DEFAULT_CHROMA_HOST, port: int = DEFAULT_CHROMA_PORT) -> None:
        self.base = f"http://{host}:{port}/api/v2/tenants/{TENANT}/databases/{DATABASE}/collections"
        self._collection_ids: dict[str, str] = {}

    def _request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Chroma HTTP {method} {url} failed: {detail}") from exc

    def _ensure_collection(self, collection_name: str) -> str:
        if collection_name in self._collection_ids:
            return self._collection_ids[collection_name]
        created = self._request(
            "POST",
            self.base,
            {"name": collection_name, "get_or_create": True},
        )
        collection_id = created["id"]
        self._collection_ids[collection_name] = collection_id
        return collection_id

    def reset(self, collection_name: str) -> None:
        if collection_name in self._collection_ids:
            collection_id = self._collection_ids.pop(collection_name)
            try:
                self._request("DELETE", f"{self.base}/{collection_id}")
            except Exception:  # noqa: BLE001
                pass
        self._ensure_collection(collection_name)

    def add(
        self,
        collection_name: str,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        collection_id = self._ensure_collection(collection_name)
        self._request(
            "POST",
            f"{self.base}/{collection_id}/add",
            {
                "ids": ids,
                "documents": documents,
                "embeddings": embeddings,
                "metadatas": metadatas,
            },
        )

    def query(
        self,
        collection_name: str,
        *,
        query_embedding: list[float],
        k: int,
    ) -> list[dict[str, Any]]:
        collection_id = self._ensure_collection(collection_name)
        result = self._request(
            "POST",
            f"{self.base}/{collection_id}/query",
            {"query_embeddings": [query_embedding], "n_results": k},
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            {
                "content": doc,
                "metadata": meta or {},
                "distance": dist,
            }
            for doc, meta, dist in zip(documents, metadatas, distances, strict=False)
        ]

    def count(self, collection_name: str) -> int:
        collection_id = self._ensure_collection(collection_name)
        result = self._request("GET", f"{self.base}/{collection_id}/count")
        return int(result.get("count", 0))


class ChromaNativeVectorStore(VectorStoreBackend):
    backend_name = "chroma_native"

    def __init__(self, persist_directory: str | Path) -> None:
        import chromadb

        path = Path(persist_directory)
        path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(path))

    def reset(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(collection_name)
        except Exception:  # noqa: BLE001
            pass

    def add(
        self,
        collection_name: str,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        collection = self.client.get_or_create_collection(name=collection_name)
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        collection_name: str,
        *,
        query_embedding: list[float],
        k: int,
    ) -> list[dict[str, Any]]:
        collection = self.client.get_collection(collection_name)
        result = collection.query(query_embeddings=[query_embedding], n_results=k)
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            {
                "content": doc,
                "metadata": meta or {},
                "distance": dist,
            }
            for doc, meta, dist in zip(documents, metadatas, distances, strict=False)
        ]

    def count(self, collection_name: str) -> int:
        collection = self.client.get_collection(collection_name)
        return int(collection.count())


def get_vector_store(
    *,
    persist_directory: str | Path | None = None,
    use_http: bool = False,
    chroma_host: str = DEFAULT_CHROMA_HOST,
    chroma_port: int = DEFAULT_CHROMA_PORT,
    prefer_native: bool = True,
) -> VectorStoreBackend:
    if use_http:
        return ChromaHttpVectorStore(host=chroma_host, port=chroma_port)

    if prefer_native:
        try:
            return ChromaNativeVectorStore(persist_directory or DEFAULT_PERSIST_DIR)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Native Chroma unavailable (%s); using local JSON store", exc)

    return LocalJsonVectorStore(persist_directory or DEFAULT_PERSIST_DIR)
