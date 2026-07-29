"""Module 8B — Live Kuksa bridge control API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import require_operator_for_writes
from app.models.user import User
from app.services import kuksa_bridge_service, kuksa_service

router = APIRouter(prefix="/api/v1/kuksa", tags=["Kuksa Bridge"])
PHASE = "8B"


class BridgeStartRequest(BaseModel):
    vehicle_id: UUID | None = None
    interval_s: float = Field(default=2.0, ge=0.5, le=60.0)
    feed_risk: bool = True
    max_updates: int | None = Field(default=None, ge=1, le=10_000)


@router.get("/bridge/status")
async def bridge_status():
    return kuksa_bridge_service.bridge_status()


@router.post("/bridge/start")
async def bridge_start(
    body: BridgeStartRequest | None = None,
    _user: User | None = Depends(require_operator_for_writes),
):
    body = body or BridgeStartRequest()
    return await kuksa_bridge_service.start_bridge(
        vehicle_id=body.vehicle_id,
        interval_s=body.interval_s,
        feed_risk=body.feed_risk,
        max_updates=body.max_updates,
    )


@router.post("/bridge/stop")
async def bridge_stop(
    _user: User | None = Depends(require_operator_for_writes),
):
    return await kuksa_bridge_service.stop_bridge()


@router.get("/snapshot/{vehicle_id}")
async def kuksa_snapshot(vehicle_id: UUID):
    try:
        snap = await kuksa_service.get_kuksa_snapshot(vehicle_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Kuksa unavailable: {exc}") from exc
    data = snap.as_context_dict()
    # JSON-safe timestamp
    ts = data.get("timestamp")
    if hasattr(ts, "isoformat"):
        data["timestamp"] = ts.isoformat()
    return {"phase": PHASE, **data}
