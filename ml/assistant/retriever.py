"""Module 5B — RAG retrieval pipeline over the 5A knowledge base.

Pure retrieval (no LLM): classify intent → search vector store → format
cited context for the Phase 5C LangGraph / Ollama response generator.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ml.assistant.config import (
    COLLECTION_NAME,
    DEFAULT_CHROMA_HOST,
    DEFAULT_CHROMA_PORT,
    DEFAULT_DATA_DIR,
    DEFAULT_PERSIST_DIR,
    DEFAULT_TOP_K,
    DISTANCE_SOFT_LIMIT,
    MAX_CONTEXT_CHARS,
)
from ml.assistant.knowledge_base import EmbedFn, search_knowledge

PHASE = "5B"

Intent = str  # vehicle_warning | maintenance_question | obd_code | general_question
Route = str  # rag_with_telemetry | rag_only | direct_response

INTENT_VEHICLE_WARNING = "vehicle_warning"
INTENT_MAINTENANCE = "maintenance_question"
INTENT_OBD = "obd_code"
INTENT_GENERAL = "general_question"

ROUTE_RAG_TELEMETRY = "rag_with_telemetry"
ROUTE_RAG_ONLY = "rag_only"
ROUTE_DIRECT = "direct_response"

_WARNING_TERMS = (
    "warning",
    "light",
    "tire",
    "pressure",
    "tpms",
    "battery",
    "engine",
    "dash",
    "indicator",
    "alert",
)
_MAINTENANCE_TERMS = (
    "oil",
    "service",
    "maintenance",
    "replace",
    "interval",
    "brake",
    "filter",
    "when",
    "schedule",
    "cbs",
)
_OBD_TERMS = ("code", "fault", "error", "dtc", "diagnostic", "obd", "p0", "p1", "p2")
_OBD_CODE_RE = re.compile(r"\b([PBCU]\d{4})\b", re.IGNORECASE)


@dataclass(frozen=True)
class RetrievedChunk:
    content: str
    source_name: str
    source: str
    distance: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    intent: Intent
    route: Route
    chunks: tuple[RetrievedChunk, ...]
    context: str
    citations: tuple[str, ...]
    obd_matches: tuple[dict[str, str], ...] = ()
    warnings: tuple[str, ...] = ()
    phase: str = PHASE

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "route": self.route,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "context": self.context,
            "citations": list(self.citations),
            "obd_matches": list(self.obd_matches),
            "warnings": list(self.warnings),
            "phase": self.phase,
        }


def classify_intent(query: str) -> Intent:
    """Rule-based intent classifier used by the LangGraph entry node."""
    text = query.strip().lower()
    if not text:
        return INTENT_GENERAL

    if _OBD_CODE_RE.search(query) or any(term in text for term in _OBD_TERMS):
        return INTENT_OBD
    if any(term in text for term in _WARNING_TERMS):
        return INTENT_VEHICLE_WARNING
    if any(term in text for term in _MAINTENANCE_TERMS):
        return INTENT_MAINTENANCE
    return INTENT_GENERAL


def route_for_intent(intent: Intent) -> Route:
    """Map intent to the LangGraph route used in Module 07."""
    if intent in {INTENT_VEHICLE_WARNING, INTENT_OBD}:
        return ROUTE_RAG_TELEMETRY
    if intent == INTENT_MAINTENANCE:
        return ROUTE_RAG_ONLY
    return ROUTE_DIRECT


def extract_obd_codes(query: str) -> list[str]:
    return [match.group(1).upper() for match in _OBD_CODE_RE.finditer(query)]


def lookup_obd_codes(
    codes: Sequence[str],
    *,
    obd_path: Path | None = None,
) -> list[dict[str, str]]:
    """Exact OBD code lookup from the demo ``obd2_codes.txt`` knowledge file."""
    path = obd_path or (DEFAULT_DATA_DIR / "obd2_codes.txt")
    if not path.is_file() or not codes:
        return []

    text = path.read_text(encoding="utf-8")
    matches: list[dict[str, str]] = []
    for code in codes:
        pattern = re.compile(
            rf"(?P<entry>{re.escape(code)}\s*—.*?Severity:.*?)(?=\n[PBCU]\d{{4}}\s*—|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        found = pattern.search(text)
        if not found:
            matches.append(
                {
                    "code": code,
                    "entry": f"{code}: not found in local OBD knowledge base.",
                    "found": "false",
                }
            )
            continue
        entry = " ".join(found.group("entry").split())
        matches.append({"code": code, "entry": entry, "found": "true"})
    return matches


def _chunk_from_hit(hit: Mapping[str, Any]) -> RetrievedChunk:
    metadata = dict(hit.get("metadata") or {})
    distance = hit.get("distance")
    distance_f = float(distance) if distance is not None else None
    score = None if distance_f is None else max(0.0, 1.0 - distance_f)
    return RetrievedChunk(
        content=str(hit.get("content") or "").strip(),
        source_name=str(metadata.get("source_name") or metadata.get("source") or "Manual"),
        source=str(metadata.get("source") or ""),
        distance=distance_f,
        metadata=metadata,
        score=score,
    )


def format_context(
    chunks: Sequence[RetrievedChunk],
    *,
    obd_matches: Sequence[Mapping[str, str]] = (),
    max_chars: int = MAX_CONTEXT_CHARS,
) -> tuple[str, tuple[str, ...]]:
    """Build an LLM-ready context string with source citations."""
    sections: list[str] = []
    citations: list[str] = []

    if obd_matches:
        for match in obd_matches:
            label = f"OBD:{match.get('code', 'unknown')}"
            citations.append(label)
            sections.append(f"[Source: {label}]\n{match.get('entry', '')}")

    for chunk in chunks:
        if not chunk.content:
            continue
        citation = chunk.source_name
        if citation not in citations:
            citations.append(citation)
        sections.append(f"[Source: {citation}]\n{chunk.content}")

    if not sections:
        return "", tuple()

    assembled = "\n\n".join(sections)
    if len(assembled) > max_chars:
        assembled = assembled[: max_chars - 3].rstrip() + "..."
    return assembled, tuple(citations)


def retrieve(
    query: str,
    *,
    k: int = DEFAULT_TOP_K,
    persist_directory: str | Path | None = None,
    collection_name: str = COLLECTION_NAME,
    use_http: bool = False,
    chroma_host: str = DEFAULT_CHROMA_HOST,
    chroma_port: int = DEFAULT_CHROMA_PORT,
    embed_fn: EmbedFn | None = None,
    distance_limit: float = DISTANCE_SOFT_LIMIT,
    search_fn: Callable[..., list[dict[str, Any]]] | None = None,
    obd_path: Path | None = None,
) -> RetrievalResult:
    """Run the Module 5B retrieval pipeline for one user query."""
    cleaned = query.strip()
    intent = classify_intent(cleaned)
    route = route_for_intent(intent)
    warnings: list[str] = []

    obd_codes = extract_obd_codes(cleaned)
    obd_matches = lookup_obd_codes(obd_codes, obd_path=obd_path)

    chunks: list[RetrievedChunk] = []
    if cleaned:
        search = search_fn or search_knowledge
        try:
            hits = search(
                cleaned,
                k=k,
                persist_directory=persist_directory,
                collection_name=collection_name,
                use_http=use_http,
                chroma_host=chroma_host,
                chroma_port=chroma_port,
                embed_fn=embed_fn,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Vector search unavailable: {exc}")
            hits = []

        for hit in hits:
            chunk = _chunk_from_hit(hit)
            if not chunk.content:
                continue
            if chunk.distance is not None and chunk.distance > distance_limit:
                continue
            chunks.append(chunk)

    # Promote general questions to RAG when chunks look useful.
    if intent == INTENT_GENERAL and chunks:
        route = ROUTE_RAG_ONLY
    elif intent == INTENT_GENERAL and not chunks:
        warnings.append("No strong RAG matches; route remains direct_response")

    context, citations = format_context(chunks, obd_matches=obd_matches)
    if not context and route != ROUTE_DIRECT:
        warnings.append("No retrieved context; LLM will answer without manual grounding")

    return RetrievalResult(
        query=cleaned,
        intent=intent,
        route=route,
        chunks=tuple(chunks),
        context=context,
        citations=citations,
        obd_matches=tuple(obd_matches),
        warnings=tuple(warnings),
    )


def retrieve_for_prompt(query: str, **kwargs: Any) -> dict[str, Any]:
    """Convenience helper returning a dict ready for LangGraph state merge."""
    result = retrieve(query, **kwargs)
    return {
        "user_query": result.query,
        "intent": result.intent,
        "route": result.route,
        "retrieved_context": result.context,
        "citations": list(result.citations),
        "obd_matches": list(result.obd_matches),
        "warnings": list(result.warnings),
        "phase": PHASE,
    }
