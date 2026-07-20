"""Module 4C — risk evaluation publish/cache adapter over Modules 4A/4B."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core import redis as redis_ops
from app.models.risk_score import RiskScoreRecord

logger = logging.getLogger(__name__)

RISK_CHANNEL_PREFIX = "risk:"
RISK_PATTERN = "risk:*"
RISK_CACHE_PREFIX = "risk:latest:"
RISK_CACHE_TTL_SECONDS = 300
PHASE = "4F"


def risk_channel(vehicle_id: UUID | str) -> str:
    return f"{RISK_CHANNEL_PREFIX}{vehicle_id}"


def risk_cache_key(vehicle_id: UUID | str) -> str:
    return f"{RISK_CACHE_PREFIX}{vehicle_id}"


def evaluate_risk(
    vehicle_id: UUID | str,
    driver_state: Mapping[str, Any] | None = None,
    road_state: Mapping[str, Any] | None = None,
    telemetry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the pure 4A/4B decision path and normalize the Redis payload."""
    from ml.risk_engine import compute_risk_with_overrides

    decision = compute_risk_with_overrides(
        str(vehicle_id),
        driver_state,
        road_state,
        telemetry,
    )
    payload = decision.to_dict()
    # Spec aliases used by fleet WebSocket consumers.
    payload["risk_score"] = payload["score"]
    payload["risk_level"] = payload["level"]
    payload["phase"] = PHASE
    return payload


async def evaluate_and_publish(
    vehicle_id: UUID | str,
    driver_state: Mapping[str, Any] | None = None,
    road_state: Mapping[str, Any] | None = None,
    telemetry: Mapping[str, Any] | None = None,
    *,
    publish: bool = True,
    cache: bool = True,
    persist: bool = True,
    session: Any | None = None,
) -> dict[str, Any]:
    """Evaluate risk, optionally cache/publish, and optionally persist history."""
    payload = await asyncio.to_thread(
        evaluate_risk,
        vehicle_id,
        driver_state,
        road_state,
        telemetry,
    )
    receivers = 0
    cached = False
    persisted = False

    if persist:
        try:
            if session is None:
                from app.core.database import async_session_maker

                async with async_session_maker() as owned_session:
                    row = await persist_risk_score(owned_session, vehicle_id, payload)
            else:
                row = await persist_risk_score(session, vehicle_id, payload)
            persisted = row is not None
            payload["persisted"] = persisted
            if row is not None:
                payload["record_id"] = str(row.id)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist risk score for %s", vehicle_id)
            payload["persist_warning"] = "Risk history persistence unavailable"

    if cache:
        try:
            await redis_ops.cache_json_set(
                risk_cache_key(vehicle_id),
                payload,
                RISK_CACHE_TTL_SECONDS,
            )
            cached = True
        except Exception:  # noqa: BLE001 — inference still useful without cache
            logger.warning("Failed to cache risk result for %s", vehicle_id)

    if publish:
        try:
            receivers = await redis_ops.publish_json(
                risk_channel(vehicle_id),
                payload,
            )
        except Exception:  # noqa: BLE001 — inference still useful without Redis
            logger.warning("Failed to publish risk result for %s", vehicle_id)
            payload = {
                **payload,
                "published": False,
                "receivers": 0,
                "cached": cached,
                "persisted": persisted,
                "warning": "Redis publish unavailable",
            }
            return payload

    payload = {
        **payload,
        "published": bool(publish),
        "receivers": int(receivers),
        "cached": cached,
        "persisted": persisted,
    }
    return payload


async def persist_risk_score(
    session: Any,
    vehicle_id: UUID | str,
    payload: Mapping[str, Any],
) -> RiskScoreRecord | None:
    moment = payload.get("timestamp")
    if isinstance(moment, str):
        evaluated_at = datetime.fromisoformat(moment)
    elif isinstance(moment, datetime):
        evaluated_at = moment
    else:
        evaluated_at = datetime.now(timezone.utc)
    if evaluated_at.tzinfo is None:
        evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)

    row = RiskScoreRecord(
        vehicle_id=UUID(str(vehicle_id)),
        score=float(payload.get("score", 0.0)),
        level=str(payload.get("level", "LOW")),
        payload=dict(payload),
        timestamp=evaluated_at,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_risk_history(
    session: Any,
    vehicle_id: UUID | str,
    *,
    limit: int = 100,
) -> list[RiskScoreRecord]:
    from sqlalchemy import select

    result = await session.execute(
        select(RiskScoreRecord)
        .where(RiskScoreRecord.vehicle_id == UUID(str(vehicle_id)))
        .order_by(RiskScoreRecord.timestamp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def evaluate_persist_and_publish(
    vehicle_id: UUID | str,
    driver_state: Mapping[str, Any] | None = None,
    road_state: Mapping[str, Any] | None = None,
    telemetry: Mapping[str, Any] | None = None,
    *,
    publish: bool = True,
    cache: bool = True,
) -> dict[str, Any]:
    """Celery/back-office entry point for one full 4F risk evaluation."""
    return await evaluate_and_publish(
        vehicle_id,
        driver_state,
        road_state,
        telemetry,
        publish=publish,
        cache=cache,
        persist=True,
    )


async def get_cached_risk(
    vehicle_id: UUID | str,
    session: Any | None = None,
) -> dict[str, Any] | None:
    try:
        cached = await redis_ops.cache_json_get(risk_cache_key(vehicle_id))
        if cached is not None:
            return cached
    except Exception:  # noqa: BLE001
        logger.warning("Redis cache read failed for %s; trying database fallback", vehicle_id)

    if session is None:
        return None
    return await get_latest_persisted_risk(session, vehicle_id)


async def get_latest_persisted_risk(
    session: Any,
    vehicle_id: UUID | str,
) -> dict[str, Any] | None:
    rows = await list_risk_history(session, vehicle_id, limit=1)
    if not rows:
        return None
    row = rows[0]
    payload = dict(row.payload or {})
    payload["vehicle_id"] = str(vehicle_id)
    payload["score"] = float(row.score)
    payload["level"] = str(row.level)
    payload["risk_score"] = float(row.score)
    payload["risk_level"] = str(row.level)
    payload["timestamp"] = row.timestamp.isoformat()
    payload["phase"] = PHASE
    payload["source"] = "database"
    payload.pop("message", None)
    return payload


def empty_risk_payload(vehicle_id: UUID | str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "vehicle_id": str(vehicle_id),
        "score": 0.0,
        "level": "LOW",
        "risk_score": 0.0,
        "risk_level": "LOW",
        "base_score": 0.0,
        "base_level": "LOW",
        "factors": [],
        "overrides": [],
        "reasons": [],
        "timestamp": now.isoformat(),
        "method": "none",
        "phase": PHASE,
        "message": "No recent risk score cached",
    }


async def iter_risk_messages() -> AsyncIterator[dict[str, Any]]:
    """Yield parsed risk payloads from the Redis ``risk:*`` pattern."""
    async for message in redis_ops.iter_pattern_messages(RISK_PATTERN):
        raw = message.get("data")
        if raw is None:
            continue
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if not isinstance(raw, str):
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Ignoring non-JSON risk message on %s", message.get("channel"))
            continue
        if not isinstance(payload, dict):
            continue
        yield {
            "channel": message.get("channel"),
            "pattern": message.get("pattern"),
            "data": payload,
        }
