"""Model registry API — Spec Phase 11A (MLflow staging → production + eval gate)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN, require_roles
from app.models.user import User
from app.services import auth_service, ml_registry_service

router = APIRouter(prefix="/api/v1/models", tags=["Model Registry"])
PHASE = "11A"


class PromoteRequest(BaseModel):
    target_stage: str = Field(default="Production")
    version: str | None = None
    # Callers may set a higher bar; production always enforces >= 0.80
    min_eval_metric: float | None = Field(default=None, ge=0.0, le=1.0)
    eval_metric_value: float = Field(default=0.9, ge=0.0, le=1.0)


@router.get("")
async def list_models(
    _user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    return {"models": ml_registry_service.list_registered_models(), "phase": PHASE}


@router.get("/{name}/versions")
async def model_versions(
    name: str,
    _user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    versions = ml_registry_service.list_versions(name.strip())
    if not versions and name.strip() not in {
        m["name"] for m in ml_registry_service.list_registered_models()
    }:
        raise HTTPException(status_code=404, detail=f"Unknown model {name!r}")
    return {"name": name.strip(), "versions": versions, "phase": PHASE}


@router.post("/{name}/promote")
async def promote_model(
    name: str,
    body: PromoteRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    """Gate stage transition behind eval metric; prefer MLflow when available."""
    try:
        result = ml_registry_service.promote(
            name.strip(),
            target_stage=body.target_stage,
            version=body.version,
            eval_metric_value=body.eval_metric_value,
            min_eval_metric=body.min_eval_metric,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await auth_service.write_audit(
        session,
        action="MODEL_PROMOTED",
        user=user,
        target_type="models",
        target_id=None,
        metadata={
            "model": result["name"],
            "version": result.get("version"),
            "from_stage": result.get("previous_stage"),
            "to_stage": result.get("stage"),
            "eval_metric_value": result.get("eval_metric_value"),
            "min_eval_metric": result.get("min_eval_metric"),
            "source": result.get("source"),
        },
    )
    await session.commit()
    return result
