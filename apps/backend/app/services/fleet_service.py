"""Module 6A — fleet overview aggregation and demo map metadata."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import SafetyEvent
from app.models.maintenance import MaintenancePrediction
from app.models.risk_score import RiskScoreRecord
from app.models.vehicle import Vehicle
from app.services import risk_service

logger = logging.getLogger(__name__)

PHASE = "6A"
DEMO_ORG_ID = UUID("00000000-0000-4000-8000-000000000010")

# Demo GPS markers for fleet map (Munich area) — no live Kuksa GPS required.
DEMO_VEHICLE_LOCATIONS: dict[str, dict[str, float]] = {
    "00000000-0000-4000-8000-000000000003": {
        "latitude": 48.1351,
        "longitude": 11.5820,
    },
    "00000000-0000-4000-8000-000000000004": {
        "latitude": 48.1405,
        "longitude": 11.5612,
    },
    "00000000-0000-4000-8000-000000000005": {
        "latitude": 48.1278,
        "longitude": 11.5915,
    },
}

ONLINE_WINDOW_MINUTES = 30
CRITICAL_HEALTH = 0.35


def demo_location(vehicle_id: UUID | str) -> dict[str, float] | None:
    return DEMO_VEHICLE_LOCATIONS.get(str(vehicle_id))


async def resolve_vehicle_location(
    session: AsyncSession,
    vehicle_id: UUID | str,
) -> dict[str, float]:
    """Prefer latest GPS from vehicle_telemetry (8B Kuksa bridge); else demo map pin."""
    try:
        from app.models.telemetry import VehicleTelemetry

        result = await session.execute(
            select(VehicleTelemetry)
            .where(VehicleTelemetry.vehicle_id == UUID(str(vehicle_id)))
            .where(VehicleTelemetry.latitude.is_not(None))
            .where(VehicleTelemetry.longitude.is_not(None))
            .order_by(VehicleTelemetry.time.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is not None and row.latitude is not None and row.longitude is not None:
            return {"latitude": float(row.latitude), "longitude": float(row.longitude)}
    except Exception:  # noqa: BLE001
        logger.debug("No live GPS for %s — using demo pin", vehicle_id)
    return demo_location(vehicle_id) or {"latitude": 48.137, "longitude": 11.575}


def status_from_risk_and_health(
    *,
    risk_level: str | None,
    worst_health: float | None,
) -> str:
    level = (risk_level or "LOW").upper()
    if level in {"CRITICAL", "HIGH"} or (
        worst_health is not None and worst_health <= CRITICAL_HEALTH
    ):
        return "critical"
    if level == "MEDIUM" or (
        worst_health is not None and worst_health <= 0.6
    ):
        return "maintenance"
    return "operational"


async def _latest_risk_rows(
    session: AsyncSession,
    vehicle_ids: list[UUID],
) -> dict[str, RiskScoreRecord]:
    if not vehicle_ids:
        return {}
    result = await session.execute(
        select(RiskScoreRecord)
        .where(RiskScoreRecord.vehicle_id.in_(vehicle_ids))
        .order_by(RiskScoreRecord.timestamp.desc())
    )
    latest: dict[str, RiskScoreRecord] = {}
    for row in result.scalars().all():
        key = str(row.vehicle_id)
        if key not in latest:
            latest[key] = row
    return latest


async def _worst_health_by_vehicle(
    session: AsyncSession,
    vehicle_ids: list[UUID],
) -> dict[str, float]:
    if not vehicle_ids:
        return {}
    result = await session.execute(
        select(
            MaintenancePrediction.vehicle_id,
            func.min(MaintenancePrediction.health_score),
        )
        .where(MaintenancePrediction.vehicle_id.in_(vehicle_ids))
        .group_by(MaintenancePrediction.vehicle_id)
    )
    return {str(vid): float(score) for vid, score in result.all() if score is not None}


async def build_fleet_overview(
    session: AsyncSession,
    *,
    org_id: UUID | None = None,
) -> dict[str, Any]:
    query = select(Vehicle).where(Vehicle.is_active.is_(True))
    if org_id is not None:
        query = query.where(Vehicle.org_id == org_id)
    vehicles = list((await session.execute(query)).scalars().all())
    vehicle_ids = [v.id for v in vehicles]

    active_alerts = 0
    if vehicle_ids:
        active_alerts = (
            await session.scalar(
                select(func.count())
                .select_from(SafetyEvent)
                .where(
                    SafetyEvent.acknowledged.is_(False),
                    SafetyEvent.vehicle_id.in_(vehicle_ids),
                )
            )
            or 0
        )

    latest_risk = await _latest_risk_rows(session, vehicle_ids)
    scores: list[float] = []
    online = 0
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=ONLINE_WINDOW_MINUTES)
    risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

    for vehicle in vehicles:
        key = str(vehicle.id)
        row = latest_risk.get(key)
        cached = None
        if row is None:
            try:
                cached = await risk_service.get_cached_risk(vehicle.id, session=None)
            except Exception:  # noqa: BLE001
                cached = None

        score = float(row.score) if row is not None else (
            float(cached.get("score") or cached.get("risk_score") or 0.0)
            if cached
            else None
        )
        level = (
            str(row.level).upper()
            if row is not None
            else str((cached or {}).get("level") or (cached or {}).get("risk_level") or "LOW").upper()
        )
        if score is not None:
            scores.append(score)
        if level in risk_distribution:
            risk_distribution[level] += 1
        else:
            risk_distribution["LOW"] += 1

        stamp = None
        if row is not None:
            stamp = row.timestamp
        elif cached and cached.get("timestamp"):
            try:
                stamp = datetime.fromisoformat(str(cached["timestamp"]).replace("Z", "+00:00"))
            except ValueError:
                stamp = None
        if stamp is not None:
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            if stamp >= cutoff:
                online += 1

    # If we have active vehicles but no recent risk stamps, treat seeded fleet as online for demo.
    if vehicles and online == 0:
        online = len(vehicles)

    return {
        "vehicle_count": len(vehicles),
        "active_alerts": int(active_alerts),
        "average_risk": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "online_vehicles": online,
        "risk_distribution": risk_distribution,
        "org_id": str(org_id) if org_id else None,
        "phase": PHASE,
    }


async def list_fleet_vehicles(
    session: AsyncSession,
    *,
    org_id: UUID | None = None,
) -> list[dict[str, Any]]:
    query = select(Vehicle).where(Vehicle.is_active.is_(True))
    if org_id is not None:
        query = query.where(Vehicle.org_id == org_id)
    vehicles = list((await session.execute(query)).scalars().all())
    vehicle_ids = [v.id for v in vehicles]
    latest_risk = await _latest_risk_rows(session, vehicle_ids)
    health = await _worst_health_by_vehicle(session, vehicle_ids)

    alert_counts: dict[str, int] = {}
    if vehicle_ids:
        result = await session.execute(
            select(SafetyEvent.vehicle_id, func.count())
            .where(
                SafetyEvent.vehicle_id.in_(vehicle_ids),
                SafetyEvent.acknowledged.is_(False),
            )
            .group_by(SafetyEvent.vehicle_id)
        )
        alert_counts = {str(vid): int(count) for vid, count in result.all()}

    rows: list[dict[str, Any]] = []
    for vehicle in vehicles:
        key = str(vehicle.id)
        risk_row = latest_risk.get(key)
        score = float(risk_row.score) if risk_row else 0.0
        level = str(risk_row.level).upper() if risk_row else "LOW"
        loc = await resolve_vehicle_location(session, vehicle.id)
        worst = health.get(key)
        rows.append(
            {
                "id": key,
                "name": vehicle.name,
                "vin": vehicle.vin,
                "model": vehicle.model,
                "year": vehicle.year,
                "fuel_type": vehicle.fuel_type,
                "org_id": str(vehicle.org_id) if vehicle.org_id else None,
                "is_active": vehicle.is_active,
                "risk_score": score,
                "risk_level": level,
                "status": status_from_risk_and_health(
                    risk_level=level,
                    worst_health=worst,
                ),
                "active_alerts": alert_counts.get(key, 0),
                "worst_health": worst,
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "phase": PHASE,
            }
        )
    return rows


async def list_fleet_alerts(
    session: AsyncSession,
    *,
    org_id: UUID | None = None,
    limit: int = 50,
    driver_id: UUID | None = None,
) -> list[dict[str, Any]]:
    query = (
        select(SafetyEvent)
        .where(SafetyEvent.acknowledged.is_(False))
        .order_by(SafetyEvent.timestamp.desc())
        .limit(limit)
    )
    if org_id is not None:
        query = query.join(Vehicle, Vehicle.id == SafetyEvent.vehicle_id).where(
            Vehicle.org_id == org_id
        )
    if driver_id is not None:
        query = query.where(SafetyEvent.driver_id == driver_id)
    events = list((await session.execute(query)).scalars().all())
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    events.sort(
        key=lambda e: (
            severity_rank.get(str(e.severity).upper(), 9),
            -(e.timestamp.timestamp() if e.timestamp else 0),
        )
    )
    return [
        {
            "id": str(e.id),
            "vehicle_id": str(e.vehicle_id),
            "driver_id": str(e.driver_id),
            "event_type": e.event_type,
            "severity": e.severity,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "video_clip_url": e.video_clip_url,
            "xai_explanation": e.xai_explanation,
            "acknowledged": e.acknowledged,
            "latitude": e.latitude,
            "longitude": e.longitude,
        }
        for e in events
    ]
