"""Phase 7A — cross-phase integration smoke tests (ASGI + service mocks).

These prove the critical API contracts still compose without requiring a live car.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parent / "fixtures" / "test_frame.jpg"
DEMO_VEHICLE = "00000000-0000-4000-8000-000000000003"
DEMO_ORG = "00000000-0000-4000-8000-000000000010"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def frame_bytes() -> bytes:
    if FIXTURE.is_file():
        return FIXTURE.read_bytes()
    # Fallback tiny JPEG header-ish payload if fixture missing
    return b"\xff\xd8\xff\xd9"


@pytest.mark.asyncio
async def test_integration_driver_analysis(frame_bytes):
    fake = {
        "vehicle_id": DEMO_VEHICLE,
        "session_id": "demo-session",
        "alertness_score": 72,
        "risk_level": "MEDIUM",
        "ear_value": 0.24,
        "mar_value": 0.3,
        "yawn_count": 1,
        "head_pose": {"pitch": 2.0, "yaw": 1.0, "roll": 0.0, "distracted": False},
        "phone_detected": False,
        "seatbelt_worn": True,
        "is_drowsy": True,
        "is_yawning": False,
        "face_detected": True,
        "consecutive_drowsy_frames": 12,
        "yolo_model_loaded": False,
        "smoking_detected": False,
    }
    with patch("app.services.driver_service.analyze_frame_bytes", return_value=fake):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/driver/analysis",
                files={"file": ("frame.jpg", frame_bytes, "image/jpeg")},
                data={"vehicle_id": DEMO_VEHICLE, "persist": "false"},
            )
    assert response.status_code == 200
    data = response.json()
    assert "alertness_score" in data
    assert data["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert "ear_value" in data


@pytest.mark.asyncio
async def test_integration_risk_compute():
    from datetime import datetime, timezone

    payload = {
        "score": 78.0,
        "level": "HIGH",
        "risk_score": 78.0,
        "risk_level": "HIGH",
        "base_score": 60.0,
        "base_level": "MEDIUM",
        "factors": [{"name": "drowsiness", "weight": 0.4}],
        "overrides": [],
        "reasons": ["drowsy_driver"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": "rule_engine",
        "published": True,
        "receivers": 1,
        "cached": True,
        "persisted": False,
        "record_id": None,
        "warning": None,
        "persist_warning": None,
        "phase": "4F",
    }
    with patch(
        "app.services.risk_service.evaluate_and_publish",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/api/v1/risk/{DEMO_VEHICLE}/compute",
                json={
                    "driver_state": {
                        "is_drowsy": True,
                        "ear_value": 0.18,
                        "consecutive_drowsy_frames": 65,
                    },
                    "road_state": {
                        "objects": [
                            {
                                "class": "car",
                                "distance_m": 9.0,
                                "relative_speed_kmh": 50,
                                "confirmed": True,
                            }
                        ]
                    },
                    "telemetry": {"speed_kmh": 58},
                    "persist": False,
                },
            )
    assert response.status_code == 200
    data = response.json()
    assert 0 <= float(data["risk_score"]) <= 100
    assert data["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert data["phase"] == "4F"


@pytest.mark.asyncio
async def test_integration_fleet_overview_and_ack():
    overview = {
        "vehicle_count": 3,
        "active_alerts": 2,
        "average_risk": 41.5,
        "online_vehicles": 2,
        "phase": "6A",
    }
    alerts = [
        {
            "id": str(uuid4()),
            "vehicle_id": DEMO_VEHICLE,
            "event_type": "NEAR_COLLISION",
            "severity": "CRITICAL",
            "timestamp": "2026-07-20T08:00:00+00:00",
            "video_clip_url": None,
            "xai_explanation": "TTC below threshold",
            "acknowledged": False,
        }
    ]
    alert_id = UUID(alerts[0]["id"])
    event = MagicMock()
    event.id = alert_id
    event.acknowledged = False
    event.acknowledged_at = None

    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = event
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    from app.core.database import get_async_session

    async def _override():
        yield session

    with (
        patch(
            "app.services.fleet_service.build_fleet_overview",
            new_callable=AsyncMock,
            return_value=overview,
        ),
        patch(
            "app.services.fleet_service.list_fleet_alerts",
            new_callable=AsyncMock,
            return_value=alerts,
        ),
    ):
        app.dependency_overrides[get_async_session] = _override
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                ov = await client.get(
                    "/api/v1/fleet/overview",
                    params={"org_id": DEMO_ORG},
                )
                al = await client.get("/api/v1/fleet/alerts")
                ack = await client.post(f"/api/v1/fleet/alerts/{alert_id}/acknowledge")
        finally:
            app.dependency_overrides.clear()

    assert ov.status_code == 200
    assert ov.json()["vehicle_count"] == 3
    assert al.status_code == 200
    assert al.json()["phase"] == "6E"
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_integration_xai_frame_and_heatmap(frame_bytes, tmp_path, monkeypatch):
    from ml.xai import gradcam
    from app.services import xai_service

    monkeypatch.setattr(gradcam, "DEFAULT_HEATMAP_DIR", tmp_path)
    monkeypatch.setattr(xai_service, "DEFAULT_HEATMAP_DIR", tmp_path)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        explain = await client.post(
            "/api/v1/xai/explain/frame",
            data={"event_type": "drowsiness"},
            files={"file": ("frame.jpg", frame_bytes, "image/jpeg")},
        )
        assert explain.status_code == 200
        payload = explain.json()
        assert payload["heatmap_url"]
        assert payload["phase"] == "6F"
        filename = payload["heatmap_url"].rstrip("/").split("/")[-1]
        heat = await client.get(f"/api/v1/xai/heatmap/{filename}")
    assert heat.status_code == 200
    assert heat.headers["content-type"].startswith("image/")


@pytest.mark.asyncio
async def test_integration_xai_maintenance_shap():
    from types import SimpleNamespace

    top = [
        {
            "feature": "Vibration (g)",
            "contribution": 1.2,
            "direction": "increases_risk",
        }
    ]
    row = SimpleNamespace(
        component="engine",
        health_score=0.2,
        shap_explanation={
            "severity": "critical",
            "explanation": {"top_features": top},
        },
    )

    class FakeResult:
        def scalar_one_or_none(self):
            return row

    class FakeSession:
        async def execute(self, _stmt):
            return FakeResult()

    from app.core.database import get_async_session

    async def _override():
        yield FakeSession()

    app.dependency_overrides[get_async_session] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/xai/explain",
                json={
                    "vehicle_id": DEMO_VEHICLE,
                    "component": "engine",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "6G"
    assert data["shap_values"] is not None
    assert "Vibration" in data["explanation"]


@pytest.mark.asyncio
async def test_integration_assistant_chat_json():
    fake = {
        "conversation_id": None,
        "vehicle_id": DEMO_VEHICLE,
        "message": "What does TPMS mean?",
        "reply": "TPMS monitors tire pressure.",
        "intent": "knowledge",
        "route": "rag",
        "citations": ["bmw_owner_manual.txt"],
        "obd_matches": [],
        "warnings": [],
        "llm_backend": "offline",
        "llm_model": "offline",
        "phase": "5G",
    }
    with patch(
        "app.services.assistant_service.chat",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "What does TPMS mean?",
                    "vehicle_id": DEMO_VEHICLE,
                    "stream": False,
                    "persist": False,
                },
            )
    assert response.status_code == 200
    data = response.json()
    assert data["reply"]
    assert "TPMS" in data["reply"] or len(data["reply"]) > 5
