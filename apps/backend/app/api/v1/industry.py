"""Industry features API — Spec Section 19 (OTA, replay, insurance, carbon, chaos, twin)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN, require_roles, require_user
from app.core.tenant_limit import tenant_rate_limit
from app.models.user import User
from app.services import industry_service

router = APIRouter(prefix="/api/v1/industry", tags=["Section 19 — Industry"])
PHASE = "19"


class CanaryRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_name: str = "driver_monitor"
    version: str = "latest"
    fleet_percent: float = Field(default=10.0, ge=1.0, le=100.0)


class ReplayRequest(BaseModel):
    vehicle_id: UUID
    frames: list[dict[str, Any]] = Field(default_factory=list, max_length=500)


class StripeCheckoutRequest(BaseModel):
    tier: str = Field(default="fleet_pro", pattern="^(starter|fleet_pro|enterprise)$")
    seats: int = Field(default=5, ge=1, le=500)


@router.get("/ota/canary")
async def ota_status(_user: User = Depends(tenant_rate_limit)):
    return industry_service.ota_status()


@router.post("/ota/canary")
async def ota_start_canary(
    body: CanaryRequest,
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    return industry_service.start_canary(
        model_name=body.model_name,
        version=body.version,
        fleet_percent=body.fleet_percent,
        started_by=str(user.id),
    )


@router.post("/ota/canary/rollback")
async def ota_rollback(
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    return industry_service.rollback_canary(rolled_back_by=str(user.id))


@router.post("/replay")
async def event_replay(
    body: ReplayRequest,
    _user: User = Depends(require_user),
):
    return industry_service.replay_drive(str(body.vehicle_id), body.frames)


@router.get("/insurance/{driver_id}")
async def insurance_premium(
    driver_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_user),
):
    return await industry_service.insurance_premium(session, driver_id)


@router.get("/carbon/{vehicle_id}")
async def carbon_efficiency(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_user),
):
    return await industry_service.carbon_efficiency(session, vehicle_id)


@router.post("/billing/checkout")
async def stripe_checkout(
    body: StripeCheckoutRequest,
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    return industry_service.stripe_checkout_session(
        org_id=str(user.org_id) if user.org_id else None,
        tier=body.tier,
        seats=body.seats,
    )


@router.get("/twin/{vehicle_id}")
async def digital_twin(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_user),
):
    return await industry_service.digital_twin_state(session, vehicle_id)


@router.post("/chaos/{target}")
async def chaos_inject(
    target: str,
    user: User = Depends(require_roles(ROLE_SUPER_ADMIN)),
):
    """Deliberately probe dependency health (Redis/Postgres) — Section 19.5."""
    if target not in {"redis", "postgres", "both"}:
        raise HTTPException(status_code=400, detail="target must be redis|postgres|both")
    return await industry_service.chaos_probe(target)


@router.get("/edge/decide")
async def edge_cloud_decide(
    risk_score: float = Query(default=40.0, ge=0, le=100),
    _user: User = Depends(require_user),
):
    return industry_service.edge_cloud_route(risk_score)


@router.get("/fusion/demo")
async def sensor_fusion_demo(_user: User = Depends(require_user)):
    return industry_service.sensor_fusion_demo()


@router.get("/kafka/buffer")
async def kafka_buffer(
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    from app.services.kafka_bus import drain_buffer

    items = drain_buffer()
    return {"count": len(items), "events": items[-50:], "phase": PHASE}


@router.get("/feast/entities")
async def feast_entities(
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    from ml.feature_store.feast_stub import list_entities, read_features

    ids = list_entities()
    return {
        "entities": ids,
        "sample": read_features(ids[0]) if ids else None,
        "phase": PHASE,
    }


@router.post("/federated/round")
async def federated_round(
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    return industry_service.federated_avg_round()
