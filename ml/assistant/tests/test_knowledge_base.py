"""Module 5A knowledge base tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ml.assistant.knowledge_base import (
    BuildResult,
    build_knowledge_base,
    chunk_documents,
    collection_stats,
    default_document_paths,
    load_documents,
    resolve_document_paths,
    search_knowledge,
)


def _fake_embed(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        seed = sum(ord(char) for char in text) % 997
        vectors.append([float((seed + index) % 13) for index in range(8)])
    return vectors


def test_default_documents_exist() -> None:
    paths = default_document_paths(include_optional_pdf=False)
    assert len(paths) >= 3
    assert all(path.is_file() for path in paths)


def test_load_and_chunk_demo_documents() -> None:
    paths = resolve_document_paths(None, include_optional_pdf=False)
    docs = load_documents(paths)
    chunks = chunk_documents(docs)

    assert len(docs) >= 3
    assert len(chunks) > len(docs)
    assert all(chunk.metadata.get("source_name") for chunk in chunks)


def test_build_and_search_with_fake_embeddings(tmp_path: Path) -> None:
    paths = resolve_document_paths(None, include_optional_pdf=False)
    persist_dir = tmp_path / "chroma"

    result = build_knowledge_base(
        paths,
        persist_directory=persist_dir,
        reset=True,
        include_optional_pdf=False,
        embed_fn=_fake_embed,
    )
    hits = search_knowledge(
        "TPMS tire pressure warning",
        k=2,
        persist_directory=persist_dir,
        embed_fn=_fake_embed,
    )

    assert isinstance(result, BuildResult)
    assert result.chunks_indexed > 0
    assert result.documents_loaded >= 3
    assert len(hits) >= 1

    stats = collection_stats(persist_directory=persist_dir)
    assert stats["available"] is True
    assert stats["count"] > 0


def test_missing_document_raises() -> None:
    with pytest.raises(FileNotFoundError):
        resolve_document_paths(["data/does_not_exist.txt"])
