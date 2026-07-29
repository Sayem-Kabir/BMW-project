"""Phase 6 fleet / analytics / xai API smoke tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_fleet_overview_detail_uses_service():
    payload = {
        "vehicle_count": 3,
        "active_alerts": 2,
        "average_risk": 41.5,
        "online_vehicles": 3,
        "risk_distribution": {"LOW": 1, "MEDIUM": 1, "HIGH": 1, "CRITICAL": 0},
        "phase": "6A",
    }
    vehicles = [
        {
            "id": str(uuid4()),
            "name": "Demo BMW i4",
            "risk_score": 22,
            "risk_level": "LOW",
            "status": "operational",
            "active_alerts": 0,
            "latitude": 48.13,
            "longitude": 11.58,
            "is_active": True,
        }
    ]
    with (
        patch(
            "app.services.fleet_service.build_fleet_overview",
            new_callable=AsyncMock,
            return_value=payload,
        ),
        patch(
            "app.services.fleet_service.list_fleet_vehicles",
            new_callable=AsyncMock,
            return_value=vehicles,
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/fleet/overview/detail")

    assert response.status_code == 200
    data = response.json()
    assert data["vehicle_count"] == 3
    assert data["average_risk"] == 41.5
    assert data["vehicles"][0]["name"] == "Demo BMW i4"


@pytest.mark.asyncio
async def test_analytics_leaderboard_endpoint():
    board = [
        {
            "rank": 1,
            "driver_id": str(uuid4()),
            "name": "Demo Driver",
            "safety_score": 90,
            "risk_tier": "green",
            "sparkline": [88, 90, 91],
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
    assert data["count"] == 1
    assert data["leaderboard"][0]["risk_tier"] == "green"
    assert data["phase"] == "6D"


@pytest.mark.asyncio
async def test_xai_explain_frame_returns_heatmap(tmp_path, monkeypatch):
    import cv2

    from ml.xai import gradcam

    monkeypatch.setattr(gradcam, "DEFAULT_HEATMAP_DIR", tmp_path)
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", frame)
    assert ok

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/xai/explain/frame",
            data={"event_type": "drowsiness"},
            files={"file": ("frame.jpg", buf.tobytes(), "image/jpeg")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["heatmap_url"]
    assert "eye" in data["explanation"].lower() or "Grad-CAM" in data["explanation"]
    assert data["phase"] == "6F"
    assert data.get("activation_mass") is not None
