"""Module 3H Celery tasks — background 3G predictions persisted to Postgres."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.maintenance.run_batch_predictions")
def run_batch_predictions(
    vehicle_id: str | None = None,
    telemetry: dict[str, Any] | None = None,
) -> dict:
    """Run the unified 3G maintenance pipeline and persist component rows."""
    if not vehicle_id:
        return {
            "status": "skipped",
            "vehicle_id": vehicle_id,
            "reason": "vehicle_id is required",
        }
    if not telemetry:
        return {
            "status": "skipped",
            "vehicle_id": vehicle_id,
            "reason": (
                "telemetry payload is required — raw VSS alone does not satisfy "
                "the 3B–3E feature contracts"
            ),
        }

    from app.services.maintenance_service import run_and_persist

    try:
        return asyncio.run(run_and_persist(vehicle_id, telemetry))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Batch maintenance prediction failed")
        return {
            "status": "failed",
            "vehicle_id": vehicle_id,
            "error": f"{type(exc).__name__}: {exc}",
        }
