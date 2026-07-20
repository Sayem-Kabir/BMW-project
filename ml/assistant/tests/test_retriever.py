"""Module 5B RAG retrieval pipeline tests."""

from __future__ import annotations

from pathlib import Path

from ml.assistant.knowledge_base import build_knowledge_base, resolve_document_paths
from ml.assistant.retriever import (
    INTENT_MAINTENANCE,
    INTENT_OBD,
    INTENT_VEHICLE_WARNING,
    ROUTE_RAG_ONLY,
    ROUTE_RAG_TELEMETRY,
    classify_intent,
    extract_obd_codes,
    format_context,
    lookup_obd_codes,
    retrieve,
    retrieve_for_prompt,
    route_for_intent,
)
from ml.assistant.retriever import RetrievedChunk


def _fake_embed(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        lowered = text.lower()
        # Bias dimensions so TPMS/OBD/maintenance queries land near matching docs.
        base = [0.0] * 8
        base[0] = float(sum(ord(c) for c in lowered) % 17)
        if "tpms" in lowered or "tire" in lowered or "pressure" in lowered:
            base[1] = 10.0
        if "p0420" in lowered or "catalyst" in lowered or "obd" in lowered:
            base[2] = 10.0
        if "service" in lowered or "maintenance" in lowered or "interval" in lowered:
            base[3] = 10.0
        vectors.append(base)
    return vectors


def test_classify_intent_and_routes() -> None:
    assert classify_intent("Why is my TPMS warning light on?") == INTENT_VEHICLE_WARNING
    assert route_for_intent(INTENT_VEHICLE_WARNING) == ROUTE_RAG_TELEMETRY

    assert classify_intent("When should I replace brake fluid?") == INTENT_MAINTENANCE
    assert route_for_intent(INTENT_MAINTENANCE) == ROUTE_RAG_ONLY

    assert classify_intent("What does P0420 mean?") == INTENT_OBD
    assert route_for_intent(INTENT_OBD) == ROUTE_RAG_TELEMETRY


def test_obd_lookup_extracts_and_matches() -> None:
    codes = extract_obd_codes("Scanner shows P0420 and p0300")
    assert codes == ["P0420", "P0300"]
    matches = lookup_obd_codes(codes)
    assert matches[0]["found"] == "true"
    assert "Catalyst" in matches[0]["entry"]
    assert matches[1]["found"] == "true"


def test_format_context_includes_citations() -> None:
    chunks = [
        RetrievedChunk(
            content="TPMS monitors tire inflation pressure.",
            source_name="bmw_owner_manual.txt",
            source="data/bmw_owner_manual.txt",
            distance=0.2,
            score=0.8,
        )
    ]
    context, citations = format_context(
        chunks,
        obd_matches=[{"code": "P0420", "entry": "P0420 — Catalyst issue", "found": "true"}],
    )
    assert "bmw_owner_manual.txt" in citations
    assert "OBD:P0420" in citations
    assert "[Source: bmw_owner_manual.txt]" in context
    assert "TPMS" in context


def test_retrieve_pipeline_with_temp_index(tmp_path: Path) -> None:
    paths = resolve_document_paths(None, include_optional_pdf=False)
    persist_dir = tmp_path / "chroma"
    build_knowledge_base(
        paths,
        persist_directory=persist_dir,
        reset=True,
        include_optional_pdf=False,
        embed_fn=_fake_embed,
    )

    result = retrieve(
        "Why is my tire pressure warning on?",
        persist_directory=persist_dir,
        embed_fn=_fake_embed,
        k=3,
    )
    assert result.intent == INTENT_VEHICLE_WARNING
    assert result.route == ROUTE_RAG_TELEMETRY
    assert result.chunks
    assert result.context
    assert result.citations
    assert result.phase == "5B"

    prompt_state = retrieve_for_prompt(
        "What does fault code P0420 mean?",
        persist_directory=persist_dir,
        embed_fn=_fake_embed,
    )
    assert prompt_state["intent"] == INTENT_OBD
    assert prompt_state["obd_matches"]
    assert "retrieved_context" in prompt_state
