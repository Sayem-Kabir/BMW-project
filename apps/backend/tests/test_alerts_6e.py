"""Module 6E fleet alerts acknowledge API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_fleet_alerts_list_phase():
    alerts = [
        {
            "id": str(uuid4()),
            "vehicle_id": str(uuid4()),
            "event_type": "NEAR_COLLISION",
            "severity": "CRITICAL",
            "timestamp": "2026-07-20T08:00:00+00:00",
            "video_clip_url": None,
            "xai_explanation": "Near collision detected.",
            "acknowledged": False,
        }
    ]
    with patch(
        "app.services.fleet_service.list_fleet_alerts",
        new_callable=AsyncMock,
        return_value=alerts,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/fleet/alerts")

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "6E"
    assert data["count"] == 1
    assert data["alerts"][0]["severity"] == "CRITICAL"


@pytest.mark.asyncio
async def test_fleet_alert_acknowledge():
    alert_id = uuid4()
    event = MagicMock()
    event.id = alert_id
    event.acknowledged = False
    event.acknowledged_at = None

    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = event
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    with patch("app.api.v1.fleet.get_async_session", return_value=session):
        # Depends() injection is tricky; call endpoint logic via ASGI with dependency override
        from app.core.database import get_async_session
        from app.main import app as fastapi_app

        async def _override():
            yield session

        fastapi_app.dependency_overrides[get_async_session] = _override
        try:
            async with AsyncClient(
                transport=ASGITransport(app=fastapi_app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/fleet/alerts/{alert_id}/acknowledge"
                )
        finally:
            fastapi_app.dependency_overrides.pop(get_async_session, None)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "acknowledged"
    assert data["phase"] == "6E"
    assert event.acknowledged is True
    session.commit.assert_awaited()
