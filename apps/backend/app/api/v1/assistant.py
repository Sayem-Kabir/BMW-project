"""AI Assistant API — Module 5D chat (JSON + SSE) and conversation history."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import FEATURE_ASSISTANT, require_feature
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.common import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
)
from app.services import assistant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assistant", tags=["AI Assistant"])
PHASE = "5G"


def _to_chat_response(payload: dict) -> ChatResponse:
    conversation_id = payload.get("conversation_id")
    vehicle_id = payload.get("vehicle_id")
    return ChatResponse(
        conversation_id=UUID(str(conversation_id)) if conversation_id else None,
        vehicle_id=UUID(str(vehicle_id)) if vehicle_id else None,
        message=str(payload.get("message") or ""),
        reply=str(payload.get("reply") or ""),
        intent=str(payload.get("intent") or ""),
        route=str(payload.get("route") or ""),
        citations=list(payload.get("citations") or []),
        obd_matches=list(payload.get("obd_matches") or []),
        telemetry_context=payload.get("telemetry_context"),
        maintenance_context=payload.get("maintenance_context"),
        conversation_memory=payload.get("conversation_memory"),
        memory_message_count=int(payload.get("memory_message_count") or 0),
        llm_backend=payload.get("llm_backend"),
        llm_model=payload.get("llm_model"),
        warnings=list(payload.get("warnings") or []),
        phase=str(payload.get("phase") or PHASE),
    )


@router.post("/chat")
async def chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_feature(FEATURE_ASSISTANT)),
):
    """Chat with the Module 5C assistant.

    Default ``stream=true`` returns Server-Sent Events. Set ``stream=false``
    for a single JSON ``ChatResponse``.
    """
    try:
        payload = await assistant_service.chat(
            session,
            message=body.message,
            vehicle_id=body.vehicle_id,
            driver_id=body.driver_id,
            conversation_id=body.conversation_id,
            persist=body.persist,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Assistant chat failed")
        raise HTTPException(
            status_code=503,
            detail=f"Assistant unavailable: {exc}",
        ) from exc

    if not body.stream:
        return _to_chat_response(payload)

    async def event_stream():
        meta = {
            "type": "meta",
            "conversation_id": payload.get("conversation_id"),
            "vehicle_id": payload.get("vehicle_id"),
            "intent": payload.get("intent"),
            "route": payload.get("route"),
            "citations": payload.get("citations") or [],
            "llm_backend": payload.get("llm_backend"),
            "llm_model": payload.get("llm_model"),
            "maintenance_context": payload.get("maintenance_context"),
            "memory_message_count": payload.get("memory_message_count") or 0,
            "warnings": payload.get("warnings") or [],
            "phase": PHASE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield f"data: {json.dumps(meta)}\n\n"

        for chunk in assistant_service.chunk_reply_for_sse(str(payload.get("reply") or "")):
            yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"

        done = {
            "type": "done",
            "reply": payload.get("reply"),
            "conversation_id": payload.get("conversation_id"),
            "phase": PHASE,
        }
        yield f"data: {json.dumps(done)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations/{vehicle_id}", response_model=ConversationListResponse)
async def conversations(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    limit: int = Query(20, ge=1, le=100),
    _user: User = Depends(require_feature(FEATURE_ASSISTANT)),
):
    """List recent assistant conversations for one vehicle."""
    warning: str | None = None
    rows = []
    try:
        rows = await assistant_service.list_conversations(session, vehicle_id, limit=limit)
    except Exception:  # noqa: BLE001
        logger.exception("Conversation list failed for %s", vehicle_id)
        warning = "Conversation history unavailable — database connection failed"

    summaries: list[ConversationSummary] = []
    for row in rows:
        messages = list(row.messages or [])
        last_user = next(
            (m.get("content") for m in reversed(messages) if m.get("role") == "user"),
            None,
        )
        last_assistant = next(
            (m.get("content") for m in reversed(messages) if m.get("role") == "assistant"),
            None,
        )
        summaries.append(
            ConversationSummary(
                id=row.id,
                vehicle_id=row.vehicle_id,
                driver_id=row.driver_id,
                started_at=row.started_at,
                message_count=len(messages),
                last_user_message=last_user,
                last_assistant_message=last_assistant,
            )
        )

    return ConversationListResponse(
        vehicle_id=vehicle_id,
        conversations=summaries,
        count=len(summaries),
        phase=PHASE,
        warning=warning,
    )


@router.get("/conversations/detail/{conversation_id}", response_model=ConversationDetailResponse)
async def conversation_detail(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_feature(FEATURE_ASSISTANT)),
):
    """Return one conversation with full message history."""
    try:
        row = await assistant_service.get_conversation(session, conversation_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Conversation detail failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetailResponse(
        id=row.id,
        vehicle_id=row.vehicle_id,
        driver_id=row.driver_id,
        started_at=row.started_at,
        messages=list(row.messages or []),
        phase=PHASE,
    )
