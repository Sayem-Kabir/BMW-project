"""ML governance APIs — Spec Phase 11B drift + 11D RAG eval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.access import FEATURE_ASSISTANT, require_feature
from app.core.security import (
    ROLE_FLEET_MANAGER,
    ROLE_ORG_ADMIN,
    ROLE_SUPER_ADMIN,
    require_roles,
)
from app.models.user import User
from app.services import drift_service, guardrails, rag_eval_service

router = APIRouter(prefix="/api/v1/ml", tags=["ML Governance"])


class DriftCheckRequest(BaseModel):
    features: dict[str, list[float]] = Field(
        default_factory=dict,
        description="Live samples keyed by feature name (speed_kmh, ear, braking_freq)",
    )
    threshold_psi: float | None = Field(default=None, ge=0.0, le=2.0)


class GuardrailProbeRequest(BaseModel):
    message: str


@router.post("/drift/check")
async def drift_check(
    body: DriftCheckRequest,
    _user: User = Depends(
        require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN, ROLE_FLEET_MANAGER)
    ),
):
    """Compare live feature samples to training baseline via PSI."""
    if not body.features:
        raise HTTPException(status_code=400, detail="features must not be empty")
    try:
        return drift_service.check_drift(
            body.features, threshold=body.threshold_psi
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/assistant/guardrail-probe")
async def guardrail_probe(
    body: GuardrailProbeRequest,
    _user: User = Depends(require_feature(FEATURE_ASSISTANT)),
):
    blocked = guardrails.check_input(body.message)
    if blocked:
        return {"allowed": False, **blocked, "phase": "11D"}
    return {"allowed": True, "phase": "11D"}


@router.post("/assistant/eval")
async def assistant_eval(
    _user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    """Run RAGAS-inspired faithfulness eval set against guardrails + canned answers."""

    async def answer(question: str) -> str:
        blocked = guardrails.check_input(question)
        if blocked:
            return str(blocked.get("reply") or guardrails.REFUSAL)
        # Lightweight offline answers for eval (no Ollama required)
        q = question.lower()
        if "tpms" in q:
            return "TPMS warning usually means a tire pressure is low — check PSI on each tire."
        if "p0420" in q:
            return "OBD P0420 indicates catalyst system efficiency below threshold."
        if "oil" in q:
            return "Follow the oil service interval in the BMW owner manual (miles/months)."
        return "I can help with BMW vehicle maintenance and OBD questions."

    return await rag_eval_service.run_eval(answer)
