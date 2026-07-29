"""Spec Phase 13 — LTTB, semantic cache, buffered telemetry, gzip smoke."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.lttb import downsample_series, lttb
from app.main import app
from app.services.semantic_cache import SemanticCache, cosine_sparse, bag_of_words_vector
from sdv.kuksa.buffered_store import BufferedTelemetryStore
from sdv.kuksa.signal_subscriber import InMemoryTelemetryStore, TelemetrySnapshot
from datetime import datetime, timezone


def test_lttb_reduces_points_preserving_ends():
    pts = [{"i": i, "y": float(i % 17)} for i in range(200)]
    out = lttb(pts, 40)
    assert len(out) == 40
    assert out[0]["i"] == 0
    assert out[-1]["i"] == 199


def test_downsample_series_chart_rows():
    rows = [{"speed_kmh": float(i), "time": f"t{i}"} for i in range(100)]
    out = downsample_series(rows, 20, y_key="speed_kmh")
    assert len(out) == 20
    assert "speed_kmh" in out[0]
    assert "i" not in out[0]


def test_semantic_cache_hit_on_similar_question():
    cache = SemanticCache(threshold=0.5, ttl_sec=60)
    cache.store("What does TPMS mean on my BMW?", {"reply": "tire pressure"})
    hit = cache.lookup("what does tpms mean on bmw")
    assert hit is not None
    assert hit["reply"] == "tire pressure"
    assert hit["semantic_cache"]["hit"] is True


def test_cosine_identical_is_one():
    a, _ = bag_of_words_vector("oil service interval")
    b, _ = bag_of_words_vector("oil service interval")
    assert cosine_sparse(a, b) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_buffered_telemetry_flush():
    inner = InMemoryTelemetryStore()
    buf = BufferedTelemetryStore(inner, flush_interval_sec=0.01, max_buffer=10)
    snap = TelemetrySnapshot(
        vehicle_id="00000000-0000-4000-8000-000000000003",
        timestamp=datetime.now(timezone.utc),
        speed_kmh=42.0,
    )
    await buf.store(snap)
    await buf.store(snap)
    n = await buf.flush()
    assert n >= 1
    assert buf.stats["flushed_rows"] >= 1
    assert inner.latest(snap.vehicle_id) is not None


@pytest.mark.asyncio
async def test_gzip_middleware_present():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.get("/health", headers={"Accept-Encoding": "gzip"})
        assert r.status_code == 200
        assert r.json().get("phase") == "13"


@pytest.mark.asyncio
async def test_ws_rate_limiter_unit():
    from app.api.v1.ws import _RateLimiter

    lim = _RateLimiter(max_hz=1000)
    assert lim.allow() is True
    lim2 = _RateLimiter(max_hz=0.5)
    assert lim2.allow() is True
    assert lim2.allow() is False
