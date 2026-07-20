"""Module 4F Celery tasks — background risk evaluation and persistence."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.risk.run_risk_evaluation")
def run_risk_evaluation(
    vehicle_id: str | None = None,
    driver_state: dict[str, Any] | None = None,
    road_state: dict[str, Any] | None = None,
    telemetry: dict[str, Any] | None = None,
    *,
    publish: bool = True,
    cache: bool = True,
) -> dict:
    if not vehicle_id:
        return {
            "status": "skipped",
            "vehicle_id": vehicle_id,
            "reason": "vehicle_id is required",
        }

    from app.services.risk_service import evaluate_persist_and_publish

    try:
        payload = asyncio.run(
            evaluate_persist_and_publish(
                vehicle_id,
                driver_state,
                road_state,
                telemetry,
                publish=publish,
                cache=cache,
            )
        )
        return {"status": "ok", **payload}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Background risk evaluation failed")
        return {
            "status": "failed",
            "vehicle_id": vehicle_id,
            "error": f"{type(exc).__name__}: {exc}",
        }
