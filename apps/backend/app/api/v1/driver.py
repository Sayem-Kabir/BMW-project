"""Driver monitoring API — Module 1F (real CV pipeline, not Phase 0 scaffolds)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.common import DriverAnalysisResponse, DriverSessionResponse, SafetyEventResponse
from app.services import driver_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/driver", tags=["Driver Monitoring"])


@router.post("/analysis", response_model=DriverAnalysisResponse)
async def analyze_frame(
    file: UploadFile = File(...),
    vehicle_id: str = "test",
    session_id: str = "test",
    persist: bool = False,
    db: AsyncSession = Depends(get_async_session),
):
    """Analyze a single JPEG/PNG frame via the Phase 1 monitoring pipeline."""
    image_bytes = await file.read()
    try:
        raw = await asyncio.to_thread(
            driver_service.analyze_frame_bytes,
            image_bytes,
            vehicle_id=vehicle_id,
            session_id=session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Driver analysis failed")
        raise HTTPException(status_code=503, detail=f"Pipeline unavailable: {exc}") from exc

    payload = driver_service.analysis_to_api_payload(raw)

    if persist:
        try:
            sid = UUID(session_id)
        except ValueError:
            sid = None
        if sid is not None:
            await driver_service.apply_frame_stats(db, sid, payload)

    return DriverAnalysisResponse(**payload)


@router.get("/sessions/{vehicle_id}")
async def list_sessions(
    vehicle_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    sessions = await driver_service.list_sessions_for_vehicle(db, vehicle_id)
    return {
        "vehicle_id": str(vehicle_id),
        "sessions": [DriverSessionResponse.model_validate(s).model_dump() for s in sessions],
        "count": len(sessions),
    }


@router.get("/sessions/{session_id}/detail")
async def session_detail(
    session_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    session, events = await driver_service.get_session_detail(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session": DriverSessionResponse.model_validate(session).model_dump(),
        "events": [SafetyEventResponse.model_validate(e).model_dump() for e in events],
        "event_count": len(events),
    }


@router.websocket("/stream/{vehicle_id}/{session_id}")
async def driver_stream(websocket: WebSocket, vehicle_id: UUID, session_id: UUID):
    """Real-time stream: client sends JPEG bytes, server replies with analysis JSON."""
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "ready",
            "vehicle_id": str(vehicle_id),
            "session_id": str(session_id),
            "message": "Send JPEG frames as binary WebSocket messages.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Optional DB session for stats — obtained lazily per frame via engine
    from app.core.database import async_session_maker

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            frame_bytes: bytes | None = message.get("bytes")
            if frame_bytes is None and message.get("text"):
                # Ignore control/text pings; clients should send binary JPEG
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Expected binary JPEG frame bytes",
                    }
                )
                continue
            if not frame_bytes:
                continue

            try:
                raw = await asyncio.to_thread(
                    driver_service.analyze_frame_bytes,
                    frame_bytes,
                    vehicle_id=str(vehicle_id),
                    session_id=str(session_id),
                )
                payload = driver_service.analysis_to_api_payload(raw)
            except ValueError as exc:
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue
            except Exception as exc:  # noqa: BLE001
                logger.exception("Stream analysis failed")
                await websocket.send_json(
                    {"type": "error", "detail": f"Pipeline unavailable: {exc}"}
                )
                continue

            # Best-effort session stats (ignore if session row does not exist)
            try:
                async with async_session_maker() as db:
                    await driver_service.apply_frame_stats(db, session_id, payload)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Session stats update skipped: %s", exc)

            await websocket.send_json({"type": "analysis", "payload": payload})
    except WebSocketDisconnect:
        return
