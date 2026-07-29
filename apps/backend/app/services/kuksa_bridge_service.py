"""Module 8B — Live Kuksa bridge: poll databroker → SQL → optional risk refresh."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.services import kuksa_service, risk_service

logger = logging.getLogger(__name__)

PHASE = "8B"
DEMO_VEHICLE = UUID("00000000-0000-4000-8000-000000000003")

_state: dict[str, Any] = {
    "running": False,
    "vehicle_id": None,
    "updates": 0,
    "last_error": None,
    "last_snapshot": None,
    "started_at": None,
    "task": None,
}


def bridge_status() -> dict[str, Any]:
    return {
        "running": bool(_state["running"]),
        "vehicle_id": _state.get("vehicle_id"),
        "updates": int(_state.get("updates") or 0),
        "last_error": _state.get("last_error"),
        "last_snapshot": _state.get("last_snapshot"),
        "started_at": _state.get("started_at"),
        "phase": PHASE,
    }


async def _bridge_loop(
    vehicle_id: UUID,
    *,
    interval_s: float,
    feed_risk: bool,
    max_updates: int | None,
) -> None:
    _state["running"] = True
    _state["vehicle_id"] = str(vehicle_id)
    _state["updates"] = 0
    _state["last_error"] = None
    _state["started_at"] = datetime.now(timezone.utc).isoformat()
    try:
        while _state["running"]:
            try:
                await kuksa_service.run_kuksa_subscription(vehicle_id, max_updates=1)
                snap = await kuksa_service.get_kuksa_snapshot(vehicle_id)
                ctx = snap.as_context_dict()
                _state["last_snapshot"] = {
                    "speed_kmh": ctx.get("speed_kmh"),
                    "latitude": ctx.get("latitude"),
                    "longitude": ctx.get("longitude"),
                    "battery_soc_pct": ctx.get("battery_soc_pct"),
                    "rpm": ctx.get("rpm"),
                    "timestamp": (
                        ctx["timestamp"].isoformat()
                        if hasattr(ctx.get("timestamp"), "isoformat")
                        else ctx.get("timestamp")
                    ),
                }
                _state["updates"] = int(_state["updates"]) + 1
                if feed_risk:
                    await risk_service.evaluate_and_publish(
                        vehicle_id,
                        telemetry=ctx,
                        publish=True,
                        cache=True,
                        persist=True,
                    )
            except Exception as exc:  # noqa: BLE001
                _state["last_error"] = str(exc)
                logger.warning("Kuksa bridge tick failed: %s", exc)

            if max_updates is not None and int(_state["updates"]) >= max_updates:
                break
            await asyncio.sleep(max(0.5, interval_s))
    finally:
        _state["running"] = False
        _state["task"] = None


async def start_bridge(
    *,
    vehicle_id: UUID | str | None = None,
    interval_s: float = 2.0,
    feed_risk: bool = True,
    max_updates: int | None = None,
) -> dict[str, Any]:
    if _state["running"] and _state.get("task"):
        return bridge_status()

    vid = UUID(str(vehicle_id or DEMO_VEHICLE))
    task = asyncio.create_task(
        _bridge_loop(
            vid,
            interval_s=interval_s,
            feed_risk=feed_risk,
            max_updates=max_updates,
        ),
        name="kuksa-bridge-8b",
    )
    _state["task"] = task
    await asyncio.sleep(0.05)
    return bridge_status()


async def stop_bridge() -> dict[str, Any]:
    _state["running"] = False
    task = _state.get("task")
    if task and not task.done():
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=3.0)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):  # noqa: BLE001
            task.cancel()
    _state["task"] = None
    return bridge_status()
