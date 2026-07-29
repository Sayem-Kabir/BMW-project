"""Spec Phase 8 — Authentication, onboarding, MFA (8A–8F)."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.core.rate_limit import enforce_login_rate
from app.core.security import (
    ROLE_DRIVER,
    ROLE_FLEET_MANAGER,
    ROLE_ORG_ADMIN,
    ROLE_SUPER_ADMIN,
    SPEC_ROLES,
    create_access_token,
    decode_token,
    get_current_user,
    get_password_hash,
    normalize_role,
    require_roles,
    require_user,
    verify_password,
)
from app.models.driver import Driver
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    InviteUserRequest,
    LinkDriverRequest,
    LoginRequest,
    LogoutRequest,
    MfaConfirmRequest,
    MfaEnableResponse,
    MfaLoginRequest,
    OnboardingOrgRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    RoleChangeRequest,
    Token,
    UserResponse,
    VerifyEmailRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
PHASE = "8"


def _auto_verify() -> bool:
    return settings.environment.lower() in {"development", "dev", "test", "local"}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_async_session),
):
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    org_id = None
    role = ROLE_FLEET_MANAGER
    if body.org_name:
        org = Organization(name=body.org_name)
        session.add(org)
        await session.flush()
        org_id = org.id
        role = ROLE_ORG_ADMIN

    verify_token = secrets.token_urlsafe(32)
    user = User(
        email=body.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
        org_id=org_id,
        role=role,
        is_email_verified=_auto_verify(),
        email_verify_token=None if _auto_verify() else verify_token,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await auth_service.write_audit(
        session, action="USER_REGISTERED", user=user, target_type="users", target_id=user.id
    )
    await session.commit()
    await session.refresh(user)
    if not _auto_verify() and verify_token:
        await auth_service.send_verification_email(email=user.email, token=verify_token)
    return user


@router.post("/verify-email", response_model=UserResponse)
async def verify_email(
    body: VerifyEmailRequest,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(User).where(User.email_verify_token == body.token)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    user.is_email_verified = True
    user.email_verify_token = None
    await auth_service.write_audit(
        session, action="EMAIL_VERIFIED", user=user, target_type="users", target_id=user.id
    )
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Always return 200 to avoid email enumeration. Spec §11."""
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    reset_token: str | None = None
    if user is not None and user.is_active:
        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = reset_token
        from datetime import timedelta

        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await auth_service.write_audit(
            session,
            action="PASSWORD_RESET_REQUESTED",
            user=user,
            target_type="users",
            target_id=user.id,
        )
        await session.commit()
        if reset_token:
            await auth_service.send_password_reset_email(email=user.email, token=reset_token)
        if _auto_verify():
            return {
                "status": "ok",
                "message": "If the account exists, a reset link was sent",
                "reset_token": reset_token,
                "phase": PHASE,
            }
    return {
        "status": "ok",
        "message": "If the account exists, a reset link was sent",
        "phase": PHASE,
    }


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(User).where(User.password_reset_token == body.token)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    expires = user.password_reset_expires
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires is None or expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user.hashed_password = get_password_hash(body.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await auth_service.revoke_all_user_refresh(session, user.id)
    await auth_service.write_audit(
        session,
        action="PASSWORD_RESET_COMPLETED",
        user=user,
        target_type="users",
        target_id=user.id,
    )
    await session.commit()
    return {"status": "password_updated", "phase": PHASE}


@router.post("/login", response_model=Token)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _rate: None = Depends(enforce_login_rate),
):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        try:
            from app.core.metrics_custom import LOGIN_ATTEMPTS

            LOGIN_ATTEMPTS.labels(result="failure").inc()
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if user.is_active is False:
        raise HTTPException(status_code=403, detail="Account disabled")
    if not user.is_email_verified and not _auto_verify():
        raise HTTPException(status_code=403, detail="Email not verified")

    if user.mfa_enabled:
        if not body.totp_code:
            from jose import jwt as jose_jwt

            from app.core.security import ALGORITHM

            payload = {
                "sub": str(user.id),
                "type": "mfa_challenge",
                "exp": datetime.now(timezone.utc)
                + __import__("datetime").timedelta(minutes=5),
            }
            mfa_token = jose_jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
            return Token(
                access_token="",
                refresh_token=None,
                mfa_required=True,
                mfa_token=mfa_token,
            )
        if not user.mfa_secret or not pyotp.TOTP(user.mfa_secret).verify(
            body.totp_code, valid_window=1
        ):
            raise HTTPException(status_code=401, detail="Invalid MFA code")

    user.last_login = datetime.now(timezone.utc)
    tokens = await auth_service.issue_token_pair(session, user)
    await auth_service.write_audit(
        session, action="USER_LOGIN", user=user, target_type="users", target_id=user.id
    )
    await session.commit()
    try:
        from app.core.metrics_custom import LOGIN_ATTEMPTS

        LOGIN_ATTEMPTS.labels(result="success").inc()
    except Exception:  # noqa: BLE001
        pass
    return Token(**tokens)


