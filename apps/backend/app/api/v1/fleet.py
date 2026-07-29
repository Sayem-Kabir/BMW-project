"""Fleet Management API — Modules 6A+; Spec Phase 8D org scoping + feature gates."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import FEATURE_HOME_FLEET, FEATURE_SAFETY, require_feature
from app.core.database import get_async_session
from app.core.hardening import (
    idempotency_lookup,
    idempotency_store,
    optional_idempotency_key,
    page_meta,
)
from app.core.scope import driver_scope_id, resolve_org_id
from app.core.security import (
    ROLE_DRIVER,
    ROLE_FLEET_MANAGER,
    ROLE_MAINTENANCE_TECH,
    ROLE_ORG_ADMIN,
    require_roles,
    require_user_for_writes,
)
from app.models.event import SafetyEvent
from app.models.user import User
from app.schemas.common import FleetOverviewResponse
from app.schemas.fleet import VehicleCreate, VehicleResponse
from app.services import auth_service, fleet_service

router = APIRouter(prefix="/api/v1/fleet", tags=["Fleet Management"])
PHASE = "6A"
ALERTS_PHASE = "6E"

# Drivers may list own alerts (safety); fleet roles use org fleet home.
_ALERT_ROLES = require_roles(
    ROLE_DRIVER,
    ROLE_FLEET_MANAGER,
    ROLE_MAINTENANCE_TECH,
    ROLE_ORG_ADMIN,
)


@router.get("/vehicles")
async def list_vehicles(
    org_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_feature(FEATURE_HOME_FLEET)),
):
    resolved = resolve_org_id(org_id, user)
    rows = await fleet_service.list_fleet_vehicles(session, org_id=resolved)
    return {"vehicles": rows, "count": len(rows), "phase": PHASE}


@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
async def create_vehicle(
    body: VehicleCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User | None = Depends(require_user_for_writes),
    _fleet: User = Depends(require_feature(FEATURE_HOME_FLEET)),
    idempotency_key: str | None = Depends(optional_idempotency_key),
):
    from app.models.vehicle import Vehicle

    path = "/api/v1/fleet/vehicles"
    uid = user.id if user else None
    cached = idempotency_lookup(key=idempotency_key, path=path, user_id=uid)
    if cached is not None:
        return VehicleResponse(**cached)

    data = body.model_dump()
    if user is not None and user.org_id is not None:
        data["org_id"] = user.org_id
    vehicle = Vehicle(**data)
    session.add(vehicle)
    await session.commit()
    await session.refresh(vehicle)
    payload = VehicleResponse.model_validate(vehicle).model_dump(mode="json")
    idempotency_store(key=idempotency_key, path=path, payload=payload, user_id=uid)
    return vehicle


@router.get("/alerts")
async def list_alerts(
    org_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(_ALERT_ROLES),
):
    from app.core.hardening import page_meta

    resolved = resolve_org_id(org_id, user)
    alerts = await fleet_service.list_fleet_alerts(
        session,
        org_id=resolved,
        limit=limit + offset,
        driver_id=driver_scope_id(user),
    )
    page = alerts[offset : offset + limit]
    return {
        "alerts": page,
        "count": len(page),
        "pagination": page_meta(total=len(alerts), limit=limit, offset=offset),
        "phase": ALERTS_PHASE,
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User | None = Depends(require_user_for_writes),
    _safety: User = Depends(require_feature(FEATURE_SAFETY)),
):
    result = await session.execute(select(SafetyEvent).where(SafetyEvent.id == alert_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if user is not None and user.org_id is not None:
        from app.models.vehicle import Vehicle

        v = await session.execute(select(Vehicle).where(Vehicle.id == event.vehicle_id))
        vehicle = v.scalar_one_or_none()
        if vehicle and vehicle.org_id and vehicle.org_id != user.org_id:
            raise HTTPException(status_code=403, detail="Alert not in your organization")
    event.acknowledged = True
    event.acknowledged_at = datetime.now(timezone.utc)
    if user is not None:
        await auth_service.write_audit(
            session,
            action="EVENT_ACKNOWLEDGED",
            user=user,
            target_type="safety_events",
            target_id=alert_id,
        )
    await session.commit()
    return {
        "status": "acknowledged",
        "alert_id": str(alert_id),
        "phase": ALERTS_PHASE,
    }


@router.get("/overview", response_model=FleetOverviewResponse)
async def fleet_overview(
    org_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_feature(FEATURE_HOME_FLEET)),
):
    resolved = resolve_org_id(org_id, user)
    try:
        payload = await fleet_service.build_fleet_overview(session, org_id=resolved)
    except Exception:  # noqa: BLE001
        return FleetOverviewResponse(
            vehicle_count=0,
            active_alerts=0,
            average_risk=0.0,
            online_vehicles=0,
        )
    return FleetOverviewResponse(
        vehicle_count=int(payload["vehicle_count"]),
        active_alerts=int(payload["active_alerts"]),
        average_risk=float(payload["average_risk"]),
        online_vehicles=int(payload["online_vehicles"]),
        phase=str(payload.get("phase") or PHASE),
    )


@router.get("/overview/detail")
async def fleet_overview_detail(
    org_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_feature(FEATURE_HOME_FLEET)),
):
    resolved = resolve_org_id(org_id, user)
    overview = await fleet_service.build_fleet_overview(session, org_id=resolved)
    vehicles = await fleet_service.list_fleet_vehicles(session, org_id=resolved)
    return {**overview, "vehicles": vehicles, "phase": PHASE}
