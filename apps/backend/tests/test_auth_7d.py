"""Module 7D — JWT auth, write guards, and org scoping tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import (
    auth_writes_required,
    create_access_token,
    decode_token,
)
from app.main import app

DEMO_ORG = UUID("00000000-0000-4000-8000-000000000010")
DEMO_USER = UUID("00000000-0000-4000-8000-000000000011")


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_create_and_decode_access_token():
    token = create_access_token(DEMO_USER)
    payload = decode_token(token)
    assert payload["sub"] == str(DEMO_USER)
    assert payload["type"] == "access"


def test_auth_writes_required_respects_flag(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "require_auth_writes", False)
    monkeypatch.setattr(config.settings, "environment", "development")
    assert auth_writes_required() is False
    monkeypatch.setattr(config.settings, "require_auth_writes", True)
    assert auth_writes_required() is True
    monkeypatch.setattr(config.settings, "require_auth_writes", False)
    monkeypatch.setattr(config.settings, "environment", "production")
    assert auth_writes_required() is True


@pytest.mark.asyncio
async def test_ack_requires_auth_when_writes_enforced(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "require_auth_writes", True)
    monkeypatch.setattr(config.settings, "environment", "development")

    alert_id = uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(f"/api/v1/fleet/alerts/{alert_id}/acknowledge")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ack_succeeds_with_bearer_when_writes_enforced(monkeypatch):
    from app.core import config
    from app.core.database import get_async_session
    from app.core.security import get_current_user

    monkeypatch.setattr(config.settings, "require_auth_writes", True)

    alert_id = uuid4()
    event = MagicMock()
    event.id = alert_id
    event.acknowledged = False
    event.acknowledged_at = None

    session = AsyncMock()
    event_result = MagicMock()
    event_result.scalar_one_or_none.return_value = event
    vehicle = SimpleNamespace(id=uuid4(), org_id=DEMO_ORG)
    vehicle_result = MagicMock()
    vehicle_result.scalar_one_or_none.return_value = vehicle
    session.execute = AsyncMock(side_effect=[event_result, vehicle_result])
    session.commit = AsyncMock()
    session.add = MagicMock()

    user = SimpleNamespace(
        id=DEMO_USER,
        email="demo@bmwai.dev",
        org_id=DEMO_ORG,
        role="fleet_manager",
    )

    async def _override_db():
        yield session

    async def _override_user():
        return user

    app.dependency_overrides[get_async_session] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/api/v1/fleet/alerts/{alert_id}/acknowledge",
                headers={"Authorization": f"Bearer {create_access_token(DEMO_USER)}"},
            )
    finally:
        app.dependency_overrides.pop(get_async_session, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_fleet_overview_uses_user_org_when_query_omitted():
    from app.core.database import get_async_session
    from app.core.security import get_current_user

    user = SimpleNamespace(
        id=DEMO_USER,
        email="demo@bmwai.dev",
        org_id=DEMO_ORG,
        role="fleet_manager",
    )
    overview = {
        "vehicle_count": 3,
        "active_alerts": 1,
        "average_risk": 40.0,
        "online_vehicles": 2,
        "phase": "6A",
    }

    async def _override_user():
        return user

    async def _override_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_async_session] = _override_db
    try:
        with patch(
            "app.services.fleet_service.build_fleet_overview",
            new_callable=AsyncMock,
            return_value=overview,
        ) as build:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/fleet/overview")
            build.assert_awaited()
            kwargs = build.await_args.kwargs
            assert kwargs.get("org_id") == DEMO_ORG
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_async_session, None)

    assert response.status_code == 200
    assert response.json()["vehicle_count"] == 3
