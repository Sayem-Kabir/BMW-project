"""Module 6D analytics API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_fleet_leaderboard_endpoint():
    board = [
        {
            "rank": 1,
            "driver_id": str(uuid4()),
            "name": "Demo Driver",
            "email": "demo@bmwai.local",
            "safety_score": 89.0,
            "risk_tier": "green",
            "sparkline": [86, 87, 88, 89, 90, 91, 92],
            "event_count_7d": 0,
        }
    ]
    with patch(
        "app.services.analytics_service.fleet_leaderboard",
        new_callable=AsyncMock,
        return_value=board,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/analytics/fleet/leaderboard")

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "6D"
    assert data["count"] == 1
    assert data["leaderboard"][0]["risk_tier"] == "green"
    assert len(data["leaderboard"][0]["sparkline"]) == 7


@pytest.mark.asyncio
async def test_fleet_incidents_endpoint():
    incidents = [
        {
            "week_start": "2026-07-20",
            "total": 6,
            "CRITICAL": 5,
            "HIGH": 1,
            "MEDIUM": 0,
            "LOW": 0,
        }
    ]
    with patch(
        "app.services.analytics_service.fleet_incidents",
        new_callable=AsyncMock,
        return_value=incidents,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/analytics/fleet/incidents")

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "6D"
    assert data["incidents"][0]["total"] == 6
