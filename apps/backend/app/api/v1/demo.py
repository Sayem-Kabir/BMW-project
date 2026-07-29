"""Demo Mode API — Module 7C start/stop/status; Module 8E write-role guard."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.access import FEATURE_DEMO, require_feature
from app.models.user import User
from app.services import demo_service

router = APIRouter(prefix="/api/v1/demo", tags=["Demo Mode"])
PHASE = "7C"


class DemoStartRequest(BaseModel):
    vehicle_id: str = Field(default="00000000-0000-4000-8000-000000000003")
    fps: float = Field(default=4.0, ge=0.5, le=15.0)
    synthetic_only: bool = True
    loop: bool = True
    max_frames: int | None = Field(default=None, ge=1, le=5000)


@router.get("/status")
async def demo_status(
    _user: User = Depends(require_feature(FEATURE_DEMO)),
):
    return demo_service.status_demo()


@router.post("/start")
async def demo_start(
    body: DemoStartRequest | None = None,
    _user: User = Depends(require_feature(FEATURE_DEMO)),
):
    payload = body or DemoStartRequest()
    result = await demo_service.start_demo(
        vehicle_id=payload.vehicle_id,
        fps=payload.fps,
        synthetic_only=payload.synthetic_only,
        loop=payload.loop,
        max_frames=payload.max_frames,
    )
    result["phase"] = PHASE
    return result


@router.post("/stop")
async def demo_stop(
    _user: User = Depends(require_feature(FEATURE_DEMO)),
):
    result = await demo_service.stop_demo()
    result["phase"] = PHASE
    return result
