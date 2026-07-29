"""Module 7E — production readiness (CORS, probes, settings)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import _cors_origins, _warn_insecure_production_settings, app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_cors_origins_include_localhost_and_extras(monkeypatch):
    from app.core import config

    monkeypatch.setattr(
        config.settings,
        "cors_origins",
        "https://bmw-demo.vercel.app, https://bmw-demo.vercel.app",
    )
    origins = _cors_origins()
    assert "http://localhost:3000" in origins
    assert "https://bmw-demo.vercel.app" in origins
    assert origins.count("https://bmw-demo.vercel.app") == 1


def test_warn_insecure_production_settings(monkeypatch, caplog):
    from app.core import config

    monkeypatch.setattr(config.settings, "environment", "production")
    monkeypatch.setattr(
        config.settings,
        "secret_key",
        "change-this-to-a-real-random-string-in-production",
    )
    monkeypatch.setattr(config.settings, "cors_origins", "")
    with caplog.at_level("WARNING"):
        _warn_insecure_production_settings()
    text = " ".join(r.message for r in caplog.records)
    assert "SECRET_KEY" in text
    assert "CORS_ORIGINS" in text


@pytest.mark.asyncio
async def test_ready_returns_200_when_db_ok():
    fake_conn = MagicMock()
    fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
    fake_conn.__aexit__ = AsyncMock(return_value=None)
    fake_conn.execute = AsyncMock()

    with patch("app.main.engine") as engine:
        engine.connect.return_value = fake_conn
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["phase"] == "7E"


@pytest.mark.asyncio
async def test_ready_returns_503_when_db_down():
    with patch("app.main.engine") as engine:
        engine.connect.side_effect = RuntimeError("db down")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
