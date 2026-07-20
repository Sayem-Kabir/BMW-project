"""Module 4E — safety event persistence and MinIO clip attachment."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping
from uuid import UUID

from app.core import minio as minio_ops
from app.models.event import SafetyEvent
from app.services.clip_encoder import encode_jpeg_sequence_to_mp4
from app.services.video_clip_buffer import VideoClipBuffer

logger = logging.getLogger(__name__)

PHASE = "4E"
CLIP_DURATION_SECONDS = 30.0
DEFAULT_FPS = 30.0

_detector: Any | None = None
_detector_lock = RLock()
_buffers: dict[str, VideoClipBuffer] = {}
_buffers_lock = RLock()


def get_detector() -> Any:
    """Lazy shared Module 4D detector."""
    global _detector
    with _detector_lock:
        if _detector is None:
            from ml.risk_engine import EventDetector

            _detector = EventDetector(fps=DEFAULT_FPS)
        return _detector


def reset_detector() -> None:
    global _detector
    with _detector_lock:
        if _detector is not None:
            _detector.reset()
        _detector = None


def get_clip_buffer(
    vehicle_id: str,
    *,
    duration_seconds: float = CLIP_DURATION_SECONDS,
    fps: float = DEFAULT_FPS,
) -> VideoClipBuffer:
    key = str(vehicle_id)
    with _buffers_lock:
        buffer = _buffers.get(key)
        if buffer is None:
            buffer = VideoClipBuffer(duration_seconds=duration_seconds, fps=fps)
            _buffers[key] = buffer
        return buffer


def reset_clip_buffer(vehicle_id: str) -> None:
    with _buffers_lock:
        _buffers.pop(str(vehicle_id), None)


def append_frame(
    vehicle_id: str,
    frame_bytes: bytes,
    *,
    timestamp: datetime | None = None,
) -> None:
    get_clip_buffer(vehicle_id).append_jpeg(frame_bytes, timestamp=timestamp)


def detect_events(
    vehicle_id: str,
    driver_state: Mapping[str, Any] | None = None,
    road_state: Mapping[str, Any] | None = None,
    telemetry: Mapping[str, Any] | None = None,
    *,
    risk_score: float | None = None,
    timestamp: datetime | None = None,
) -> Any:
    return get_detector().process_frame(
        str(vehicle_id),
        driver_state,
        road_state,
        telemetry,
        risk_score=risk_score,
        timestamp=timestamp,
    )


def build_xai_explanation(detected: Any) -> str:
    from ml.risk_engine.explanations import explain_safety_event

    return explain_safety_event(
        detected.event_type,
        reason=detected.reason,
        evidence=detected.evidence,
        telemetry_snapshot=detected.telemetry_snapshot,
    )


def row_from_detected_event(
    *,
    vehicle_id: UUID | str,
    driver_id: UUID | str,
    detected: Any,
    session_id: UUID | str | None = None,
    evaluated_at: datetime | None = None,
    xai_explanation: str | None = None,
) -> SafetyEvent:
    telemetry = dict(detected.telemetry_snapshot or {})
    moment = evaluated_at or detected.timestamp
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    return SafetyEvent(
        vehicle_id=UUID(str(vehicle_id)),
        driver_id=UUID(str(driver_id)),
        session_id=UUID(str(session_id)) if session_id else None,
        event_type=str(detected.event_type),
        severity=str(detected.severity),
        timestamp=moment,
        latitude=_optional_float(telemetry.get("latitude")),
        longitude=_optional_float(telemetry.get("longitude")),
        telemetry_snapshot=telemetry,
        xai_explanation=xai_explanation or build_xai_explanation(detected),
        acknowledged=False,
    )


def materialize_clip_bytes(
    vehicle_id: str,
    *,
    anchor: datetime | None = None,
    duration_seconds: float = CLIP_DURATION_SECONDS,
    fps: float = DEFAULT_FPS,
) -> bytes | None:
    frames = get_clip_buffer(vehicle_id).collect_clip(
        duration_seconds=duration_seconds,
        anchor=anchor,
    )
    return encode_jpeg_sequence_to_mp4(frames, fps=fps)


def upload_clip_for_event(
    vehicle_id: UUID | str,
    event_id: UUID | str,
    clip_bytes: bytes,
) -> str | None:
    return minio_ops.upload_event_clip(str(vehicle_id), str(event_id), clip_bytes)


async def attach_clip_to_event(
    session: Any,
    event: SafetyEvent,
    clip_bytes: bytes,
) -> str | None:
    url = await asyncio.to_thread(
        upload_clip_for_event,
        event.vehicle_id,
        event.id,
        clip_bytes,
    )
    if url:
        event.video_clip_url = url
        await session.commit()
        await session.refresh(event)
    return url


async def persist_detected_events(
    session: Any,
    *,
    vehicle_id: UUID | str,
    driver_id: UUID | str,
    detection: Any,
    session_id: UUID | str | None = None,
    attach_clips: bool = True,
) -> list[SafetyEvent]:
    """Persist 4D detections as ``safety_events`` rows with XAI text."""
    rows: list[SafetyEvent] = []
    for detected in detection.events:
        row = row_from_detected_event(
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            detected=detected,
            session_id=session_id,
            evaluated_at=detection.timestamp,
        )
        session.add(row)
        rows.append(row)

    if not rows:
        return rows

    await session.commit()
    for row in rows:
        await session.refresh(row)

    if attach_clips:
        clip_bytes = await asyncio.to_thread(
            materialize_clip_bytes,
            str(vehicle_id),
            anchor=detection.timestamp,
        )
        if clip_bytes:
            for row in rows:
                await attach_clip_to_event(session, row, clip_bytes)
        else:
            logger.info(
                "No clip bytes available for vehicle %s (%s events persisted)",
                vehicle_id,
                len(rows),
            )

    return rows


async def detect_and_persist(
    *,
    vehicle_id: UUID | str,
    driver_id: UUID | str,
    driver_state: Mapping[str, Any] | None = None,
    road_state: Mapping[str, Any] | None = None,
    telemetry: Mapping[str, Any] | None = None,
    session_id: UUID | str | None = None,
    risk_score: float | None = None,
    attach_clips: bool = True,
) -> dict[str, Any]:
    """Run 4D detection, persist rows, and optionally upload a 30 s clip."""
    from app.core.database import async_session_maker

    detection = await asyncio.to_thread(
        detect_events,
        str(vehicle_id),
        driver_state,
        road_state,
        telemetry,
        risk_score=risk_score,
    )

    async with async_session_maker() as session:
        rows = await persist_detected_events(
            session,
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            detection=detection,
            session_id=session_id,
            attach_clips=attach_clips,
        )

    return {
        "vehicle_id": str(vehicle_id),
        "driver_id": str(driver_id),
        "session_id": str(session_id) if session_id else None,
        "phase": PHASE,
        "detected": len(detection.events),
        "persisted": len(rows),
        "events": [
            {
                "id": str(row.id),
                "event_type": row.event_type,
                "severity": row.severity,
                "timestamp": row.timestamp.isoformat(),
                "video_clip_url": row.video_clip_url,
                "xai_explanation": row.xai_explanation,
            }
            for row in rows
        ],
        "warnings": list(detection.warnings),
        "skipped_detectors": list(detection.skipped_detectors),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


async def upload_missing_clip(event_id: UUID | str, vehicle_id: UUID | str) -> str | None:
    """Retry clip upload for an existing row (used by Celery post-processing)."""
    from sqlalchemy import select

    from app.core.database import async_session_maker

    clip_bytes = await asyncio.to_thread(materialize_clip_bytes, str(vehicle_id))
    if not clip_bytes:
        return None

    async with async_session_maker() as session:
        result = await session.execute(
            select(SafetyEvent).where(SafetyEvent.id == UUID(str(event_id)))
        )
        event = result.scalar_one_or_none()
        if event is None or event.video_clip_url:
            return event.video_clip_url if event else None
        return await attach_clip_to_event(session, event, clip_bytes)


async def acknowledge_event(
    session: Any,
    event_id: UUID | str,
    *,
    acknowledged_by: UUID | str | None = None,
) -> SafetyEvent:
    from sqlalchemy import select

    result = await session.execute(
        select(SafetyEvent).where(SafetyEvent.id == UUID(str(event_id)))
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise ValueError(f"Safety event {event_id} not found")

    event.acknowledged = True
    event.acknowledged_at = datetime.now(timezone.utc)
    if acknowledged_by is not None:
        event.acknowledged_by = UUID(str(acknowledged_by))
    await session.commit()
    await session.refresh(event)
    return event


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
