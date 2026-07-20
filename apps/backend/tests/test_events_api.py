"""Module 4F events and risk REST API tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import risk_service


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _risk_payload(vehicle_id: str) -> dict:
    return {
        "vehicle_id": vehicle_id,
        "score": 75.0,
        "level": "HIGH",
        "risk_score": 75.0,
        "risk_level": "HIGH",
        "base_score": 15.0,
        "base_level": "LOW",
        "factors": [],
        "overrides": [],
        "reasons": ["Seatbelt not worn"],
        "timestamp": datetime(2026, 7, 20, 6, 0, tzinfo=timezone.utc).isoformat(),
        "method": "weighted_rules_with_overrides_v1",
        "phase": "4F",
        "published": True,
        "receivers": 1,
        "cached": True,
        "persisted": True,
        "record_id": str(uuid4()),
    }


def _detect_payload(vehicle_id: str, driver_id: str) -> dict:
    event_id = str(uuid4())
    return {
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "session_id": None,
        "phase": "4E",
        "detected": 1,
        "persisted": 1,
        "events": [
            {
                "id": event_id,
                "event_type": "NEAR_COLLISION",
                "severity": "CRITICAL",
                "timestamp": datetime(2026, 7, 20, 7, 0, tzinfo=timezone.utc).isoformat(),
                "video_clip_url": None,
                "xai_explanation": "Near collision detected because TTC dropped to 1.7s",
            }
        ],
        "warnings": [],
        "skipped_detectors": [],
        "completed_at": datetime(2026, 7, 20, 7, 0, 1, tzinfo=timezone.utc).isoformat(),
    }


@pytest.mark.asyncio
async def test_compute_returns_persisted_flag():
    vehicle_id = uuid4()
    payload = _risk_payload(str(vehicle_id))

    with patch(
        "app.services.risk_service.evaluate_and_publish",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/risk/{vehicle_id}/compute",
                json={"driver_state": {"seatbelt_worn": False}, "persist": True},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "4F"
    assert data["persisted"] is True
    assert data["record_id"] is not None


@pytest.mark.asyncio
async def test_risk_history_reads_database_rows():
    vehicle_id = uuid4()
    row = MagicMock()
    row.id = uuid4()
    row.vehicle_id = vehicle_id
    row.score = 75.0
    row.level = "HIGH"
    row.timestamp = datetime(2026, 7, 20, 6, 0, tzinfo=timezone.utc)
    row.payload = {"factors": [], "reasons": ["test"], "overrides": []}

    with patch(
        "app.services.risk_service.list_risk_history",
        new_callable=AsyncMock,
        return_value=[row],
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/risk/history/{vehicle_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "4F"
    assert data["count"] == 1
    assert data["history"][0]["score"] == 75.0


@pytest.mark.asyncio
async def test_detect_events_endpoint_returns_persisted_summary():
    vehicle_id = uuid4()
    driver_id = uuid4()
    payload = _detect_payload(str(vehicle_id), str(driver_id))

    with patch(
        "app.services.event_service.detect_and_persist",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/events/{vehicle_id}/detect",
                json={
                    "driver_id": str(driver_id),
                    "driver_state": {"consecutive_drowsy_frames": 70},
                    "road_state": {"objects": []},
                    "telemetry": {"speed_kmh": 50},
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "4F"
    assert data["detected"] == 1
    assert data["persisted"] == 1
    assert data["events"][0]["event_type"] == "NEAR_COLLISION"


@pytest.mark.asyncio
async def test_acknowledge_event_updates_row():
    event_id = uuid4()
    driver_id = uuid4()
    row = MagicMock()
    row.id = event_id
    row.vehicle_id = uuid4()
    row.driver_id = driver_id
    row.session_id = None
    row.event_type = "NEAR_COLLISION"
    row.severity = "CRITICAL"
    row.timestamp = datetime(2026, 7, 20, 7, 0, tzinfo=timezone.utc)
    row.latitude = None
    row.longitude = None
    row.telemetry_snapshot = {}
    row.video_clip_url = None
    row.xai_explanation = "test"
    row.acknowledged = True
    row.acknowledged_at = datetime(2026, 7, 20, 7, 5, tzinfo=timezone.utc)

    with patch(
        "app.services.event_service.acknowledge_event",
        new_callable=AsyncMock,
        return_value=row,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/events/detail/{event_id}/acknowledge",
                json={"driver_id": str(driver_id)},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged"] is True


def test_run_risk_evaluation_task_success():
    from app.tasks.risk import run_risk_evaluation

    vehicle_id = str(uuid4())
    with patch(
        "app.services.risk_service.evaluate_persist_and_publish",
        new_callable=AsyncMock,
        return_value=_risk_payload(vehicle_id),
    ):
        result = run_risk_evaluation(vehicle_id, {}, {}, {})

    assert result["status"] == "ok"
    assert result["phase"] == "4F"


def test_evaluate_risk_reports_phase_4f():
    payload = risk_service.evaluate_risk(
        "vehicle-demo",
        {"seatbelt_worn": False},
        {},
        {"speed_kmh": 80},
    )
    assert payload["phase"] == "4F"
