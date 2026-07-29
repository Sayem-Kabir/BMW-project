"""Explainable AI API — Modules 6F/6G Grad-CAM, SHAP; Module 8A Captum IG."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.common import XAIExplainRequest, XAIExplainResponse
from app.services import xai_service

router = APIRouter(prefix="/api/v1/xai", tags=["Explainable AI"])
PHASE = "6G"


@router.post("/explain", response_model=XAIExplainResponse)
async def explain(
    body: XAIExplainRequest,
    session: AsyncSession = Depends(get_async_session),
):
    result = await xai_service.explain(
        session,
        event_id=body.event_id,
        event_type=body.event_type,
        component=body.component,
        vehicle_id=body.vehicle_id,
    )
    return XAIExplainResponse(
        explanation=str(result["explanation"]),
        method=str(result["method"]),
        heatmap_url=result.get("heatmap_url"),
        ig_heatmap_url=result.get("ig_heatmap_url"),
        shap_values=result.get("shap_values"),
        rule_trace=result.get("rule_trace"),
        activation_mass=result.get("activation_mass"),
        attribution=result.get("attribution"),
        phase=str(result.get("phase") or PHASE),
    )


@router.post("/explain/frame", response_model=XAIExplainResponse)
async def explain_frame(
    event_type: str = Form(default="drowsiness"),
    event_id: UUID | None = Form(default=None),
    attribution: str = Form(default="gradcam"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Vision XAI. attribution: gradcam | ig | both (Module 8A)."""
    from app.core.uploads import read_upload_bytes

    frame_bytes = await read_upload_bytes(file)
    result = await xai_service.explain(
        session,
        event_id=event_id,
        event_type=event_type,
        frame_bytes=frame_bytes,
        attribution=attribution,
    )
    return XAIExplainResponse(
        explanation=str(result["explanation"]),
        method=str(result["method"]),
        heatmap_url=result.get("heatmap_url"),
        ig_heatmap_url=result.get("ig_heatmap_url"),
        shap_values=result.get("shap_values"),
        rule_trace=result.get("rule_trace"),
        activation_mass=result.get("activation_mass"),
        attribution=result.get("attribution"),
        phase=str(result.get("phase") or PHASE),
    )


@router.get("/heatmap/{filename}")
async def get_heatmap(filename: str):
    path = xai_service.resolve_heatmap_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Heatmap not found")
    return FileResponse(path, media_type="image/jpeg", filename=Path(path).name)
