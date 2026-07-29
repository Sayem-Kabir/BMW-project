"""Module 6D — fleet analytics (leaderboard + incident trends)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.driver import Driver
from app.models.event import SafetyEvent
from app.models.score import DriverScore
from app.models.vehicle import Vehicle
from app.services.fleet_service import DEMO_ORG_ID

PHASE = "6D"


def _risk_tier(score: float) -> str:
    if score >= 85:
        return "green"
    if score >= 70:
        return "amber"
    return "red"


async def fleet_leaderboard(
    session: AsyncSession,
    *,
    org_id: UUID | None = DEMO_ORG_ID,
    days: int = 7,
) -> list[dict[str, Any]]:
    since = date.today() - timedelta(days=max(1, days) - 1)
    drivers_q = select(Driver)
    if org_id is not None:
        drivers_q = drivers_q.where(Driver.org_id == org_id)
    drivers = list((await session.execute(drivers_q)).scalars().all())
    if not drivers:
        return []

    scores_result = await session.execute(
        select(DriverScore)
        .where(
            DriverScore.driver_id.in_([d.id for d in drivers]),
            DriverScore.date >= since,
        )
        .order_by(DriverScore.date.asc())
    )
    by_driver: dict[str, list[DriverScore]] = {}
    for row in scores_result.scalars().all():
        by_driver.setdefault(str(row.driver_id), []).append(row)

    # Fallback: derive a score from recent safety events when DriverScore is empty.
    event_counts: dict[str, int] = {}
    events_result = await session.execute(
        select(SafetyEvent.driver_id, func.count())
        .where(
            SafetyEvent.driver_id.in_([d.id for d in drivers]),
            SafetyEvent.timestamp
            >= datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc),
        )
        .group_by(SafetyEvent.driver_id)
    )
    event_counts = {str(did): int(count) for did, count in events_result.all()}

    board: list[dict[str, Any]] = []
    for driver in drivers:
        key = str(driver.id)
        rows = by_driver.get(key, [])
        sparkline = [int(r.safety_score) for r in rows]
        if sparkline:
            avg = sum(sparkline) / len(sparkline)
        else:
            # Start at 95 and subtract 5 per recent safety event (floor 40).
            avg = max(40.0, 95.0 - 5.0 * event_counts.get(key, 0))
            sparkline = [int(avg)]
        board.append(
            {
                "driver_id": key,
                "name": driver.name,
                "email": driver.email,
                "safety_score": round(avg, 1),
                "risk_tier": _risk_tier(avg),
                "sparkline": sparkline[-7:],
                "event_count_7d": event_counts.get(key, 0),
            }
        )

    board.sort(key=lambda item: item["safety_score"], reverse=True)
    for index, item in enumerate(board, start=1):
        item["rank"] = index
    return board


async def fleet_incidents(
    session: AsyncSession,
    *,
    org_id: UUID | None = DEMO_ORG_ID,
    weeks: int = 8,
) -> list[dict[str, Any]]:
    weeks = max(1, min(weeks, 26))
    since = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    query = select(SafetyEvent).where(SafetyEvent.timestamp >= since)
    if org_id is not None:
        query = query.join(Vehicle, Vehicle.id == SafetyEvent.vehicle_id).where(
            Vehicle.org_id == org_id
        )
    events = list((await session.execute(query)).scalars().all())

    buckets: dict[str, dict[str, int]] = {}
    for event in events:
        week_start = (event.timestamp.date() - timedelta(days=event.timestamp.weekday())).isoformat()
        bucket = buckets.setdefault(
            week_start,
            {"week_start": week_start, "total": 0, "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        )
        bucket["total"] += 1
        sev = str(event.severity).upper()
        if sev in bucket:
            bucket[sev] += 1

    # Ensure empty weeks still appear for chart continuity.
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    for i in range(weeks):
        week = (current_monday - timedelta(weeks=i)).isoformat()
        buckets.setdefault(
            week,
            {"week_start": week, "total": 0, "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        )

    return sorted(buckets.values(), key=lambda item: item["week_start"])


async def driver_weekly(
    session: AsyncSession,
    driver_id: UUID,
    *,
    days: int = 7,
) -> dict[str, Any]:
    since = date.today() - timedelta(days=max(1, days) - 1)
    result = await session.execute(
        select(DriverScore)
        .where(DriverScore.driver_id == driver_id, DriverScore.date >= since)
        .order_by(DriverScore.date.asc())
    )
    rows = list(result.scalars().all())
    if not rows:
        return {
            "driver_id": str(driver_id),
            "safety_score": None,
            "events": {},
            "phase": PHASE,
            "message": "No driver_scores rows for this window",
        }
    latest = rows[-1]
    avg = sum(r.safety_score for r in rows) / len(rows)
    return {
        "driver_id": str(driver_id),
        "safety_score": round(avg, 1),
        "events": {
            "harsh_braking": latest.harsh_braking_count,
            "rapid_acceleration": latest.rapid_acceleration_count,
            "speeding": latest.speeding_events,
            "drowsiness": latest.drowsiness_events,
            "phone_usage": latest.phone_usage_events,
            "no_seatbelt": latest.no_seatbelt_events,
        },
        "sparkline": [r.safety_score for r in rows],
        "phase": PHASE,
    }
