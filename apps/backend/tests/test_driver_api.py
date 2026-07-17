"""Module 1F — driver monitoring API tests (pipeline mocked)."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _fake_pipeline_result(**overrides):
    base = {
        "vehicle_id": "v1",
        "session_id": "s1",
        "alertness_score": 85,
        "risk_level": "LOW",
        "ear_value": 0.28,
        "mar_value": 0.22,
        "is_drowsy": False,
        "is_yawning": False,
        "consecutive_drowsy_frames": 0,
        "yawn_count": 0,
        "head_pose": {
            "pitch": 1.0,
            "yaw": -2.0,
            "roll": 0.5,
            "distracted": False,
            "face_detected": True,
        },
        "phone_detected": False,
        "smoking_detected": False,
        "seatbelt_worn": True,
        "face_detected": True,
        "yolo_model_loaded": True,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_driver_analysis_requires_file():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/driver/analysis")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_driver_analysis_returns_pipeline_payload():
    fake = _fake_pipeline_result(alertness_score=72, risk_level="MEDIUM", phone_detected=True)
    with patch(
        "app.services.driver_service.analyze_frame_bytes",
        return_value=fake,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/driver/analysis",
                files={"file": ("frame.jpg", b"fake-jpeg-bytes", "image/jpeg")},
            )
    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "1"
    assert data["message"] == "ok"
    assert data["alertness_score"] == 72
    assert data["risk_level"] == "MEDIUM"
    assert data["phone_detected"] is True
    assert data["head_pose"]["yaw"] == -2.0


@pytest.mark.asyncio
async def test_driver_analysis_bad_image_returns_400():
    with patch(
        "app.services.driver_service.analyze_frame_bytes",
        side_effect=ValueError("Could not decode image bytes (expected JPEG/PNG)"),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/driver/analysis",
                files={"file": ("bad.jpg", b"not-an-image", "image/jpeg")},
            )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_sessions_empty():
    vehicle_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/driver/sessions/{vehicle_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == []
    assert data["count"] == 0
    assert "phase" not in data  # no longer a scaffold stub


@pytest.mark.asyncio
async def test_session_detail_not_found():
    session_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/driver/sessions/{session_id}/detail")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analysis_to_api_payload_defaults():
    from app.services.driver_service import analysis_to_api_payload

    payload = analysis_to_api_payload(
        {
            "alertness_score": 90,
            "risk_level": "LOW",
            "ear_value": None,
            "mar_value": None,
            "head_pose": {},
        }
    )
    assert payload["ear_value"] == 0.0
    assert payload["mar_value"] == 0.0
    assert payload["phase"] == "1"