@router.post("/mfa/complete", response_model=Token)
async def mfa_complete(
    body: MfaLoginRequest,
    session: AsyncSession = Depends(get_async_session),
):
    payload = decode_token(body.mfa_token)
    if payload.get("type") != "mfa_challenge":
        # decode_token may accept access — check type
        raise HTTPException(status_code=401, detail="Invalid MFA challenge token")
    user_id = payload.get("sub")
    result = await session.execute(select(User).where(User.id == UUID(str(user_id))))
    user = result.scalar_one_or_none()
    if user is None or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=401, detail="MFA not configured")
    if not pyotp.TOTP(user.mfa_secret).verify(body.totp_code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    user.last_login = datetime.now(timezone.utc)
    tokens = await auth_service.issue_token_pair(session, user)
    await session.commit()
    return Token(**tokens)


@router.post("/login/form", response_model=Token, include_in_schema=False)
async def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session),
    _rate: None = Depends(enforce_login_rate),
):
    return await login(
        LoginRequest(email=form_data.username, password=form_data.password),
        request,
        session,
    )


@router.post("/refresh", response_model=Token)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        tokens = await auth_service.rotate_refresh_token(session, body.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    await session.commit()
    return Token(**tokens)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User | None = Depends(get_current_user),
):
    await auth_service.revoke_refresh_token(session, body.refresh_token)
    if user is not None:
        await auth_service.write_audit(
            session, action="USER_LOGOUT", user=user, target_type="users", target_id=user.id
        )
    await session.commit()
    return {"status": "ok", "phase": PHASE}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(require_user)):
    return user


@router.post("/onboarding/org", response_model=UserResponse)
async def onboarding_create_org(
    body: OnboardingOrgRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_user),
):
    if user.org_id is not None:
        raise HTTPException(status_code=400, detail="User already belongs to an organization")
    org = Organization(name=body.org_name)
    session.add(org)
    await session.flush()
    user.org_id = org.id
    if normalize_role(user.role) == ROLE_DRIVER:
        pass
    else:
        user.role = ROLE_ORG_ADMIN
    await auth_service.write_audit(
        session,
        action="ORG_CREATED",
        user=user,
        target_type="organizations",
        target_id=org.id,
    )
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/onboarding/link-driver", response_model=UserResponse)
async def onboarding_link_driver(
    body: LinkDriverRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_user),
):
    user.role = ROLE_DRIVER
    if body.driver_id:
        result = await session.execute(select(Driver).where(Driver.id == body.driver_id))
        driver = result.scalar_one_or_none()
        if driver is None:
            raise HTTPException(status_code=404, detail="Driver not found")
        if user.org_id and driver.org_id and driver.org_id != user.org_id:
            raise HTTPException(status_code=403, detail="Driver not in your org")
    else:
        name = body.create_driver_name or user.full_name or user.email.split("@")[0]
        driver = Driver(
            name=name,
            email=user.email,
            org_id=user.org_id,
            user_id=user.id,
        )
        session.add(driver)
        await session.flush()
    driver.user_id = user.id
    user.driver_id = driver.id
    if user.org_id is None and driver.org_id is not None:
        user.org_id = driver.org_id
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/mfa/enable", response_model=MfaEnableResponse)
async def mfa_enable(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_user),
):
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    user.mfa_enabled = False
    await session.commit()
    totp = pyotp.TOTP(secret)
    url = totp.provisioning_uri(name=user.email, issuer_name="BMW AI Platform")
    return MfaEnableResponse(secret=secret, otpauth_url=url)


