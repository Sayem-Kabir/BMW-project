"""Cabin Intelligence API — Module 02 (seat occupancy, child heuristic, unattended)."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.access import FEATURE_MONITOR, require_feature
from app.core.uploads import read_upload_bytes
from app.models.user import User
from app.schemas.common import CabinOccupancyResponse
from app.services import cabin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cabin", tags=["Cabin Intelligence"])


@router.post("/analysis", response_model=CabinOccupancyResponse)
async def analyze_cabin(
    file: UploadFile = File(...),
    _user: User = Depends(require_feature(FEATURE_MONITOR)),
):
    """Analyze cabin occupancy from a single JPEG/PNG frame."""
    image_bytes = await read_upload_bytes(file)
    try:
        raw = await asyncio.to_thread(cabin_service.analyze_frame_bytes, image_bytes)
        try:
            from app.core.metrics_custom import observe_inference

            observe_inference("cabin", 0.05)
        except Exception:  # noqa: BLE001
            pass
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Cabin analysis failed")
        raise HTTPException(status_code=503, detail=f"Cabin pipeline unavailable: {exc}") from exc
    return CabinOccupancyResponse(**raw)
