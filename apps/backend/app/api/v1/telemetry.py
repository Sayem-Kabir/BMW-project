"""Vehicle telemetry API — history with demo series fallback for Phase 6C + LTTB (13)."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import FEATURE_ASSISTANT, require_feature
from app.core.database import get_async_session
from app.core.lttb import downsample_series
from app.models.telemetry import VehicleTelemetry
from app.models.user import User
from app.schemas.common import TelemetrySnapshot

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])
PHASE = "6C"


def _demo_series(vehicle_id: UUID, points: int = 40) -> list[dict]:
    now = datetime.now(timezone.utc)
    seed = int(str(vehicle_id).replace("-", "")[-4:], 16) % 17
    rows: list[dict] = []
    for i in range(points):
        t = now - timedelta(minutes=points - i)
        rows.append(
            {
                "time": t.isoformat(),
                "speed_kmh": round(35 + ((i + seed) % 12) * 2.5, 1),
                "rpm": 1200 + ((i + seed) % 8) * 150,
                "battery_soc_pct": round(72 - i * 0.15, 1),
                "tire_fl": 32.0,
                "tire_fr": 33.0,
                "tire_rl": 22.0 + (i % 3) * 0.2,
                "tire_rr": 33.0,
                "latitude": 48.135 + (i * 0.0003),
                "longitude": 11.582 + (i * 0.0002),
            }
        )
    return rows


@router.get("/{vehicle_id}")
async def telemetry_history(
    vehicle_id: UUID,
    max_points: int = Query(default=120, ge=10, le=500),
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_feature(FEATURE_ASSISTANT)),
):
    try:
        result = await session.execute(
            select(VehicleTelemetry)
            .where(VehicleTelemetry.vehicle_id == vehicle_id)
            .order_by(VehicleTelemetry.time.desc())
            .limit(500)
        )
        rows = list(result.scalars().all())
    except Exception:  # noqa: BLE001
        rows = []

    if not rows:
        points = _demo_series(vehicle_id)
        down = downsample_series(points, max_points, y_key="speed_kmh")
        return {
            "vehicle_id": str(vehicle_id),
            "points": down,
            "phase": PHASE,
            "source": "demo",
            "downsampled": len(down) < len(points),
            "max_points": max_points,
        }

    points = [
        {
            "time": r.time.isoformat(),
            "speed_kmh": r.speed_kmh,
            "rpm": r.rpm,
            "battery_soc_pct": r.battery_soc_pct,
            "latitude": r.latitude,
            "longitude": r.longitude,
        }
        for r in reversed(rows)
    ]
    down = downsample_series(points, max_points, y_key="speed_kmh")
    return {
        "vehicle_id": str(vehicle_id),
        "points": down,
        "phase": PHASE,
        "source": "database",
        "downsampled": len(down) < len(points),
        "max_points": max_points,
    }


@router.get("/{vehicle_id}/live", response_model=TelemetrySnapshot)
async def telemetry_live(
    vehicle_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _user: User = Depends(require_feature(FEATURE_ASSISTANT)),
):
    # Module 8B — prefer live Kuksa snapshot when broker is reachable
    try:
        from app.services import kuksa_service

        snap = await kuksa_service.get_kuksa_snapshot(vehicle_id)
        if snap.speed_kmh is not None or snap.latitude is not None:
            return TelemetrySnapshot(
                vehicle_id=vehicle_id,
                speed_kmh=snap.speed_kmh,
                rpm=snap.rpm,
                battery_soc_pct=snap.battery_soc_pct,
                latitude=snap.latitude,
                longitude=snap.longitude,
                timestamp=snap.timestamp,
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        result = await session.execute(
            select(VehicleTelemetry)
            .where(VehicleTelemetry.vehicle_id == vehicle_id)
            .order_by(VehicleTelemetry.time.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
    except Exception:  # noqa: BLE001
        row = None
    if row is None:
        demo = _demo_series(vehicle_id, points=1)[0]
        return TelemetrySnapshot(
            vehicle_id=vehicle_id,
            speed_kmh=demo["speed_kmh"],
            rpm=demo["rpm"],
            battery_soc_pct=demo["battery_soc_pct"],
            latitude=demo["latitude"],
            longitude=demo["longitude"],
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
