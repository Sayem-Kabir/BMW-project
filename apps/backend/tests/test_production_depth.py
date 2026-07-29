"""Production-depth wiring tests — Kafka buffer, media URL, feast on risk path."""

from __future__ import annotations

from app.core.minio import public_http_url, resolve_media_url, build_object_url
from app.services import kafka_bus
from app.services.risk_service import _write_feast, evaluate_risk
from ml.feature_store import read_features


def test_media_url_resolution():
    uri = build_object_url("safety-events", "veh/evt.mp4")
    http = resolve_media_url(uri)
    assert http is not None
    assert "safety-events" in http
    assert public_http_url("b", "k").endswith("/b/k")


def test_kafka_buffer_fallback():
    kafka_bus.drain_buffer()
    out = kafka_bus.publish("bmw.test", {"ok": True}, bootstrap="127.0.0.1:1")
    assert out["ok"] is True
    assert out["mode"] in {"buffer", "kafka"}
    buf = kafka_bus.drain_buffer()
    assert isinstance(buf, list)


def test_feast_write_from_risk_helper():
    _write_feast(
        "00000000-0000-4000-8000-000000000003",
        {"score": 55.0, "level": "MEDIUM"},
        {"speed_kmh": 40},
    )
    got = read_features("00000000-0000-4000-8000-000000000003")
    assert got is not None
    assert got["features"]["risk_score"] == 55.0


def test_evaluate_risk_includes_fail_safe_keys():
    payload = evaluate_risk(
        "v1",
        {"is_drowsy": False, "face_detected": True},
        {"objects": []},
        {"speed_kmh": 30},
    )
    assert "risk_score" in payload
    assert "level" in payload
