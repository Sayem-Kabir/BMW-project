"""Module 5D/5F — assistant chat service over RAG + telemetry + maintenance context."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assistant import AssistantConversation
from app.models.maintenance import MaintenancePrediction

logger = logging.getLogger(__name__)

PHASE = "5G"
DEFAULT_VEHICLE_ID = UUID("00000000-0000-4000-8000-000000000003")


def _ensure_repo_on_path() -> None:
    for idx in (4, 3, 2):
        try:
            candidate = Path(__file__).resolve().parents[idx]
        except IndexError:
            continue
        if (candidate / "ml").is_dir():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return


def _serialize_prediction(row: MaintenancePrediction) -> dict[str, Any]:
    explanation = row.shap_explanation if isinstance(row.shap_explanation, dict) else {}
    return {
        "component": row.component,
        "health_score": row.health_score,
        "anomaly_score": row.anomaly_score,
        "confidence": row.confidence,
        "predicted_remaining_km": row.predicted_remaining_km,
        "predicted_replacement_date": (
            row.predicted_replacement_date.isoformat()
            if row.predicted_replacement_date
            else None
        ),
        "severity": explanation.get("severity"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "shap_explanation": explanation,
    }


async def load_latest_maintenance(
    session: AsyncSession | None,
    vehicle_id: UUID,
) -> list[dict[str, Any]]:
    """Latest persisted prediction per component for one vehicle."""
    if session is None:
        return []
    try:
        result = await session.execute(
            select(MaintenancePrediction)
            .where(MaintenancePrediction.vehicle_id == vehicle_id)
            .order_by(MaintenancePrediction.created_at.desc())
            .limit(50)
        )
        latest: dict[str, MaintenancePrediction] = {}
        for row in result.scalars().all():
            latest.setdefault(row.component, row)
        return [_serialize_prediction(row) for row in latest.values()]
    except Exception:  # noqa: BLE001
        logger.exception("Failed to load maintenance context for %s", vehicle_id)
        return []


def run_assistant_sync(
    message: str,
    *,
    vehicle_id: str,
    maintenance_rows: list[dict[str, Any]] | None = None,
    prior_messages: list[dict[str, Any]] | None = None,
    allow_fallback_llm: bool = True,
) -> dict[str, Any]:
    """Blocking 5C–5G invocation — run via ``asyncio.to_thread`` from API handlers."""
    _ensure_repo_on_path()
    from ml.assistant.agent import ask_assistant

    rows = list(maintenance_rows or [])

    def _maintenance_fn(_vid: str):
        return rows or None

    state = ask_assistant(
        message,
        vehicle_id=vehicle_id,
        allow_fallback_llm=allow_fallback_llm,
        maintenance_fn=_maintenance_fn if rows else None,
        use_demo_maintenance=not rows,
        prior_messages=prior_messages,
    )
    return state.to_dict()


async def run_assistant(
    message: str,
    *,
    vehicle_id: UUID | str | None = None,
    maintenance_rows: list[dict[str, Any]] | None = None,
    prior_messages: list[dict[str, Any]] | None = None,
    allow_fallback_llm: bool = True,
) -> dict[str, Any]:
    vid = str(vehicle_id or DEFAULT_VEHICLE_ID)
    return await asyncio.to_thread(
        run_assistant_sync,
        message,
        vehicle_id=vid,
        maintenance_rows=maintenance_rows,
        prior_messages=prior_messages,
        allow_fallback_llm=allow_fallback_llm,
    )


def _message_entry(role: str, content: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "id": str(uuid4()),
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(extra)
    return payload


async def persist_turn(
    session: AsyncSession,
    *,
    vehicle_id: UUID | None,
    driver_id: UUID | None,
    conversation_id: UUID | None,
    user_message: str,
    assistant_payload: dict[str, Any],
) -> AssistantConversation | None:
    """Append one user/assistant turn to ``assistant_conversations``."""
    try:
        row: AssistantConversation | None = None
        if conversation_id is not None:
            result = await session.execute(
                select(AssistantConversation).where(AssistantConversation.id == conversation_id)
            )
            row = result.scalar_one_or_none()

        if row is None:
            row = AssistantConversation(
                id=uuid4(),
                vehicle_id=vehicle_id,
                driver_id=driver_id,
                messages=[],
            )
            session.add(row)

        messages = list(row.messages or [])
        messages.append(_message_entry("user", user_message))
        messages.append(
            _message_entry(
                "assistant",
                str(assistant_payload.get("final_response") or ""),
                intent=assistant_payload.get("intent"),
                route=assistant_payload.get("route"),
                citations=list(assistant_payload.get("citations") or []),
                llm_backend=assistant_payload.get("llm_backend"),
                llm_model=assistant_payload.get("llm_model"),
                maintenance_context=assistant_payload.get("maintenance_context"),
            )
        )
        row.messages = messages
        if vehicle_id is not None:
            row.vehicle_id = vehicle_id
        if driver_id is not None:
            row.driver_id = driver_id
        await session.commit()
        await session.refresh(row)
        return row
    except Exception:  # noqa: BLE001
        logger.exception("Failed to persist assistant conversation")
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None


async def chat(
    session: AsyncSession | None,
    *,
    message: str,
    vehicle_id: UUID | None = None,
    driver_id: UUID | None = None,
    conversation_id: UUID | None = None,
    persist: bool = True,
    allow_fallback_llm: bool = True,
) -> dict[str, Any]:
    if not message.strip():
        raise ValueError("message must not be empty")

    from app.services import guardrails

    blocked = guardrails.check_input(message)
    if blocked:
        return {
            "conversation_id": str(conversation_id) if conversation_id else None,
            "vehicle_id": str(vehicle_id) if vehicle_id else None,
            "message": message.strip(),
            "reply": str(blocked.get("reply") or guardrails.REFUSAL),
            "intent": "refused",
            "route": "guardrail",
            "citations": [],
            "obd_matches": [],
            "telemetry_context": None,
            "maintenance_context": None,
            "conversation_memory": None,
            "memory_message_count": 0,
            "llm_backend": "guardrail",
            "llm_model": None,
            "warnings": [f"guardrail:{blocked.get('reason')}"],
            "phase": "11D",
        }

    vid = vehicle_id or DEFAULT_VEHICLE_ID
    stripped = message.strip()

    from app.core.config import settings
    from app.services.semantic_cache import get_cache

    cache = get_cache(
        threshold=settings.assistant_semantic_cache_threshold,
        ttl_sec=float(settings.assistant_semantic_cache_ttl_sec),
    )
    cached = cache.lookup(stripped)
    if cached is not None:
        return {
            **cached,
            "conversation_id": cached.get("conversation_id")
            or (str(conversation_id) if conversation_id else None),
            "vehicle_id": str(vid),
            "message": stripped,
            "phase": "13",
        }

    maintenance_rows = await load_latest_maintenance(session, vid)

    prior_messages: list[dict[str, Any]] = []
    if conversation_id is not None and session is not None:
        existing = await get_conversation(session, conversation_id)
        if existing is not None:
            prior_messages = list(existing.messages or [])

    assistant_payload = await run_assistant(
        stripped,
        vehicle_id=vid,
        maintenance_rows=maintenance_rows,
        prior_messages=prior_messages,
        allow_fallback_llm=allow_fallback_llm,
    )

    raw_reply = str(assistant_payload.get("final_response") or "")
    safe_reply, gw = guardrails.filter_output(raw_reply)
    assistant_payload["final_response"] = safe_reply

    conversation: AssistantConversation | None = None
    persist_warning: str | None = None
    if persist and session is not None:
        conversation = await persist_turn(
            session,
            vehicle_id=vid,
            driver_id=driver_id,
            conversation_id=conversation_id,
            user_message=stripped,
            assistant_payload=assistant_payload,
        )
        if conversation is None:
            persist_warning = "Conversation persistence unavailable"

    warnings = list(assistant_payload.get("warnings") or [])
    warnings.extend(gw)
    if persist_warning:
        warnings.append(persist_warning)
    if not maintenance_rows:
        warnings.append("No persisted maintenance predictions — demo/maintenance context may be used")

    result = {
        "conversation_id": str(conversation.id) if conversation else (
            str(conversation_id) if conversation_id else None
        ),
        "vehicle_id": str(vid),
        "message": stripped,
        "reply": safe_reply,
        "intent": str(assistant_payload.get("intent") or ""),
        "route": str(assistant_payload.get("route") or ""),
        "citations": list(assistant_payload.get("citations") or []),
        "obd_matches": list(assistant_payload.get("obd_matches") or []),
        "telemetry_context": assistant_payload.get("telemetry_context"),
        "maintenance_context": assistant_payload.get("maintenance_context"),
        "conversation_memory": assistant_payload.get("conversation_memory"),
        "memory_message_count": int(assistant_payload.get("memory_message_count") or 0),
        "llm_backend": assistant_payload.get("llm_backend"),
        "llm_model": assistant_payload.get("llm_model"),
        "warnings": warnings,
        "phase": PHASE,
        "semantic_cache": {"hit": False, "phase": "13"},
    }
    cache.store(stripped, result)
    return result


async def list_conversations(
    session: AsyncSession,
    vehicle_id: UUID,
    *,
    limit: int = 20,
) -> list[AssistantConversation]:
    result = await session.execute(
        select(AssistantConversation)
        .where(AssistantConversation.vehicle_id == vehicle_id)
        .order_by(AssistantConversation.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_conversation(
    session: AsyncSession,
    conversation_id: UUID,
) -> AssistantConversation | None:
    result = await session.execute(
        select(AssistantConversation).where(AssistantConversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


def chunk_reply_for_sse(reply: str, *, chunk_size: int = 48) -> list[str]:
    """Split a completed reply into SSE-friendly text chunks."""
    text = reply.strip()
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
