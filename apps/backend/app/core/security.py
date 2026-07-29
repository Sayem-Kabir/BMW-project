"""Spec Phase 8 — passwords, JWT, roles, and auth dependencies."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.models.user import User

# argon2 for new hashes; bcrypt kept so existing demo users still verify (8A)
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/form", auto_error=False)

ALGORITHM = "HS256"

# Spec Phase 8C — five-role model
ROLE_SUPER_ADMIN = "super_admin"
ROLE_ORG_ADMIN = "org_admin"
ROLE_FLEET_MANAGER = "fleet_manager"
ROLE_DRIVER = "driver"
ROLE_MAINTENANCE_TECH = "maintenance_tech"

# Legacy aliases from earlier demo polish (map toward fleet_manager / read-only driver)
ROLE_VIEWER = "viewer"
ROLE_OPERATOR = "operator"
ROLE_ADMIN = "admin"

SPEC_ROLES = frozenset(
    {
        ROLE_SUPER_ADMIN,
        ROLE_ORG_ADMIN,
        ROLE_FLEET_MANAGER,
        ROLE_DRIVER,
        ROLE_MAINTENANCE_TECH,
    }
)

WRITE_ROLES = frozenset(
    {
        ROLE_SUPER_ADMIN,
        ROLE_ORG_ADMIN,
        ROLE_FLEET_MANAGER,
        ROLE_OPERATOR,
        ROLE_ADMIN,
        ROLE_MAINTENANCE_TECH,
    }
)

ADMIN_ROLES = frozenset({ROLE_SUPER_ADMIN, ROLE_ORG_ADMIN, ROLE_ADMIN})
FLEET_READ_ROLES = frozenset(
    {
        ROLE_SUPER_ADMIN,
        ROLE_ORG_ADMIN,
        ROLE_FLEET_MANAGER,
        ROLE_MAINTENANCE_TECH,
        ROLE_OPERATOR,
        ROLE_ADMIN,
    }
)
KNOWN_ROLES = SPEC_ROLES | {ROLE_VIEWER, ROLE_OPERATOR, ROLE_ADMIN}


def auth_writes_required() -> bool:
    if settings.require_auth_writes:
        return True
    return settings.environment.lower() in {"production", "prod", "staging"}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:  # noqa: BLE001
        return False


def get_password_hash(password: str) -> str:
    """Hash with argon2 (preferred)."""
    return pwd_context.hash(password)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str | UUID,
    *,
    role: str | None = None,
    org_id: str | UUID | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
    }
    if role:
        payload["role"] = role
    if org_id is not None:
        payload["org_id"] = str(org_id)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token_jwt(subject: str | UUID, *, jti: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "jti": jti,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(subject: str | UUID) -> str:
    """Backward-compatible helper — prefer issue_token_pair for DB-backed refresh."""
    return create_refresh_token_jwt(subject, jti=secrets.token_urlsafe(16))


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def normalize_role(role: str | None) -> str:
    r = (role or ROLE_FLEET_MANAGER).strip().lower()
    if r == ROLE_ADMIN:
        return ROLE_ORG_ADMIN
    if r == ROLE_OPERATOR:
        return ROLE_FLEET_MANAGER
    if r == ROLE_VIEWER:
        return ROLE_DRIVER
    return r


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User | None:
    if not token:
        return None
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.is_active is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return user


async def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*roles: str) -> Callable:
    """Require authenticated user whose role is in the allow-list (super_admin always ok)."""
    allowed = {normalize_role(r) for r in roles} | {ROLE_SUPER_ADMIN}

    async def _dependency(user: User = Depends(require_user)) -> User:
        role = normalize_role(user.role)
        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{user.role}' cannot perform this action "
                    f"(need one of: {sorted(allowed)})"
                ),
            )
        return user

    return _dependency


async def require_user_for_writes(
    user: User | None = Depends(get_current_user),
) -> User | None:
    if user is not None:
        role = normalize_role(user.role)
        if role == ROLE_DRIVER or (user.role or "").strip().lower() == ROLE_VIEWER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Driver/viewer role is read-only for this action",
            )
    if auth_writes_required():
        user = await require_user(user)
        role = normalize_role(user.role)
        if role not in WRITE_ROLES and role != ROLE_SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operator / fleet role or higher required for writes",
            )
        return user
    return user


async def require_operator_for_writes(
    user: User | None = Depends(get_current_user),
) -> User | None:
    return await require_user_for_writes(user)
