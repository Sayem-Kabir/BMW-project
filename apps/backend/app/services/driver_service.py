"""Orchestrates the Phase 1 driver-monitoring CV pipeline for the API layer."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import SafetyEvent
from app.models.session import DriverSession

logger = logging.getLogger(__name__)

_pipeline: Any | None = None


def _ensure_ml_import_path() -> None:
    """Make `ml.driver_monitoring` importable (repo root locally, `/ml` in Docker)."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[4],  # .../BMW (apps/backend/app/services → repo)
        Path("/"),  # Docker: volume mounts repo ml/ at /ml
    ]
    for root in candidates:
        if (root / "ml" / "driver_monitoring").is_dir():
            root_s = str(root)
            if root_s not in sys.path:
                sys.path.insert(0, root_s)
            return
    # Fallback: ml package contents mounted directly at /ml
    if Path("/ml/driver_monitoring").is_dir() and "/" not in sys.path:
        sys.path.insert(0, "/")


def get_pipeline():
    """Lazy singleton wrapping ml.driver_monitoring.pipeline.get_pipeline."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    _ensure_ml_import_path()
    from ml.driver_monitoring.pipeline import get_pipeline as _ml_get_pipeline

    _pipeline = _ml_get_pipeline()
    return _pipeline


def decode_image_bytes(image_bytes: bytes):
    """Decode JPEG/PNG bytes to BGR ndarray. Raises ValueError if invalid."""
    import cv2
    import numpy as np

    if not image_bytes:
        raise ValueError("Empty image payload")
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode image bytes (expected JPEG/PNG)")
    return frame


def analyze_frame_bytes(
    image_bytes: bytes,
    *,
    vehicle_id: str = "test",
    session_id: str = "test",
) -> dict[str, Any]:
    """Decode + run the monitoring pipeline (sync; call via asyncio.to_thread)."""
    frame = decode_image_bytes(image_bytes)
    return get_pipeline().process_frame(frame, vehicle_id=vehicle_id, session_id=session_id)


def analysis_to_api_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Map pipeline dict → DriverAnalysisResponse-compatible payload."""
    head = result.get("head_pose") or {}
    ear = result.get("ear_value")
    mar = result.get("mar_value")
    return {
        "alertness_score": int(result.get("alertness_score", 100)),
        "risk_level": result.get("risk_level", "LOW"),
        "ear_value": float(ear) if ear is not None else 0.0,
        "mar_value": float(mar) if mar is not None else 0.0,
        "yawn_count": int(result.get("yawn_count", 0)),
        "head_pose": {
            "pitch": float(head.get("pitch", 0.0)),
            "yaw": float(head.get("yaw", 0.0)),
            "roll": float(head.get("roll", 0.0)),
            "distracted": bool(head.get("distracted", False)),
        },
        "phone_detected": bool(result.get("phone_detected", False)),
        "smoking_detected": bool(result.get("smoking_detected", False)),
        "seatbelt_worn": bool(result.get("seatbelt_worn", True)),
        "is_drowsy": bool(result.get("is_drowsy", False)),
        "is_yawning": bool(result.get("is_yawning", False)),
        "face_detected": bool(result.get("face_detected", False)),
        "consecutive_drowsy_frames": int(result.get("consecutive_drowsy_frames", 0)),
        "yolo_model_loaded": bool(result.get("yolo_model_loaded", False)),
        "vehicle_id": result.get("vehicle_id"),
        "session_id": result.get("session_id"),
        "xai_heatmap_url": None,
        "phase": "1",
        "message": "ok",
    }


async def list_sessions_for_vehicle(
    db: AsyncSession, vehicle_id: UUID
) -> list[DriverSession]:
    stmt = (
        select(DriverSession)
        .where(DriverSession.vehicle_id == vehicle_id)
        .order_by(DriverSession.started_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_session_detail(
    db: AsyncSession, session_id: UUID
) -> tuple[DriverSession | None, list[SafetyEvent]]:
    session = await db.get(DriverSession, session_id)
    if session is None:
        return None, []
    events_stmt = (
        select(SafetyEvent)
        .where(SafetyEvent.session_id == session_id)
        .order_by(SafetyEvent.timestamp.desc())
    )
    events_result = await db.execute(events_stmt)
    return session, list(events_result.scalars().all())


async def apply_frame_stats(
    db: AsyncSession, session_id: UUID, analysis: dict[str, Any]
) -> DriverSession | None:
    """Increment frame counters on an existing session row (no-op if missing)."""
    session = await db.get(DriverSession, session_id)
    if session is None:
        return None

    session.total_frames_analyzed = (session.total_frames_analyzed or 0) + 1
    score = float(analysis.get("alertness_score", 100))
    n = session.total_frames_analyzed
    prev_avg = session.alertness_score_avg
    if prev_avg is None:
        session.alertness_score_avg = score
    else:
        session.alertness_score_avg = ((prev_avg * (n - 1)) + score) / n
    if session.alertness_score_min is None:
        session.alertness_score_min = score
    else:
        session.alertness_score_min = min(session.alertness_score_min, score)

    if analysis.get("is_drowsy"):
        session.drowsy_events = (session.drowsy_events or 0) + 1
    if analysis.get("is_yawning"):
        session.yawn_events = (session.yawn_events or 0) + 1
    if analysis.get("phone_detected"):
        session.phone_events = (session.phone_events or 0) + 1
    if analysis.get("yolo_model_loaded") and not analysis.get("seatbelt_worn", True):
        session.seatbelt_events = (session.seatbelt_events or 0) + 1
    head = analysis.get("head_pose") or {}
    if head.get("distracted"):
        session.headpose_events = (session.headpose_events or 0) + 1

    await db.commit()
    await db.refresh(session)
    return session
