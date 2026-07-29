"""Spec Phase 8B — refresh token persistence, rotation, audit helpers."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token_jwt,
    hash_token,
)
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def write_audit(
    session: AsyncSession,
    *,
    action: str,
    user: User | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            user_id=user.id if user else None,
            org_id=user.org_id if user else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_=metadata,
        )
    )


async def issue_token_pair(session: AsyncSession, user: User) -> dict[str, str]:
    jti = secrets.token_urlsafe(24)
    raw_refresh = create_refresh_token_jwt(user.id, jti=jti)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=expires,
            revoked=False,
        )
    )
    access = create_access_token(user.id, role=user.role, org_id=user.org_id)
    return {
        "access_token": access,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }


async def rotate_refresh_token(session: AsyncSession, raw_refresh: str) -> dict[str, str]:
    from app.core.security import decode_token

    payload = decode_token(raw_refresh)
    if payload.get("type") != "refresh":
        raise ValueError("invalid_refresh")
    subject = payload.get("sub")
    if not subject:
        raise ValueError("invalid_refresh")

    digest = hash_token(raw_refresh)
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == digest,
            RefreshToken.revoked.is_(False),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError("refresh_revoked_or_unknown")
    now = datetime.now(timezone.utc)
    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now:
        row.revoked = True
        raise ValueError("refresh_expired")

    row.revoked = True
    user_result = await session.execute(select(User).where(User.id == UUID(subject)))
    user = user_result.scalar_one_or_none()
    if user is None or user.is_active is False:
        raise ValueError("user_inactive")
    return await issue_token_pair(session, user)


async def revoke_refresh_token(session: AsyncSession, raw_refresh: str | None) -> None:
    if not raw_refresh:
        return
    digest = hash_token(raw_refresh)
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == digest)
        .values(revoked=True)
    )


async def revoke_all_user_refresh(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )


async def send_verification_email(*, email: str, token: str) -> dict[str, Any]:
    from app.services.notification_service import send_email

    link = f"{settings.frontend_url.rstrip('/')}/verify-email?token={token}"
    html = (
        f"<p>Verify your BMW AI Platform account:</p>"
        f'<p><a href="{link}">Confirm email</a></p>'
        f"<p>Or paste this token: <code>{token}</code></p>"
    )
    return await send_email(
        to=email,
        subject="Verify your BMW AI account",
        html=html,
    )


async def send_password_reset_email(*, email: str, token: str) -> dict[str, Any]:
    from app.services.notification_service import send_email

    link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    html = (
        f"<p>Reset your BMW AI Platform password:</p>"
        f'<p><a href="{link}">Reset password</a></p>'
        f"<p>Or paste this token: <code>{token}</code></p>"
    )
    return await send_email(
        to=email,
        subject="Reset your BMW AI password",
        html=html,
    )

