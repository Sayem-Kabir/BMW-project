"""Spec Phase 9C — admin audit log + health aggregate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import engine, get_async_session
from app.core.security import ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN, normalize_role, require_roles
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])
PHASE = "9C"


@router.get("/audit")
async def list_audit(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    from app.core.hardening import page_meta

    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if normalize_role(user.role) != ROLE_SUPER_ADMIN and user.org_id is not None:
        query = query.where(AuditLog.org_id == user.org_id)
    rows_all = list((await session.execute(query.limit(limit + offset))).scalars().all())
    rows = rows_all[offset : offset + limit]
    return {
        "phase": PHASE,
        "count": len(rows),
        "pagination": page_meta(total=None, limit=limit, offset=offset),
        "items": [
            {
                "id": str(r.id),
                "user_id": str(r.user_id) if r.user_id else None,
                "org_id": str(r.org_id) if r.org_id else None,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": str(r.target_id) if r.target_id else None,
                "metadata": r.metadata_,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/health")
async def admin_health(
    _user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    db_ok = False
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False

    redis_ok = False
    try:
        from app.core import redis as redis_ops

        redis_ok = bool(await redis_ops.ping_redis())
    except Exception:  # noqa: BLE001
        redis_ok = False

    try:
        from app.core.metrics_custom import refresh_celery_queue_depth

        celery_queues = await refresh_celery_queue_depth()
    except Exception:  # noqa: BLE001
        celery_queues = {}

    return {
        "phase": PHASE,
        "environment": settings.environment,
        "database": "ok" if db_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
        "metrics_endpoint": "/metrics",
        "ready_endpoint": "/ready",
        "celery_queue_depth": celery_queues,
        "sentry": "configured" if (settings.sentry_dsn or "").strip() else "disabled",
        "mlflow_note": "Use MLflow UI when running locally (Phase 11 promote gates)",
    }
