from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.telemetry import VehicleTelemetry
from app.schemas.common import TelemetrySnapshot

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.get("/{vehicle_id}")
async def telemetry_history(vehicle_id: UUID, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(VehicleTelemetry)
        .where(VehicleTelemetry.vehicle_id == vehicle_id)
        .order_by(VehicleTelemetry.time.desc())
        .limit(500)
    )
    rows = result.scalars().all()
    return {
        "vehicle_id": str(vehicle_id),
        "points": [
            {
                "time": r.time.isoformat(),
                "speed_kmh": r.speed_kmh,
                "rpm": r.rpm,
                "battery_soc_pct": r.battery_soc_pct,
                "latitude": r.latitude,
                "longitude": r.longitude,
            }
            for r in rows
        ],
        "phase": "scaffold",
    }


@router.get("/{vehicle_id}/live", response_model=TelemetrySnapshot)
async def telemetry_live(vehicle_id: UUID, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(VehicleTelemetry)
        .where(VehicleTelemetry.vehicle_id == vehicle_id)
        .order_by(VehicleTelemetry.time.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return TelemetrySnapshot(
            vehicle_id=vehicle_id,
            timestamp=datetime.now(timezone.utc),
        )
    return TelemetrySnapshot(
        vehicle_id=vehicle_id,
        speed_kmh=row.speed_kmh,
        rpm=row.rpm,
        battery_soc_pct=row.battery_soc_pct,
        latitude=row.latitude,
        longitude=row.longitude,
        timestamp=row.time,
    )
