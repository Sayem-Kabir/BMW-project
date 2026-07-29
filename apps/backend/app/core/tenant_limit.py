"""FastAPI dependency: per-tenant rate limit using JWT org_id."""

from __future__ import annotations

from fastapi import Depends, Request

from app.core.rate_limit import enforce_tenant_rate
from app.core.security import require_user
from app.models.user import User


async def tenant_rate_limit(
    request: Request,
    user: User = Depends(require_user),
) -> User:
    await enforce_tenant_rate(
        request, str(user.org_id) if user.org_id else f"user:{user.id}"
    )
    return user
