"""Notifications API — Spec Phase 12A preferences + webhooks."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import (
    ROLE_FLEET_MANAGER,
    ROLE_ORG_ADMIN,
    ROLE_SUPER_ADMIN,
    require_roles,
    require_user,
)
from app.models.notification import NotificationPreference, NotificationWebhook
from app.models.user import User
from app.services import notification_service

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])
PHASE = "12A"


class PreferencesUpdate(BaseModel):
    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    push_enabled: bool | None = None
    critical_only: bool | None = None
    phone_e164: str | None = None


class WebhookCreate(BaseModel):
    url: HttpUrl
    secret: str | None = Field(default=None, max_length=100)
    org_id: UUID | None = None


@router.get("/preferences")
async def get_preferences(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_user),
):
    row = (
        await session.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user.id)
        )
    ).scalar_one_or_none()
    if row is None:
        return {
            "user_id": str(user.id),
            "email_enabled": True,
            "sms_enabled": False,
            "push_enabled": True,
            "critical_only": True,
            "phone_e164": None,
            "phase": PHASE,
        }
    return {
        "user_id": str(user.id),
        "email_enabled": row.email_enabled,
        "sms_enabled": row.sms_enabled,
        "push_enabled": row.push_enabled,
        "critical_only": row.critical_only,
        "phone_e164": row.phone_e164,
        "phase": PHASE,
    }


@router.patch("/preferences")
async def patch_preferences(
    body: PreferencesUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_user),
):
    row = (
        await session.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user.id)
        )
    ).scalar_one_or_none()
    if row is None:
        row = NotificationPreference(user_id=user.id)
        session.add(row)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    await session.commit()
    return await get_preferences(session=session, user=user)


@router.post("/webhooks", status_code=201)
async def create_webhook(
    body: WebhookCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(
        require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN, ROLE_FLEET_MANAGER)
    ),
):
    hook = NotificationWebhook(
        id=uuid4(),
        org_id=body.org_id or user.org_id,
        url=str(body.url),
        secret=body.secret,
        active=True,
        created_by=user.id,
    )
    session.add(hook)
    await session.commit()
    return {
        "id": str(hook.id),
        "url": hook.url,
        "org_id": str(hook.org_id) if hook.org_id else None,
        "active": hook.active,
        "phase": PHASE,
    }


@router.get("/webhooks")
async def list_webhooks(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(
        require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN, ROLE_FLEET_MANAGER)
    ),
):
    q = select(NotificationWebhook)
    if user.org_id is not None:
        q = q.where(NotificationWebhook.org_id == user.org_id)
    rows = list((await session.execute(q)).scalars().all())
    return {
        "webhooks": [
            {
                "id": str(r.id),
                "url": r.url,
                "org_id": str(r.org_id) if r.org_id else None,
                "active": r.active,
            }
            for r in rows
        ],
        "phase": PHASE,
    }


@router.post("/test/critical")
async def test_critical_notify(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    """Fire a synthetic CRITICAL notification (demo / exit criterion)."""
    result = await notification_service.notify_critical_safety_event(
        session,
        event={
            "id": "00000000-0000-4000-8000-00000000test",
            "event_type": "near_collision",
            "severity": "CRITICAL",
            "vehicle_id": "00000000-0000-4000-8000-000000000003",
            "timestamp": "2026-07-26T00:00:00Z",
            "xai_explanation": "Phase 12A synthetic critical alert",
        },
        org_id=user.org_id,
    )
    return result
