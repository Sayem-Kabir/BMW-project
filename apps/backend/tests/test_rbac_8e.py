"""Module 8E — RBAC role helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.security import ROLE_OPERATOR, ROLE_VIEWER, WRITE_ROLES, require_user_for_writes


def test_write_roles_include_operator():
    assert ROLE_OPERATOR in WRITE_ROLES
    assert ROLE_VIEWER not in WRITE_ROLES


@pytest.mark.asyncio
async def test_viewer_denied_writes(monkeypatch):
    monkeypatch.setattr("app.core.security.auth_writes_required", lambda: False)
    viewer = SimpleNamespace(role="viewer")
    with pytest.raises(HTTPException) as exc:
        await require_user_for_writes(viewer)
    assert exc.value.status_code == 403
