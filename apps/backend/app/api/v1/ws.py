"""Fleet WebSocket fan-out — Module 4C Redis ``risk:*`` distribution."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import risk_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/api/v1/fleet/ws/{org_id}")
async def fleet_ws(websocket: WebSocket, org_id: UUID):
    """Push Redis risk updates to connected fleet dashboard clients.

    Clients may send ``ping`` text frames; everything else is ignored.
    Organization scoping is reserved for later fleet auth work — every
    connected client currently receives the ``risk:*`` stream.
    """
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "connected",
            "org_id": str(org_id),
            "message": "Fleet WebSocket listening for Redis risk:* updates",
            "pattern": risk_service.RISK_PATTERN,
            "phase": risk_service.PHASE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    stop = asyncio.Event()

    async def pump_redis() -> None:
        backoff_seconds = 2
        while not stop.is_set():
            try:
                async for message in risk_service.iter_risk_messages():
                    if stop.is_set():
                        break
                    backoff_seconds = 2
                    await websocket.send_json(
                        {
                            "type": "risk_update",
                            "org_id": str(org_id),
                            "channel": message.get("channel"),
                            "data": message["data"],
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "phase": risk_service.PHASE,
                        }
                    )
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                from app.core.redis import reset_redis

                await reset_redis()
                logger.warning(
                    "Fleet risk Redis pump unavailable for org %s; retrying in %ss",
                    org_id,
                    backoff_seconds,
                )
                if stop.is_set():
                    break
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "detail": "Redis risk subscription unavailable — retrying",
                            "phase": risk_service.PHASE,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                except Exception:  # noqa: BLE001
                    break
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 15)

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
                        "phase": risk_service.PHASE,
                    }
                )

    redis_task = asyncio.create_task(pump_redis(), name=f"fleet-risk-{org_id}")
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
