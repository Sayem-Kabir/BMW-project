"""Risk Engine API — Module 4F evaluate/publish, durable history, and Celery trigger."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import FEATURE_SAFETY, require_feature
from app.core.database import get_async_session
from app.models.user import User
from app.schemas.common import (
    RiskComputeRequest,
    RiskComputeResponse,
    RiskHistoryItem,
    RiskHistoryResponse,
    RiskScoreResponse,
)
from app.services import risk_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/risk", tags=["Risk Engine"])


def _parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _to_score_response(payload: dict) -> RiskScoreResponse:
    return RiskScoreResponse(
        vehicle_id=UUID(str(payload["vehicle_id"])),
        score=int(round(float(payload.get("score", 0)))),
        level=str(payload.get("level", "LOW")),
        factors=list(payload.get("factors") or []),
        reasons=list(payload.get("reasons") or []),
        overrides=list(payload.get("overrides") or []),
        base_score=(
            float(payload["base_score"])
            if payload.get("base_score") is not None
            else None
        ),
        base_level=payload.get("base_level"),
        timestamp=_parse_timestamp(payload.get("timestamp")),
        method=payload.get("method"),
        phase=str(payload.get("phase", risk_service.PHASE)),
        message=payload.get("message"),
    )


def _history_item(row: object) -> RiskHistoryItem:
    payload = getattr(row, "payload", None) or {}
    return RiskHistoryItem(
        id=row.id,
        vehicle_id=row.vehicle_id,
        score=float(row.score),
        level=str(row.level),
        timestamp=row.timestamp,
        factors=list(payload.get("factors") or []),
        reasons=list(payload.get("reasons") or []),
        overrides=list(payload.get("overrides") or []),
    )


@router.get("/current/{vehicle_id}", response_model=RiskScoreResponse)
async def current_risk(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_feature(FEATURE_SAFETY)),
):
    """Return the latest cached risk score for one vehicle."""
    cached = await risk_service.get_cached_risk(vehicle_id, session=session)
    if cached is None:
        return _to_score_response(risk_service.empty_risk_payload(vehicle_id))
    return _to_score_response(cached)


def _optional_uuid(value: object) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


@router.post("/{vehicle_id}/compute", response_model=RiskComputeResponse)
async def compute_risk(
    vehicle_id: UUID,
    request: RiskComputeRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Evaluate Modules 4A/4B, cache, publish, and optionally persist history."""
    try:
        payload = await risk_service.evaluate_and_publish(
            vehicle_id,
            request.driver_state,
            request.road_state,
            request.telemetry,
            publish=request.publish,
            cache=request.cache,
            persist=request.persist,
            session=session if request.persist else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Risk computation failed")
        raise HTTPException(
            status_code=503,
            detail=f"Risk engine unavailable: {exc}",
        ) from exc


    return RiskComputeResponse(
        vehicle_id=vehicle_id,
        score=float(payload["score"]),
        level=str(payload["level"]),
        risk_score=float(payload["risk_score"]),
        risk_level=str(payload["risk_level"]),
        base_score=float(payload["base_score"]),
        base_level=str(payload["base_level"]),
        factors=list(payload.get("factors") or []),
        overrides=list(payload.get("overrides") or []),
        reasons=list(payload.get("reasons") or []),
        timestamp=_parse_timestamp(payload["timestamp"]),
        method=str(payload.get("method", "")),
        published=bool(payload.get("published", False)),
        receivers=int(payload.get("receivers", 0)),
        cached=bool(payload.get("cached", False)),
        persisted=bool(payload.get("persisted", False)),
        record_id=_optional_uuid(payload.get("record_id")),
        warning=payload.get("warning"),
        persist_warning=payload.get("persist_warning"),
        phase=str(payload.get("phase", risk_service.PHASE)),
    )


@router.post("/{vehicle_id}/trigger")
async def trigger_risk_evaluation(vehicle_id: UUID, request: RiskComputeRequest):
    """Queue one background 4F risk evaluation through Celery."""
    from app.tasks.risk import run_risk_evaluation

    try:
        task = run_risk_evaluation.delay(
            vehicle_id=str(vehicle_id),
            driver_state=dict(request.driver_state),
            road_state=dict(request.road_state),
            telemetry=dict(request.telemetry),
            publish=request.publish,
            cache=request.cache,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Risk task enqueue failed")
        raise HTTPException(
            status_code=503,
            detail=f"Celery broker unavailable: {exc}",
        ) from exc
    return {
        "vehicle_id": str(vehicle_id),
        "task_id": task.id,
        "status": "queued",
        "phase": risk_service.PHASE,
    }


@router.get("/history/{vehicle_id}", response_model=RiskHistoryResponse)
async def risk_history(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    limit: int = 100,
    _user: User = Depends(require_feature(FEATURE_SAFETY)),
):
    """Return persisted risk score history for one vehicle."""
    limit = max(1, min(int(limit), 500))
    warning: str | None = None
    rows = []
    try:
        rows = await risk_service.list_risk_history(session, vehicle_id, limit=limit)
    except Exception:  # noqa: BLE001
        logger.exception("Risk history query failed for %s", vehicle_id)
        warning = "Risk history unavailable — database connection failed"
        cached = await risk_service.get_cached_risk(vehicle_id, session=session)
        if cached is not None:
            rows = []

    history = [_history_item(row) for row in rows]
    if warning and not history:
        cached = await risk_service.get_cached_risk(vehicle_id, session=session)
        if cached is not None:
            warning = (
                f"{warning}; returning latest cached score only until migration runs"
            )

    return RiskHistoryResponse(
        vehicle_id=vehicle_id,
        history=history,
        count=len(history),
        warning=warning,
        phase=risk_service.PHASE,
    )