@router.post("/mfa/confirm")
async def mfa_confirm(
    body: MfaConfirmRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_user),
):
    if not user.mfa_secret:
        raise HTTPException(status_code=400, detail="Call /mfa/enable first")
    if not pyotp.TOTP(user.mfa_secret).verify(body.totp_code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    user.mfa_enabled = True
    await auth_service.write_audit(
        session, action="MFA_ENABLED", user=user, target_type="users", target_id=user.id
    )
    await session.commit()
    return {"status": "mfa_enabled", "phase": "8F"}


@router.post("/mfa/disable")
async def mfa_disable(
    body: MfaConfirmRequest,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(require_user),
):
    if user.mfa_enabled and user.mfa_secret:
        if not pyotp.TOTP(user.mfa_secret).verify(body.totp_code, valid_window=1):
            raise HTTPException(status_code=400, detail="Invalid TOTP code")
    user.mfa_enabled = False
    user.mfa_secret = None
    await session.commit()
    return {"status": "mfa_disabled", "phase": "8F"}


class GoogleExchangeRequest(BaseModel):
    code: str = Field(min_length=4)


@router.get("/google/authorize")
async def google_authorize():
    """Return Google OAuth URL when client credentials are configured."""
    cid = (settings.google_oauth_client_id or "").strip()
    if not cid:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")
    from urllib.parse import urlencode

    params = urlencode(
        {
            "client_id": cid,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return {
        "authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}",
        "redirect_uri": settings.google_oauth_redirect_uri,
        "phase": "8F",
    }


@router.post("/google/exchange", response_model=Token)
async def google_exchange(
    body: GoogleExchangeRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Exchange Google auth code for platform JWT (Spec Phase 8F)."""
    cid = (settings.google_oauth_client_id or "").strip()
    secret = (settings.google_oauth_client_secret or "").strip()
    if not cid or not secret:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": body.code,
                "client_id": cid,
                "client_secret": secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code >= 400:
            raise HTTPException(status_code=401, detail="Google token exchange failed")
        tokens = token_resp.json()
        access = tokens.get("access_token")
        if not access:
            raise HTTPException(status_code=401, detail="Google token missing")

        userinfo = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access}"},
        )
        if userinfo.status_code >= 400:
            raise HTTPException(status_code=401, detail="Google userinfo failed")
        profile = userinfo.json()

    email = str(profile.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
    if profile.get("email_verified") is False:
        raise HTTPException(status_code=403, detail="Google email not verified")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            full_name=str(profile.get("name") or ""),
            role=ROLE_DRIVER,
            is_email_verified=True,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        await auth_service.write_audit(
            session,
            action="USER_REGISTERED_GOOGLE",
            user=user,
            target_type="users",
            target_id=user.id,
        )
    elif user.is_active is False:
        raise HTTPException(status_code=403, detail="Account disabled")

    user.last_login = datetime.now(timezone.utc)
    pair = await auth_service.issue_token_pair(session, user)
    await auth_service.write_audit(
        session, action="USER_LOGIN_GOOGLE", user=user, target_type="users", target_id=user.id
    )
    await session.commit()
    return Token(**pair)
