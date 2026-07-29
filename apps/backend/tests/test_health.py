import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["phase"] == "7"


@pytest.mark.asyncio
async def test_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


@pytest.mark.asyncio
async def test_driver_analysis_scaffold():
    # Kept for backwards compatibility — full coverage in test_driver_api.py
    from unittest.mock import patch

    fake = {
        "vehicle_id": "test",
        "session_id": "test",
        "alertness_score": 100,
        "risk_level": "LOW",
        "ear_value": 0.30,
        "mar_value": 0.20,
        "yawn_count": 0,
        "head_pose": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "distracted": False},
        "phone_detected": False,
        "seatbelt_worn": True,
        "consecutive_drowsy_frames": 0,
    }
    with patch("app.services.driver_service.analyze_frame_bytes", return_value=fake):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/driver/analysis",
                files={"file": ("frame.jpg", b"fake", "image/jpeg")},
            )
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "LOW"
    assert data["phase"] == "1"


@pytest.mark.asyncio
async def test_fleet_overview_scaffold():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/fleet/overview")
    assert response.status_code == 200
    data = response.json()
    assert "vehicle_count" in data


@pytest.mark.asyncio
async def test_xai_explain_scaffold():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/xai/explain", json={})
    assert response.status_code == 200
    assert response.json()["phase"] == "6G"
