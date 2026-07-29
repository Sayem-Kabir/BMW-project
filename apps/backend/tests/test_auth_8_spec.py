"""Spec Phase 8A–8F — auth unit tests (no live DB required for pure helpers)."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.security import (
    ROLE_DRIVER,
    ROLE_FLEET_MANAGER,
    ROLE_ORG_ADMIN,
    ROLE_SUPER_ADMIN,
    SPEC_ROLES,
    create_access_token,
    decode_token,
    get_password_hash,
    hash_token,
    normalize_role,
    require_user_for_writes,
    verify_password,
)
from app.core.scope import resolve_org_id


def test_argon2_hash_and_verify():
    hashed = get_password_hash("demo-password-123")
    assert hashed.startswith("$argon2") or "argon2" in hashed.lower() or hashed.startswith("$")
    assert verify_password("demo-password-123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_includes_role_and_org():
    uid = uuid4()
    org = uuid4()
    token = create_access_token(uid, role=ROLE_FLEET_MANAGER, org_id=org)
    payload = decode_token(token)
    assert payload["sub"] == str(uid)
    assert payload["role"] == ROLE_FLEET_MANAGER
    assert payload["org_id"] == str(org)
    assert payload["type"] == "access"


def test_access_token_default_ttl_is_short():
    from datetime import datetime, timezone

    uid = uuid4()
    token = create_access_token(uid, expires_delta=timedelta(minutes=15))
    payload = decode_token(token)
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    delta = exp - datetime.now(timezone.utc)
    assert timedelta(minutes=10) < delta < timedelta(minutes=16)


def test_five_spec_roles_defined():
    assert ROLE_SUPER_ADMIN in SPEC_ROLES
    assert ROLE_ORG_ADMIN in SPEC_ROLES
    assert ROLE_DRIVER in SPEC_ROLES
    assert len(SPEC_ROLES) == 5


def test_normalize_legacy_roles():
    assert normalize_role("viewer") == ROLE_DRIVER
    assert normalize_role("admin") == ROLE_ORG_ADMIN
    assert normalize_role("operator") == ROLE_FLEET_MANAGER


def test_hash_token_stable():
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abd")


def test_resolve_org_blocks_cross_org():
    user = SimpleNamespace(role="fleet_manager", org_id=uuid4())
    other = uuid4()
    with pytest.raises(HTTPException) as exc:
        resolve_org_id(other, user)
    assert exc.value.status_code == 403


def test_resolve_org_uses_user_org():
    org = uuid4()
    user = SimpleNamespace(role="fleet_manager", org_id=org)
    assert resolve_org_id(None, user) == org


@pytest.mark.asyncio
async def test_driver_denied_writes(monkeypatch):
    monkeypatch.setattr("app.core.security.auth_writes_required", lambda: False)
    driver = SimpleNamespace(role="driver")
    with pytest.raises(HTTPException) as exc:
        await require_user_for_writes(driver)
    assert exc.value.status_code == 403
