"""Predictive maintenance API — Module 3H real 3G inference and persistence."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import FEATURE_MAINTENANCE, require_feature
from app.core.database import get_async_session
from app.models.maintenance import MaintenancePrediction
from app.models.user import User
from app.schemas.common import (
    MaintenancePredictRequest,
    MaintenancePredictionResponse,
    MaintenanceRunResponse,
)
from app.services import maintenance_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/maintenance", tags=["Predictive Maintenance"])

VALID_COMPONENTS = ("engine", "brake", "battery", "tire")


@router.get("/status")
async def maintenance_status(
    _user: User = Depends(require_feature(FEATURE_MAINTENANCE)),
):
    """Model-artifact readiness and feature contracts without inference."""
    try:
        status = await asyncio.to_thread(maintenance_service.component_status)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Maintenance status check failed")
        raise HTTPException(
            status_code=503,
            detail=f"Maintenance pipeline unavailable: {exc}",
        ) from exc
    return {**status, "phase": "3H"}


@router.post("/{vehicle_id}/predict", response_model=MaintenanceRunResponse)
async def predict_maintenance(
    vehicle_id: UUID,
    request: MaintenancePredictRequest,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_feature(FEATURE_MAINTENANCE)),
):
    """Run the 3G pipeline for one telemetry payload and persist components."""
    if not request.telemetry:
        raise HTTPException(status_code=400, detail="telemetry must not be empty")

    try:
        result = await asyncio.to_thread(
            maintenance_service.run_pipeline,
            request.telemetry,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Maintenance pipeline failed")
        raise HTTPException(
            status_code=503,
            detail=f"Maintenance pipeline unavailable: {exc}",
        ) from exc

    persisted = 0
    try:
        rows = await maintenance_service.persist_result(session, vehicle_id, result)
        persisted = len(rows)
    except Exception:  # noqa: BLE001
        logger.exception("Maintenance prediction persistence failed")

    payload = result.to_dict()
    return MaintenanceRunResponse(
        vehicle_id=vehicle_id,
        persisted=persisted,
        ml_model_version=maintenance_service.ML_MODEL_VERSION,
        **payload,
    )


@router.post("/{vehicle_id}/trigger")
async def trigger_prediction(
    vehicle_id: UUID,
    request: MaintenancePredictRequest,
    _user: User = Depends(require_feature(FEATURE_MAINTENANCE)),
):
    """Queue one background 3G run through Celery."""
    from app.tasks.maintenance import run_batch_predictions

    try:
        task = run_batch_predictions.delay(
            vehicle_id=str(vehicle_id),
            telemetry=dict(request.telemetry),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Maintenance task enqueue failed")
        raise HTTPException(
            status_code=503,
            detail=f"Celery broker unavailable: {exc}",
        ) from exc
    return {
        "vehicle_id": str(vehicle_id),
        "task_id": task.id,
        "status": "queued",
        "phase": "3H",
    }


@router.get("/{vehicle_id}/history")
async def maintenance_history(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    limit: int = 100,
    _user: User = Depends(require_feature(FEATURE_MAINTENANCE)),
):
    """Recent persisted predictions for one vehicle, newest first."""
    limit = max(1, min(int(limit), 500))
    warning: str | None = None
    rows: list[MaintenancePrediction] = []
    try:
        result = await session.execute(
            select(MaintenancePrediction)
            .where(MaintenancePrediction.vehicle_id == vehicle_id)
            .order_by(MaintenancePrediction.created_at.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
    except Exception:  # noqa: BLE001 — DB optional: live inference still works
        logger.exception("Maintenance history query failed")
        warning = "Database unavailable — no persisted history"
    return {
        "vehicle_id": str(vehicle_id),
        "history": [
            MaintenancePredictionResponse.model_validate(row).model_dump(mode="json")
            for row in rows
        ],
        "warning": warning,
        "phase": "3H",
    }


@router.get("/{vehicle_id}")
async def list_predictions(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_feature(FEATURE_MAINTENANCE)),
):
    """Latest persisted prediction per component."""
    warning: str | None = None
    latest: dict[str, MaintenancePrediction] = {}
    try:
        result = await session.execute(
            select(MaintenancePrediction)
            .where(MaintenancePrediction.vehicle_id == vehicle_id)
            .order_by(MaintenancePrediction.created_at.desc())
            .limit(50)
        )
        for row in result.scalars().all():
            latest.setdefault(row.component, row)
    except Exception:  # noqa: BLE001 — DB optional: live inference still works
        logger.exception("Maintenance latest-predictions query failed")
        warning = "Database unavailable — no persisted predictions"
    return {
        "vehicle_id": str(vehicle_id),
        "predictions": [
            MaintenancePredictionResponse.model_validate(row).model_dump(mode="json")
            for row in latest.values()
        ],
        "warning": warning,
        "phase": "3H",
    }


@router.get("/{vehicle_id}/{component}")
async def component_prediction(
    vehicle_id: UUID,
    component: str,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_feature(FEATURE_MAINTENANCE)),
):
    """Latest persisted prediction (with SHAP payload) for one component."""
    key = component.strip().lower()
    if key not in VALID_COMPONENTS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown component {component!r}; expected {VALID_COMPONENTS}",
        )
    result = await session.execute(
        select(MaintenancePrediction)
        .where(
            MaintenancePrediction.vehicle_id == vehicle_id,
            MaintenancePrediction.component == key,
        )
        .order_by(MaintenancePrediction.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored prediction for component {key!r}",
        )
    return MaintenancePredictionResponse.model_validate(row).model_dump(mode="json")
