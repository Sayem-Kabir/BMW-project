"""Module 6F/6G — XAI orchestration for events, Grad-CAM, and SHAP panels."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import SafetyEvent
from app.models.maintenance import MaintenancePrediction

logger = logging.getLogger(__name__)

PHASE = "6G"
GRADCAM_PHASE = "6F"
IG_PHASE = "8A"


def _xai():
    from ml.xai import (
        compose_nl_explanation,
        generate_gradcam,
        generate_integrated_gradients,
        shap_plot_base64_from_top_features,
        shap_waterfall_ascii,
    )
    from ml.xai.gradcam import DEFAULT_HEATMAP_DIR

    return (
        compose_nl_explanation,
        generate_gradcam,
        generate_integrated_gradients,
        shap_plot_base64_from_top_features,
        shap_waterfall_ascii,
        DEFAULT_HEATMAP_DIR,
    )


def resolve_heatmap_path(filename: str) -> Path | None:
    _, _, _, _, _, heatmap_dir = _xai()
    safe = Path(filename).name
    path = heatmap_dir / safe
    if path.is_file():
        return path
    return None


async def explain(
    session: AsyncSession,
    *,
    event_id: UUID | None = None,
    event_type: str | None = None,
    frame_bytes: bytes | None = None,
    component: str | None = None,
    vehicle_id: UUID | None = None,
    attribution: str = "gradcam",
) -> dict[str, Any]:
    heatmap_url = None
    ig_heatmap_url = None
    visual = None
    method_parts: list[str] = []
    shap_values: dict[str, Any] | None = None
    rule_trace: dict[str, Any] | None = None
    evidence: list[str] = []
    resolved_type = event_type or "safety_event"
    used_gradcam = False
    used_ig = False
    activation_mass: float | None = None
    attr = (attribution or "gradcam").strip().lower()
    if attr not in {"gradcam", "ig", "both"}:
        attr = "gradcam"

    (
        compose_nl_explanation,
        generate_gradcam,
        generate_integrated_gradients,
        shap_plot_base64_from_top_features,
        shap_waterfall_ascii,
        _,
    ) = _xai()

    if event_id is not None:
        result = await session.execute(select(SafetyEvent).where(SafetyEvent.id == event_id))
        event = result.scalar_one_or_none()
        if event is not None:
            resolved_type = event.event_type
            if event.xai_explanation:
                evidence.append(event.xai_explanation)
            rule_trace = {
                "event_type": event.event_type,
                "severity": event.severity,
                "telemetry_snapshot": event.telemetry_snapshot,
            }
            method_parts.append("rule_template")

    if frame_bytes:
        import cv2

        arr = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is not None:
            if attr in {"gradcam", "both"}:
                cam = generate_gradcam(frame, event_type=resolved_type)
                heatmap_url = cam.heatmap_url
                visual = cam.description
                method_parts.append(cam.method)
                used_gradcam = True
                activation_mass = cam.activation_mass
            if attr in {"ig", "both"}:
                ig = generate_integrated_gradients(frame, event_type=resolved_type)
                ig_heatmap_url = ig.heatmap_url
                method_parts.append(ig.method)
                used_ig = True
                if activation_mass is None:
                    activation_mass = ig.activation_mass
                if not visual:
                    visual = ig.description
                elif attr == "both":
                    visual = f"{visual} | {ig.description}"
            if attr == "ig" and heatmap_url is None:
                heatmap_url = ig_heatmap_url
        else:
            evidence.append("Uploaded frame could not be decoded for vision XAI.")

    if vehicle_id is not None and component:
        pred = await session.execute(
            select(MaintenancePrediction)
            .where(
                MaintenancePrediction.vehicle_id == vehicle_id,
                MaintenancePrediction.component == component,
            )
            .order_by(MaintenancePrediction.created_at.desc())
            .limit(1)
        )
        row = pred.scalar_one_or_none()
    elif vehicle_id is not None and not frame_bytes and event_id is None:
        # Latest maintenance row with any SHAP payload for vehicle-scoped explain.
        pred = await session.execute(
            select(MaintenancePrediction)
            .where(MaintenancePrediction.vehicle_id == vehicle_id)
            .order_by(MaintenancePrediction.created_at.desc())
            .limit(8)
        )
        row = None
        for candidate in pred.scalars().all():
            if candidate.shap_explanation:
                row = candidate
                break
    else:
        row = None

    if row is not None and row.shap_explanation:
        explanation = row.shap_explanation.get("explanation") or {}
        if not isinstance(explanation, dict):
            explanation = {}
        top = (
            explanation.get("top_features")
            or row.shap_explanation.get("top_features")
            or []
        )
        if isinstance(top, tuple):
            top = list(top)
        plot_b64 = shap_plot_base64_from_top_features(top) if top else None
        shap_values = {
            "component": row.component,
            "health_score": row.health_score,
            "top_features": top,
            "waterfall_ascii": shap_waterfall_ascii(top),
            "shap_plot_base64": plot_b64,
        }
        method_parts.append("xgboost_pred_contribs")
        resolved_type = f"maintenance_{row.component}"
        severity = row.shap_explanation.get("severity")
        if severity:
            evidence.append(
                f"{row.component} health={float(row.health_score):.0%} severity={severity}"
            )

    if not evidence and not visual and not shap_values:
        evidence.append(
            "No persisted event, frame, or maintenance SHAP payload was provided."
        )

    vehicle_state = None
    if rule_trace and isinstance(rule_trace.get("telemetry_snapshot"), dict):
        vehicle_state = rule_trace["telemetry_snapshot"]

    explanation = compose_nl_explanation(
        event_type=resolved_type,
        evidence=evidence,
        visual_description=visual,
        shap_top=(shap_values or {}).get("top_features") if shap_values else None,
        vehicle_state=vehicle_state,
    )

    return {
        "explanation": explanation,
        "method": "+".join(method_parts) or "template",
        "heatmap_url": heatmap_url,
        "ig_heatmap_url": ig_heatmap_url,
        "shap_values": shap_values,
        "rule_trace": rule_trace,
        "activation_mass": activation_mass,
        "attribution": attr if frame_bytes else None,
        "phase": IG_PHASE if used_ig and not used_gradcam else (
            GRADCAM_PHASE if used_gradcam else PHASE
        ),
    }
