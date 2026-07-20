"""Module 5A — PDF/text ingestion and ChromaDB vector indexing for RAG."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from ml.assistant.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DEFAULT_CHROMA_HOST,
    DEFAULT_CHROMA_PORT,
    DEFAULT_DATA_DIR,
    DEFAULT_DOCUMENTS,
    DEFAULT_PERSIST_DIR,
    EMBEDDING_MODEL,
    OPTIONAL_PDF,
)
from ml.assistant.vector_store import get_vector_store

logger = logging.getLogger(__name__)

PHASE = "5A"
EmbedFn = Callable[[list[str]], list[list[float]]]


@dataclass(frozen=True)
class RawDocument:
    content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class KnowledgeChunk:
    content: str
    metadata: dict[str, Any]

    @property
    def chunk_id(self) -> str:
        source = str(self.metadata.get("source", "unknown"))
        index = int(self.metadata.get("chunk_index", 0))
        digest = hashlib.sha1(f"{source}:{index}:{self.content[:64]}".encode()).hexdigest()[:12]
        return f"chunk_{digest}"


@dataclass(frozen=True)
class BuildResult:
    documents_loaded: int
    chunks_indexed: int
    collection_name: str
    persist_directory: str
    sources: tuple[str, ...]
    embedding_model: str
    backend: str
    phase: str = PHASE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_document_paths(*, include_optional_pdf: bool = True) -> list[Path]:
    paths: list[Path] = []
    for path in DEFAULT_DOCUMENTS:
        if path.is_file():
            paths.append(path)
    if include_optional_pdf and OPTIONAL_PDF.is_file():
        paths.append(OPTIONAL_PDF)
    return paths


def resolve_document_paths(
    document_paths: Sequence[str | Path] | None = None,
    *,
    include_optional_pdf: bool = True,
) -> list[Path]:
    if document_paths is None:
        resolved = default_document_paths(include_optional_pdf=include_optional_pdf)
    else:
        resolved = [Path(path) for path in document_paths]
    missing = [str(path) for path in resolved if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Knowledge documents not found: {', '.join(missing)}")
    return resolved


def _load_pdf(path: Path) -> list[RawDocument]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    docs: list[RawDocument] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        docs.append(
            RawDocument(
                content=text,
                metadata={
                    "source": str(path),
                    "source_name": path.name,
                    "doc_type": "pdf",
                    "page": page_number,
                },
            )
        )
    return docs


def _load_text(path: Path) -> list[RawDocument]:
    content = path.read_text(encoding="utf-8")
    return [
        RawDocument(
            content=content,
            metadata={
                "source": str(path),
                "source_name": path.name,
                "doc_type": path.suffix.lstrip(".").lower() or "text",
            },
        )
    ]


def load_documents(document_paths: Sequence[str | Path]) -> list[RawDocument]:
    docs: list[RawDocument] = []
    for path in resolve_document_paths(document_paths):
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            loaded = _load_pdf(path)
        elif suffix in {".txt", ".md", ".csv"}:
            loaded = _load_text(path)
        else:
            raise ValueError(f"Unsupported document type: {path}")
        docs.extend(loaded)
        logger.info("Loaded %s section(s) from %s", len(loaded), path.name)
    return docs


def _split_text(text: str, separators: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    separator = separators[0] if separators else ""
    splits: list[str] = []
    if separator and separator in text:
        parts = text.split(separator)
    else:
        parts = [text]

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= chunk_size:
            splits.append(part)
            continue
        if len(separators) > 1:
            splits.extend(_split_text(part, separators[1:], chunk_size, chunk_overlap))
        else:
            for start in range(0, len(part), chunk_size - chunk_overlap):
                splits.append(part[start : start + chunk_size])

    merged: list[str] = []
    buffer = ""
    for piece in splits:
        candidate = f"{buffer}{separator}{piece}".strip() if buffer else piece
        if len(candidate) <= chunk_size:
            buffer = candidate
        else:
            if buffer:
                merged.append(buffer)
            buffer = piece
    if buffer:
        merged.append(buffer)
    return merged


def chunk_documents(
    documents: Sequence[RawDocument],
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[KnowledgeChunk]:
    separators = ["\n\n", "\n", ". ", " "]
    chunks: list[KnowledgeChunk] = []
    index = 0
    for doc in documents:
        pieces = _split_text(doc.content, separators, chunk_size, chunk_overlap)
        for piece in pieces:
            if not piece.strip():
                continue
            metadata = dict(doc.metadata)
            metadata["chunk_index"] = index
            chunks.append(KnowledgeChunk(content=piece, metadata=metadata))
            index += 1
    return chunks


def _transformers_embedding_function(model_name: str, *, device: str = "cpu") -> EmbedFn:
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    if device != "cpu" and torch.cuda.is_available():
        model = model.to(device)
    else:
        device = "cpu"

    def embed(texts: list[str]) -> list[list[float]]:
        encoded = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        if device != "cpu":
            encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            outputs = model(**encoded)
            pooled = outputs.last_hidden_state.mean(dim=1)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return [row.tolist() for row in pooled.cpu()]

    return embed


def get_embedding_function(model_name: str = EMBEDDING_MODEL, *, device: str = "cpu") -> EmbedFn:
    import os

    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("USE_TF", "0")

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name, device=device)

        def embed(texts: list[str]) -> list[list[float]]:
            vectors = model.encode(texts, normalize_embeddings=True)
            return [vector.tolist() for vector in vectors]

        return embed
    except Exception as exc:  # noqa: BLE001 — fall back when ST/transformers stack is broken
        logger.warning("sentence-transformers unavailable (%s); using transformers fallback", exc)
        return _transformers_embedding_function(model_name, device=device)


def build_knowledge_base(
    document_paths: Sequence[str | Path] | None = None,
    *,
    persist_directory: str | Path | None = None,
    collection_name: str = COLLECTION_NAME,
    use_http: bool = False,
    chroma_host: str = DEFAULT_CHROMA_HOST,
    chroma_port: int = DEFAULT_CHROMA_PORT,
    reset: bool = False,
    embedding_device: str = "cpu",
    include_optional_pdf: bool = True,
    embed_fn: EmbedFn | None = None,
) -> BuildResult:
    paths = resolve_document_paths(document_paths, include_optional_pdf=include_optional_pdf)
    documents = load_documents(paths)
    chunks = chunk_documents(documents)
    if not chunks:
        raise ValueError("No chunks produced from input documents")

    store = get_vector_store(
        persist_directory=persist_directory,
        use_http=use_http,
        chroma_host=chroma_host,
        chroma_port=chroma_port,
    )
    if reset:
        store.reset(collection_name)

    embed = embed_fn or get_embedding_function(device=embedding_device)
    texts = [chunk.content for chunk in chunks]
    embeddings = embed(texts)
    store.add(
        collection_name,
        ids=[chunk.chunk_id for chunk in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[chunk.metadata for chunk in chunks],
    )

    persist_path = Path(persist_directory or DEFAULT_PERSIST_DIR)
    location = str(persist_path if not use_http else f"{chroma_host}:{chroma_port}")
    result = BuildResult(
        documents_loaded=len(documents),
        chunks_indexed=len(chunks),
        collection_name=collection_name,
        persist_directory=location,
        sources=tuple(sorted({str(path) for path in paths})),
        embedding_model=EMBEDDING_MODEL,
        backend=store.backend_name,
    )
    logger.info(
        "Indexed %s chunks via %s into %s",
        result.chunks_indexed,
        result.backend,
        result.collection_name,
    )
    return result


def search_knowledge(
    query: str,
    *,
    k: int = 4,
    persist_directory: str | Path | None = None,
    collection_name: str = COLLECTION_NAME,
    use_http: bool = False,
    chroma_host: str = DEFAULT_CHROMA_HOST,
    chroma_port: int = DEFAULT_CHROMA_PORT,
    embed_fn: EmbedFn | None = None,
) -> list[dict[str, Any]]:
    store = get_vector_store(
        persist_directory=persist_directory,
        use_http=use_http,
        chroma_host=chroma_host,
        chroma_port=chroma_port,
    )
    embed = embed_fn or get_embedding_function()
    query_vector = embed([query])[0]
    return store.query(collection_name, query_embedding=query_vector, k=k)


def collection_stats(
    *,
    persist_directory: str | Path | None = None,
    collection_name: str = COLLECTION_NAME,
    use_http: bool = False,
    chroma_host: str = DEFAULT_CHROMA_HOST,
    chroma_port: int = DEFAULT_CHROMA_PORT,
) -> dict[str, Any]:
    store = get_vector_store(
        persist_directory=persist_directory,
        use_http=use_http,
        chroma_host=chroma_host,
        chroma_port=chroma_port,
    )
    try:
        count = store.count(collection_name)
    except Exception as exc:  # noqa: BLE001
        return {
            "collection_name": collection_name,
            "count": 0,
            "available": False,
            "backend": store.backend_name,
            "error": str(exc),
            "phase": PHASE,
        }
    return {
        "collection_name": collection_name,
        "count": count,
        "available": count > 0,
        "backend": store.backend_name,
        "phase": PHASE,
    }


if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Build Module 5A vehicle knowledge base")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--http", action="store_true")
    parser.add_argument("--host", default=DEFAULT_CHROMA_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_CHROMA_PORT)
    args = parser.parse_args()

    doc_paths = [
        path
        for path in (
            args.data_dir / "bmw_owner_manual.txt",
            args.data_dir / "obd2_codes.txt",
            args.data_dir / "service_intervals.txt",
            args.data_dir / "bmw_owner_manual.pdf",
        )
        if path.is_file()
    ]
    if not doc_paths:
        raise SystemExit(f"No documents found in {args.data_dir}")

    build = build_knowledge_base(
        doc_paths,
        persist_directory=args.persist_dir,
        use_http=args.http,
        chroma_host=args.host,
        chroma_port=args.port,
        reset=args.reset,
        include_optional_pdf=False,
    )
    print(json.dumps(build.to_dict(), indent=2))
