"""Module 7C demo mode API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_demo_status_idle():
    with patch("app.services.demo_service.status_demo", return_value={
        "running": False,
        "status": "idle",
        "frames_sent": 0,
        "phase": "7C",
    }):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/demo/status")
    assert response.status_code == 200
    assert response.json()["running"] is False


@pytest.mark.asyncio
async def test_demo_start_stop():
    with (
        patch(
            "app.services.demo_service.start_demo",
            new_callable=AsyncMock,
            return_value={"ok": True, "running": True, "frames_sent": 0, "phase": "7C"},
        ),
        patch(
            "app.services.demo_service.stop_demo",
            new_callable=AsyncMock,
            return_value={"ok": True, "running": False, "status": "stopped", "phase": "7C"},
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            started = await client.post("/api/v1/demo/start", json={"fps": 3, "max_frames": 2})
            stopped = await client.post("/api/v1/demo/stop")
    assert started.status_code == 200
    assert started.json()["ok"] is True
    assert stopped.status_code == 200
    assert stopped.json()["ok"] is True
