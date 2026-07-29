"""Spec Phase 8D — org / driver row-level scoping helpers."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.core.security import ROLE_DRIVER, ROLE_SUPER_ADMIN, normalize_role
from app.models.user import User
from app.services import fleet_service

DEMO_ORG = fleet_service.DEMO_ORG_ID


def resolve_org_id(
    org_id: UUID | None,
    user: User | None,
    *,
    allow_demo_fallback: bool = True,
) -> UUID | None:
    """Authenticated users are locked to their org; query org_id cannot escalate."""
    if user is not None:
        role = normalize_role(user.role)
        if role == ROLE_SUPER_ADMIN and org_id is not None:
            return org_id
        if user.org_id is not None:
            if org_id is not None and org_id != user.org_id and role != ROLE_SUPER_ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access another organization's data",
                )
            return user.org_id
    if org_id is not None:
        return org_id
    if allow_demo_fallback and user is None:
        return DEMO_ORG
    return None


def driver_scope_id(user: User | None) -> UUID | None:
    """When role is driver, restrict to linked driver_id."""
    if user is None:
        return None
    if normalize_role(user.role) != ROLE_DRIVER:
        return None
    return user.driver_id
