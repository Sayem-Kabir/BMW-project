"""GDPR-style personal data export / erasure — Spec §11 + Section 19.6."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import (
    ROLE_ORG_ADMIN,
    ROLE_SUPER_ADMIN,
    require_roles,
    require_user,
)
from app.models.assistant import AssistantConversation
from app.models.notification import NotificationPreference
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services import auth_service

router = APIRouter(prefix="/api/v1/users", tags=["Users / GDPR"])
PHASE = "19.6"


def _can_access(actor: User, target_id: UUID) -> bool:
    if actor.id == target_id:
        return True
    if actor.role in {ROLE_SUPER_ADMIN}:
        return True
    if actor.role == ROLE_ORG_ADMIN and actor.org_id is not None:
        return True
    return False


@router.get("/{user_id}/export")
async def export_user_data(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    actor: User = Depends(require_user),
):
    if not _can_access(actor, user_id):
        raise HTTPException(status_code=403, detail="Cannot export another user's data")
    user = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if (
        actor.role == ROLE_ORG_ADMIN
        and actor.id != user_id
        and user.org_id != actor.org_id
    ):
        raise HTTPException(status_code=403, detail="User not in your org")

    prefs = (
        await session.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
    ).scalar_one_or_none()
    convos = list(
        (
            await session.execute(
                select(AssistantConversation)
                .where(AssistantConversation.driver_id == user.driver_id)
                .limit(50)
            )
        ).scalars().all()
    ) if user.driver_id else []

    await auth_service.write_audit(
        session,
        action="GDPR_EXPORT",
        user=actor,
        target_type="users",
        target_id=user_id,
    )
    await session.commit()

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "org_id": str(user.org_id) if user.org_id else None,
            "driver_id": str(user.driver_id) if user.driver_id else None,
            "is_email_verified": user.is_email_verified,
            "mfa_enabled": user.mfa_enabled,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        },
        "notification_preferences": (
            {
                "email_enabled": prefs.email_enabled,
                "sms_enabled": prefs.sms_enabled,
                "push_enabled": prefs.push_enabled,
                "critical_only": prefs.critical_only,
            }
            if prefs
            else None
        ),
        "assistant_conversations": [
            {
                "id": str(c.id),
                "started_at": c.started_at.isoformat() if c.started_at else None,
                "message_count": len(c.messages or []),
            }
            for c in convos
        ],
        "phase": PHASE,
    }


@router.delete("/{user_id}/data")
async def erase_user_data(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    actor: User = Depends(require_user),
):
    """Right-to-erasure: anonymize PII, revoke sessions, clear prefs (keeps audit)."""
    if actor.id != user_id and actor.role not in {ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Cannot erase another user's data")
    user = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if (
        actor.role == ROLE_ORG_ADMIN
        and actor.id != user_id
        and user.org_id != actor.org_id
    ):
        raise HTTPException(status_code=403, detail="User not in your org")

    await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await session.execute(
        delete(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    anon = f"erased-{str(user_id)[:8]}@deleted.local"
    user.email = anon
    user.full_name = "Erased User"
    user.hashed_password = "!"  # unusable
    user.is_active = False
    user.mfa_enabled = False
    user.mfa_secret = None
    user.email_verify_token = None
    user.password_reset_token = None
    user.password_reset_expires = None
    user.driver_id = None

    await auth_service.write_audit(
        session,
        action="GDPR_ERASURE",
        user=actor,
        target_type="users",
        target_id=user_id,
    )
    await session.commit()
    return {"status": "erased", "user_id": str(user_id), "phase": PHASE}


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    actor: User = Depends(require_roles(ROLE_ORG_ADMIN, ROLE_SUPER_ADMIN)),
):
    user = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if actor.role == ROLE_ORG_ADMIN and user.org_id != actor.org_id:
        raise HTTPException(status_code=403, detail="User not in your org")
    user.is_active = False
    await auth_service.revoke_all_user_refresh(session, user_id)
    await auth_service.write_audit(
        session,
        action="USER_DEACTIVATED",
        user=actor,
        target_type="users",
        target_id=user_id,
    )
    await session.commit()
    return {"status": "deactivated", "user_id": str(user_id), "phase": PHASE}
