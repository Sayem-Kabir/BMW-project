"""Analytics API — Module 6D; Spec Phase 8D org scoping + feature gates."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import FEATURE_HOME_FLEET, require_feature
from app.core.config import settings
from app.core.database import get_async_session, get_read_session
from app.core.scope import driver_scope_id, resolve_org_id
from app.core.security import (
    ROLE_DRIVER,
    ROLE_FLEET_MANAGER,
    ROLE_MAINTENANCE_TECH,
    ROLE_ORG_ADMIN,
    require_roles,
)
from app.models.user import User
from app.services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])
PHASE = "6D"

_DRIVER_ANALYTICS = require_roles(
    ROLE_DRIVER,
    ROLE_FLEET_MANAGER,
    ROLE_MAINTENANCE_TECH,
    ROLE_ORG_ADMIN,
)


@router.get("/driver/{driver_id}/weekly")
async def weekly_report(
    driver_id: UUID,
    days: int = Query(default=7, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(_DRIVER_ANALYTICS),
):
    scoped = driver_scope_id(user)
    if scoped is not None and scoped != driver_id:
        raise HTTPException(status_code=403, detail="Cannot view another driver's analytics")
    return await analytics_service.driver_weekly(session, driver_id, days=days)


@router.get("/driver/{driver_id}/weekly.pdf")
async def weekly_report_pdf(
    driver_id: UUID,
    days: int = Query(default=7, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(_DRIVER_ANALYTICS),
):
    """Spec Phase 12D — PDF weekly driver report."""
    from fastapi.responses import Response

    from app.services import report_service

    scoped = driver_scope_id(user)
    if scoped is not None and scoped != driver_id:
        raise HTTPException(status_code=403, detail="Cannot view another driver's analytics")
    data = await analytics_service.driver_weekly(session, driver_id, days=days)
    pdf = report_service.build_weekly_pdf(data)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="driver-{driver_id}-weekly.pdf"'
        },
    )


@router.get("/driver/{driver_id}/trends")
async def driver_trends(
    driver_id: UUID,
    days: int = Query(default=7, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(_DRIVER_ANALYTICS),
):
    scoped = driver_scope_id(user)
    if scoped is not None and scoped != driver_id:
        raise HTTPException(status_code=403, detail="Cannot view another driver's analytics")
    weekly = await analytics_service.driver_weekly(session, driver_id, days=days)
    return {
        "driver_id": str(driver_id),
        "trends": weekly.get("sparkline") or [],
        "phase": PHASE,
    }


@router.get("/fleet/incidents")
async def fleet_incidents(
    org_id: UUID | None = Query(default=None),
    weeks: int = Query(default=8, ge=1, le=26),
    session: AsyncSession = Depends(get_read_session),
    user: User = Depends(require_feature(FEATURE_HOME_FLEET)),
):
    resolved = resolve_org_id(org_id, user)
    incidents = await analytics_service.fleet_incidents(
        session, org_id=resolved, weeks=weeks
    )
    max_age = max(5, int(settings.analytics_cache_max_age_sec))
    return JSONResponse(
        content={"incidents": incidents, "count": len(incidents), "phase": PHASE},
        headers={"Cache-Control": f"public, max-age={max_age}"},
    )


@router.get("/fleet/leaderboard")
async def leaderboard(
    org_id: UUID | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=30),
    session: AsyncSession = Depends(get_read_session),
    user: User = Depends(require_feature(FEATURE_HOME_FLEET)),
):
    resolved = resolve_org_id(org_id, user)
    board = await analytics_service.fleet_leaderboard(
        session, org_id=resolved, days=days
    )
    max_age = max(5, int(settings.analytics_cache_max_age_sec))
    return JSONResponse(
        content={"leaderboard": board, "count": len(board), "phase": PHASE},
        headers={"Cache-Control": f"public, max-age={max_age}"},
    )
