from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.events.post_process_event")
def post_process_event(event_id: str, vehicle_id: str) -> dict:
    """Background clip upload/retry for a persisted safety event (Module 4E/4F)."""
    from app.services import event_service

    url = asyncio.run(event_service.upload_missing_clip(event_id, vehicle_id))
    return {
        "status": "ok" if url else "skipped",
        "event_id": event_id,
        "vehicle_id": vehicle_id,
        "video_clip_url": url,
        "phase": "4F",
    }


@celery_app.task(name="app.tasks.events.detect_and_persist_events")
def detect_and_persist_events(
    vehicle_id: str | None = None,
    driver_id: str | None = None,
    driver_state: dict[str, Any] | None = None,
    road_state: dict[str, Any] | None = None,
    telemetry: dict[str, Any] | None = None,
    session_id: str | None = None,
    risk_score: float | None = None,
    attach_clips: bool = True,
    enqueue_clip_retry: bool = False,
) -> dict:
    """Run Module 4D detection and persist safety events through the 4E service."""
    if not vehicle_id:
        return {
            "status": "skipped",
            "vehicle_id": vehicle_id,
            "reason": "vehicle_id is required",
        }
    if not driver_id:
        return {
            "status": "skipped",
            "vehicle_id": vehicle_id,
            "reason": "driver_id is required",
        }

    from app.services import event_service

    try:
        payload = asyncio.run(
            event_service.detect_and_persist(
                vehicle_id=vehicle_id,
                driver_id=driver_id,
                driver_state=driver_state,
                road_state=road_state,
                telemetry=telemetry,
                session_id=session_id,
                risk_score=risk_score,
                attach_clips=attach_clips,
            )
        )
        result = {"status": "ok", **payload, "phase": "4F"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Background event detection failed")
        return {
            "status": "failed",
            "vehicle_id": vehicle_id,
            "error": f"{type(exc).__name__}: {exc}",
        }

    if enqueue_clip_retry:
        for event in result.get("events", []):
            if not event.get("video_clip_url"):
                try:
                    post_process_event.delay(event["id"], str(vehicle_id))
                except Exception:  # noqa: BLE001
                    logger.exception("Clip retry enqueue failed for %s", event["id"])

    return result


@celery_app.task(name="app.tasks.events.process_safety_tick")
def process_safety_tick(
    vehicle_id: str | None = None,
    driver_id: str | None = None,
    driver_state: dict[str, Any] | None = None,
    road_state: dict[str, Any] | None = None,
    telemetry: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> dict:
    """Evaluate risk (4F) then run event detection/persistence (4D/4E) in one job."""
    if not vehicle_id or not driver_id:
        return {
            "status": "skipped",
            "reason": "vehicle_id and driver_id are required",
        }

    from app.services import event_service, risk_service

    try:
        risk_payload = asyncio.run(
            risk_service.evaluate_persist_and_publish(
                vehicle_id,
                driver_state,
                road_state,
                telemetry,
            )
        )
        events_payload = asyncio.run(
            event_service.detect_and_persist(
                vehicle_id=vehicle_id,
                driver_id=driver_id,
                driver_state=driver_state,
                road_state=road_state,
                telemetry=telemetry,
                session_id=session_id,
                risk_score=float(risk_payload.get("score", 0.0)),
            )
        )
        return {
            "status": "ok",
            "phase": "4F",
            "risk": risk_payload,
            "events": events_payload,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Safety tick failed")
        return {
            "status": "failed",
            "vehicle_id": vehicle_id,
            "error": f"{type(exc).__name__}: {exc}",
        }
