"""Spec Phase 8C/8E — org user invite and role management."""

from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import (
    ROLE_ORG_ADMIN,
    ROLE_SUPER_ADMIN,
    SPEC_ROLES,
    get_password_hash,
    normalize_role,
    require_roles,
)
from app.models.user import User
from app.schemas.auth import InviteUserRequest, RoleChangeRequest, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/api/v1/orgs", tags=["Organizations"])


@router.get("/{org_id}/users", response_model=list[UserResponse])
async def list_org_users(
    org_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN, "fleet_manager")),
):
    if normalize_role(user.role) != ROLE_SUPER_ADMIN and user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Wrong organization")
    result = await session.execute(select(User).where(User.org_id == org_id))
    return list(result.scalars().all())


@router.post("/{org_id}/users/invite", response_model=UserResponse, status_code=201)
async def invite_user(
    org_id: UUID,
    body: InviteUserRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    if normalize_role(user.role) != ROLE_SUPER_ADMIN and user.org_id != org_id:
        raise HTTPException(status_code=403, detail="Wrong organization")
    role = normalize_role(body.role)
    if role not in SPEC_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    temp_password = secrets.token_urlsafe(10)
    invited = User(
        email=body.email,
        hashed_password=get_password_hash(temp_password),
        full_name=body.full_name,
        org_id=org_id,
        role=role,
        is_email_verified=True,
        is_active=True,
    )
    session.add(invited)
    await session.flush()
    await auth_service.write_audit(
        session,
        action="USER_INVITED",
        user=user,
        target_type="users",
        target_id=invited.id,
        metadata={"email": body.email, "role": role, "temp_password": temp_password},
    )
    await session.commit()
    await session.refresh(invited)
    return invited


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_role(
    user_id: UUID,
    body: RoleChangeRequest,
    session: AsyncSession = Depends(get_async_session),
    actor: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    role = normalize_role(body.role)
    if role not in SPEC_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
    result = await session.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if normalize_role(actor.role) != ROLE_SUPER_ADMIN and target.org_id != actor.org_id:
        raise HTTPException(status_code=403, detail="Wrong organization")
    old = target.role
    target.role = role
    await auth_service.write_audit(
        session,
        action="ROLE_CHANGED",
        user=actor,
        target_type="users",
        target_id=target.id,
        metadata={"from": old, "to": role},
    )
    await session.commit()
    await session.refresh(target)
    return target
