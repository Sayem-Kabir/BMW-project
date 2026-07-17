from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.event import SafetyEvent
from app.models.vehicle import Vehicle
from app.schemas.common import FleetOverviewResponse
from app.schemas.fleet import VehicleCreate, VehicleResponse

router = APIRouter(prefix="/api/v1/fleet", tags=["Fleet Management"])


@router.get("/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Vehicle).where(Vehicle.is_active.is_(True)))
    return list(result.scalars().all())


@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
async def create_vehicle(
    body: VehicleCreate,
    session: AsyncSession = Depends(get_async_session),
):
    vehicle = Vehicle(**body.model_dump())
    session.add(vehicle)
    await session.commit()
    await session.refresh(vehicle)
    return vehicle


@router.get("/alerts")
async def list_alerts(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(SafetyEvent)
        .where(SafetyEvent.acknowledged.is_(False))
        .order_by(SafetyEvent.timestamp.desc())
        .limit(50)
    )
    events = result.scalars().all()
    return {
        "alerts": [
            {
                "id": str(e.id),
                "vehicle_id": str(e.vehicle_id),
                "event_type": e.event_type,
                "severity": e.severity,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ],
        "phase": "scaffold",
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: UUID, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(SafetyEvent).where(SafetyEvent.id == alert_id))
    event = result.scalar_one_or_none()
    if event is None:
        return {"status": "not_found", "alert_id": str(alert_id)}
    event.acknowledged = True
    await session.commit()
    return {"status": "acknowledged", "alert_id": str(alert_id)}


@router.get("/overview", response_model=FleetOverviewResponse)
async def fleet_overview(session: AsyncSession = Depends(get_async_session)):
    try:
        vehicle_count = await session.scalar(select(func.count()).select_from(Vehicle)) or 0
        active_alerts = (
            await session.scalar(
                select(func.count())
                .select_from(SafetyEvent)
                .where(SafetyEvent.acknowledged.is_(False))
            )
            or 0
        )
    except Exception:
        return FleetOverviewResponse(
            vehicle_count=0,
            active_alerts=0,
            average_risk=0.0,
            online_vehicles=0,
        )
    return FleetOverviewResponse(
        vehicle_count=vehicle_count,
        active_alerts=active_alerts,
        average_risk=0.0,
        online_vehicles=0,
    )
