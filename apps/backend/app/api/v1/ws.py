"""Fleet WebSocket fan-out — Modules 4C/6A + Spec Phase 13 throttle/org filter."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core import redis as redis_ops
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.vehicle import Vehicle
from app.services import event_service, risk_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])
PHASE = "13"
PATTERNS = (
    risk_service.RISK_PATTERN,
    event_service.EVENT_PATTERN,
    event_service.MAINTENANCE_PATTERN,
)


def _parse_payload(raw: object) -> dict | None:
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    if not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _frame_type(channel: str | None) -> str:
    ch = str(channel or "")
    if ch.startswith("events:"):
        return "safety_event"
    if ch.startswith("maintenance:"):
        return "maintenance_alert"
    return "risk_update"


def _vehicle_id_from_payload(payload: dict, channel: str | None) -> str | None:
    for key in ("vehicle_id", "vehicleId"):
        val = payload.get(key)
        if val:
            return str(val)
    ch = str(channel or "")
    for prefix in ("risk:", "events:", "maintenance:"):
        if ch.startswith(prefix) and len(ch) > len(prefix):
            return ch[len(prefix) :]
    return None


async def _org_vehicle_ids(org_id: UUID) -> set[str] | None:
    """Return vehicle IDs for org, or None if lookup failed (fail-open)."""
    try:
        async with async_session_maker() as session:
            rows = (
                await session.execute(
                    select(Vehicle.id).where(Vehicle.org_id == org_id)
                )
            ).scalars().all()
            return {str(vid) for vid in rows}
    except Exception:  # noqa: BLE001
        logger.warning("org vehicle filter unavailable for %s — fail-open", org_id)
        return None


class _RateLimiter:
    """Allow at most ``max_hz`` sends per second (Phase 13 WS throttle)."""

    def __init__(self, max_hz: float) -> None:
        self.min_interval = 1.0 / max(0.1, float(max_hz))
        self._last = 0.0

    def allow(self) -> bool:
        now = time.monotonic()
        if now - self._last >= self.min_interval:
            self._last = now
            return True
        return False


@router.websocket("/api/v1/fleet/ws/{org_id}")
async def fleet_ws(websocket: WebSocket, org_id: UUID):
    """Push Redis risk/events/maintenance updates to fleet dashboard clients."""
    await websocket.accept()
    vehicle_ids = await _org_vehicle_ids(org_id)
    limiter = _RateLimiter(settings.ws_max_hz)

    await websocket.send_json(
        {
            "type": "connected",
            "org_id": str(org_id),
            "message": "Fleet WebSocket listening for risk:*, events:*, maintenance:*",
            "patterns": list(PATTERNS),
            "phase": PHASE,
            "ws_max_hz": settings.ws_max_hz,
            "org_filter": vehicle_ids is not None,
            "org_vehicle_count": len(vehicle_ids) if vehicle_ids is not None else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    stop = asyncio.Event()

    async def pump_redis() -> None:
        backoff_seconds = 2
        while not stop.is_set():
            client = None
            pubsub = None
            try:
                client = await redis_ops.get_redis()
                pubsub = client.pubsub()
                for pattern in PATTERNS:
                    await pubsub.psubscribe(pattern)
                backoff_seconds = 2
                async for message in pubsub.listen():
                    if stop.is_set():
                        break
                    if message.get("type") != "pmessage":
                        continue
                    channel = message.get("channel")
                    payload = _parse_payload(message.get("data"))
                    if payload is None:
                        continue
                    vid = _vehicle_id_from_payload(
                        payload, str(channel) if channel else None
                    )
                    if (
                        vehicle_ids is not None
                        and vid is not None
                        and vid not in vehicle_ids
                    ):
                        continue
                    if not limiter.allow():
                        continue
                    await websocket.send_json(
                        {
                            "type": _frame_type(str(channel) if channel else None),
                            "org_id": str(org_id),
                            "channel": channel,
                            "data": payload,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "phase": PHASE,
                        }
                    )
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                await redis_ops.reset_redis()
                logger.warning(
                    "Fleet Redis pump unavailable for org %s; retrying in %ss",
                    org_id,
                    backoff_seconds,
                )
                if stop.is_set():
                    break
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "detail": "Redis fleet subscription unavailable — retrying",
                            "phase": PHASE,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                except Exception:  # noqa: BLE001
                    break
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 15)
            finally:
                if pubsub is not None:
                    try:
                        for pattern in PATTERNS:
                            await pubsub.punsubscribe(pattern)
                    except Exception:  # noqa: BLE001
                        pass
                    try:
                        await pubsub.aclose()
                    except Exception:  # noqa: BLE001
                        pass

    async def pump_client() -> None:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            text = message.get("text")
            if text is None:
                continue
            if text.strip().lower() in {"ping", "pong"}:
                await websocket.send_json(
                    {
                        "type": "pong",
                        "org_id": str(org_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "phase": PHASE,
                    }
                )

    redis_task = asyncio.create_task(pump_redis(), name=f"fleet-ws-{org_id}")
    try:
        await pump_client()
    except WebSocketDisconnect:
        return
    finally:
        stop.set()
        redis_task.cancel()
        try:
            await redis_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
