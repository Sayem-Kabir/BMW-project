"""Leftover spec coverage — auth reset, GDPR, Section 19 industry APIs."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import industry_service
from ml.models.signed_ota import sign_digest, verify_signed_weights
from ml.risk_engine.fail_safe import apply_fail_safe, classify_asil
from ml.feature_store import write_features, read_features
from pathlib import Path


def test_asil_map():
    assert classify_asil("CRITICAL") == "C"
    assert classify_asil("LOW") == "QM"


def test_fail_safe_elevates_without_telemetry():
    out = apply_fail_safe(
        "LOW",
        10.0,
        driver_state={"is_drowsy": False, "face_detected": True},
        road_state={"objects": []},
        telemetry=None,
    )
    assert out["level"] == "HIGH"
    assert out["safe_state"] == "DEGRADED_SAFE"


def test_signed_ota_roundtrip(tmp_path: Path):
    f = tmp_path / "weights.bin"
    f.write_bytes(b"fake-weights-bytes")
    from ml.models.signed_ota import sign_file

    meta = sign_file(f)
    assert meta["signature"] == sign_digest(meta["sha256"])
    verified = verify_signed_weights(f, require_signature=True)
    assert verified["verified"] is True


def test_edge_cloud_route():
    edge = industry_service.edge_cloud_route(20)
    cloud = industry_service.edge_cloud_route(90)
    assert edge["route"] == "edge"
    assert cloud["route"] == "cloud"


def test_fusion_and_fedavg():
    fusion = industry_service.sensor_fusion_demo()
    assert fusion["final_distance_m"] > 0
    fed = industry_service.federated_avg_round()
    assert len(fed["global_weights"]) == 3


def test_feature_store_stub():
    write_features("veh-1", {"speed_mean": 42.0, "risk": 11.0})
    got = read_features("veh-1")
    assert got is not None
    assert got["features"]["speed_mean"] == 42.0


def test_canary_lifecycle():
    industry_service.rollback_canary(rolled_back_by="test")
    started = industry_service.start_canary(
        model_name="driver_monitor",
        version="v2",
        fleet_percent=15,
        started_by="test",
    )
    assert started["active"] is True
    rolled = industry_service.rollback_canary(rolled_back_by="test")
    assert rolled["active"] is False


def test_stripe_checkout_stub():
    sess = industry_service.stripe_checkout_session(
        org_id="org", tier="fleet_pro", seats=3
    )
    assert sess["livemode"] is False
    assert sess["amount_total_usd"] == 297.0


@pytest.mark.asyncio
async def test_industry_and_auth_require_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        assert (await client.get("/api/v1/industry/fusion/demo")).status_code == 401
        assert (await client.post("/api/v1/auth/forgot-password", json={"email": "a@b.co"})).status_code in {
            200,
            422,
        }
        assert (
            await client.get(
                "/api/v1/users/00000000-0000-4000-8000-000000000001/export"
            )
        ).status_code == 401


@pytest.mark.asyncio
async def test_replay_empty_frames_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.post(
            "/api/v1/industry/replay",
            json={
                "vehicle_id": "00000000-0000-4000-8000-000000000003",
                "frames": [],
            },
        )
        assert r.status_code == 401
