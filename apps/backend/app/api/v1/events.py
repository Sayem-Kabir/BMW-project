"""Safety Events API — Module 4F detect/persist, list, acknowledge, and Celery jobs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.event import SafetyEvent
from app.schemas.common import (
    EventAcknowledgeRequest,
    EventDetectRequest,
    EventDetectResponse,
    EventListResponse,
    EventSummary,
    SafetyEventResponse,
)
from app.services import event_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["Safety Events"])
PHASE = "4F"


@router.post("/{vehicle_id}/detect", response_model=EventDetectResponse)
async def detect_events(vehicle_id: UUID, request: EventDetectRequest):
    """Run Module 4D detection and persist safety events (Module 4E)."""
    try:
        payload = await event_service.detect_and_persist(
            vehicle_id=vehicle_id,
            driver_id=request.driver_id,
            driver_state=request.driver_state,
            road_state=request.road_state,
            telemetry=request.telemetry,
            session_id=request.session_id,
            risk_score=request.risk_score,
            attach_clips=request.attach_clips,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Safety event detection failed")
        raise HTTPException(
            status_code=503,
            detail=f"Event detector unavailable: {exc}",
        ) from exc

    if request.enqueue_clip_retry:
        from app.tasks.events import post_process_event

        for event in payload.get("events", []):
            if not event.get("video_clip_url"):
                try:
                    post_process_event.delay(event["id"], str(vehicle_id))
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Clip retry enqueue skipped for %s (Celery/Redis unavailable): %s",
                        event["id"],
                        exc,
                    )

    return EventDetectResponse(
        vehicle_id=vehicle_id,
        driver_id=request.driver_id,
        session_id=request.session_id,
        detected=int(payload.get("detected", 0)),
        persisted=int(payload.get("persisted", 0)),
        events=[
            EventSummary(
                id=UUID(event["id"]),
                event_type=event["event_type"],
                severity=event["severity"],
                timestamp=datetime.fromisoformat(event["timestamp"]),
                video_clip_url=event.get("video_clip_url"),
                xai_explanation=event.get("xai_explanation"),
            )
            for event in payload.get("events", [])
        ],
        warnings=list(payload.get("warnings") or []),
        skipped_detectors=list(payload.get("skipped_detectors") or []),
        completed_at=datetime.fromisoformat(payload["completed_at"]),
        phase=PHASE,
    )


@router.post("/{vehicle_id}/trigger")
async def trigger_event_detection(vehicle_id: UUID, request: EventDetectRequest):
    """Queue one background 4D/4E detection run through Celery."""
    from app.tasks.events import detect_and_persist_events

    try:
        task = detect_and_persist_events.delay(
            vehicle_id=str(vehicle_id),
            driver_id=str(request.driver_id),
            driver_state=dict(request.driver_state),
            road_state=dict(request.road_state),
            telemetry=dict(request.telemetry),
            session_id=str(request.session_id) if request.session_id else None,
            risk_score=request.risk_score,
            attach_clips=request.attach_clips,
            enqueue_clip_retry=request.enqueue_clip_retry,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Event task enqueue failed")
        raise HTTPException(
            status_code=503,
            detail=f"Celery broker unavailable: {exc}",
        ) from exc
    return {
        "vehicle_id": str(vehicle_id),
        "task_id": task.id,
        "status": "queued",
        "phase": PHASE,
    }


@router.post("/{vehicle_id}/frame")
async def append_event_frame(vehicle_id: UUID, file: UploadFile = File(...)):
    """Append one JPEG frame to the rolling 30 s clip buffer for a vehicle."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="frame file must not be empty")
    event_service.append_frame(str(vehicle_id), data)
    return {
        "vehicle_id": str(vehicle_id),
        "buffered_frames": len(event_service.get_clip_buffer(str(vehicle_id))),
        "phase": PHASE,
    }


@router.get("/detail/{event_id}", response_model=SafetyEventResponse | None)
async def event_detail(event_id: UUID, session: AsyncSession = Depends(get_async_session)):
    try:
        result = await session.execute(
            select(SafetyEvent).where(SafetyEvent.id == event_id)
        )
        return result.scalar_one_or_none()
    except Exception:  # noqa: BLE001
        logger.exception("Event detail query failed")
        raise HTTPException(
            status_code=503,
            detail="Safety events database unavailable",
        ) from None


@router.post("/detail/{event_id}/acknowledge", response_model=SafetyEventResponse)
async def acknowledge_event(
    event_id: UUID,
    request: EventAcknowledgeRequest,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        row = await event_service.acknowledge_event(
            session,
            event_id,
            acknowledged_by=request.driver_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:  # noqa: BLE001
        logger.exception("Event acknowledge failed")
        raise HTTPException(
            status_code=503,
            detail="Safety events database unavailable",
        ) from None
    return row


@router.get("/{vehicle_id}", response_model=EventListResponse)
async def list_events(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    limit: int = 100,
    severity: str | None = None,
    acknowledged: bool | None = None,
):
    limit = max(1, min(int(limit), 500))
    warning: str | None = None
    rows: list[SafetyEvent] = []
    try:
        query = (
            select(SafetyEvent)
            .where(SafetyEvent.vehicle_id == vehicle_id)
            .order_by(SafetyEvent.timestamp.desc())
            .limit(limit)
        )
        if severity:
            query = query.where(SafetyEvent.severity == severity.upper())
        if acknowledged is not None:
            query = query.where(SafetyEvent.acknowledged.is_(acknowledged))
        result = await session.execute(query)
        rows = list(result.scalars().all())
    except Exception:  # noqa: BLE001
        logger.exception("Event list query failed for %s", vehicle_id)
        warning = "Safety events unavailable — database connection failed"

    return EventListResponse(
        vehicle_id=vehicle_id,
        events=rows,
        count=len(rows),
        warning=warning,
        phase=PHASE,
    )


@router.get("/{vehicle_id}/export")
async def export_events(vehicle_id: UUID, session: AsyncSession = Depends(get_async_session)):
    try:
        result = await session.execute(
            select(SafetyEvent).where(SafetyEvent.vehicle_id == vehicle_id)
        )
        events = result.scalars().all()
    except Exception:  # noqa: BLE001
        logger.exception("Event export failed for %s", vehicle_id)
        raise HTTPException(
            status_code=503,
            detail="Safety events database unavailable",
        ) from None

    lines = [
        "event_id,event_type,severity,timestamp,acknowledged,video_clip_url"
    ]
    for event in events:
        lines.append(
            f"{event.id},{event.event_type},{event.severity},"
            f"{event.timestamp.isoformat()},{event.acknowledged},"
            f"{event.video_clip_url or ''}"
        )
    return PlainTextResponse("\n".join(lines), media_type="text/csv")
