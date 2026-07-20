"""Module 4C risk Redis publish / cache / WebSocket fan-out tests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import risk_service


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _decision_payload(vehicle_id: str) -> dict:
    return {
        "vehicle_id": vehicle_id,
        "score": 75.0,
        "level": "HIGH",
        "risk_score": 75.0,
        "risk_level": "HIGH",
        "base_score": 15.0,
        "base_level": "LOW",
        "factors": [
            {
                "key": "no_seatbelt",
                "label": "Seatbelt not worn",
                "weight": 0.15,
                "contribution": 15.0,
                "reason": "Seatbelt not worn",
                "evidence": {"seatbelt_worn": False},
            }
        ],
        "overrides": [
            {
                "rule_id": "unbelted_highway_speed",
                "reason": "OVERRIDE: Unbelted at highway speed",
                "previous_score": 15.0,
                "resulting_score": 75.0,
                "previous_level": "LOW",
                "resulting_level": "HIGH",
                "evidence": {"telemetry.speed_kmh": 72.0},
            }
        ],
        "reasons": [
            "Seatbelt not worn",
            "OVERRIDE: Unbelted at highway speed",
        ],
        "timestamp": datetime(2026, 7, 20, 6, 0, tzinfo=timezone.utc).isoformat(),
        "method": "weighted_rules_with_overrides_v1",
        "phase": "4F",
    }


@pytest.mark.asyncio
async def test_compute_publishes_and_caches_risk_payload():
    vehicle_id = uuid4()
    payload = _decision_payload(str(vehicle_id))

    with (
        patch(
            "app.services.risk_service.evaluate_and_publish",
            new_callable=AsyncMock,
            return_value={
                **payload,
                "published": True,
                "receivers": 2,
                "cached": True,
                "persisted": False,
            },
        ) as evaluate_publish,
        patch(
            "app.core.redis.cache_json_set",
            new_callable=AsyncMock,
        ) as cache_set,
        patch(
            "app.core.redis.publish_json",
            new_callable=AsyncMock,
            return_value=2,
        ) as publish_json,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/risk/{vehicle_id}/compute",
                json={
                    "driver_state": {"seatbelt_worn": False},
                    "road_state": {},
                    "telemetry": {"speed_kmh": 72},
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "4F"
    assert data["score"] == 75.0
    assert data["level"] == "HIGH"
    assert data["published"] is True
    assert data["receivers"] == 2
    assert data["cached"] is True
    assert data["overrides"][0]["rule_id"] == "unbelted_highway_speed"
    cache_set.assert_not_awaited()
    publish_json.assert_not_awaited()
    evaluate_publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_compute_survives_redis_publish_failure():
    vehicle_id = uuid4()
    payload = _decision_payload(str(vehicle_id))

    with patch(
        "app.services.risk_service.evaluate_and_publish",
        new_callable=AsyncMock,
        return_value={
            **payload,
            "published": False,
            "receivers": 0,
            "cached": True,
            "persisted": False,
            "warning": "Redis publish unavailable",
        },
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/risk/{vehicle_id}/compute",
                json={"driver_state": {"is_drowsy": True}},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 75.0
    assert data["published"] is False
    assert data["warning"] == "Redis publish unavailable"


@pytest.mark.asyncio
async def test_current_risk_returns_cached_score():
    vehicle_id = uuid4()
    payload = _decision_payload(str(vehicle_id))

    with patch(
        "app.services.risk_service.get_cached_risk",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/risk/current/{vehicle_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 75
    assert data["level"] == "HIGH"
    assert data["phase"] == "4F"
    assert data["reasons"][0] == "Seatbelt not worn"


@pytest.mark.asyncio
async def test_current_risk_empty_when_cache_miss():
    vehicle_id = uuid4()
    with patch(
        "app.services.risk_service.get_cached_risk",
        new_callable=AsyncMock,
        return_value=None,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/risk/current/{vehicle_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 0
    assert data["level"] == "LOW"
    assert "No recent risk score" in data["message"]


def test_fleet_websocket_fans_out_risk_updates():
    org_id = uuid4()
    vehicle_id = str(uuid4())
    risk_payload = _decision_payload(vehicle_id)

    async def fake_iter():
        yield {
            "channel": f"risk:{vehicle_id}",
            "pattern": "risk:*",
            "data": risk_payload,
        }
        # Keep the pump alive long enough for the client assertions.
        await asyncio.Event().wait()

    with (
        patch(
            "app.services.risk_service.iter_risk_messages",
            side_effect=lambda: fake_iter(),
        ),
        TestClient(app) as client,
        client.websocket_connect(f"/api/v1/fleet/ws/{org_id}") as websocket,
    ):
        ready = websocket.receive_json()
        assert ready["type"] == "connected"
        assert ready["phase"] == "4F"
        assert ready["pattern"] == "risk:*"

        update = websocket.receive_json()
        assert update["type"] == "risk_update"
        assert update["data"]["vehicle_id"] == vehicle_id
        assert update["data"]["risk_level"] == "HIGH"
        assert update["channel"] == f"risk:{vehicle_id}"

        websocket.send_text("ping")
        pong = websocket.receive_json()
        assert pong["type"] == "pong"


def test_evaluate_risk_uses_real_4a_4b_pipeline():
    payload = risk_service.evaluate_risk(
        "vehicle-demo",
        {"seatbelt_worn": False},
        {},
        {"speed_kmh": 80},
    )
    assert payload["score"] == 75.0
    assert payload["level"] == "HIGH"
    assert payload["risk_score"] == 75.0
    assert payload["phase"] == "4F"
    assert payload["overrides"][0]["rule_id"] == "unbelted_highway_speed"


def test_channel_helpers():
    vehicle_id = "00000000-0000-4000-8000-000000000003"
    assert risk_service.risk_channel(vehicle_id) == f"risk:{vehicle_id}"
    assert risk_service.risk_cache_key(vehicle_id) == f"risk:latest:{vehicle_id}"
