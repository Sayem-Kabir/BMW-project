"""Tests for Module 02 cabin intelligence API."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "test_frame.jpg"


@pytest.mark.asyncio
async def test_cabin_analysis_requires_auth():
    if not FIXTURE.is_file():
        pytest.skip("test_frame.jpg missing")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("frame.jpg", FIXTURE.read_bytes(), "image/jpeg")}
        r = await client.post("/api/v1/cabin/analysis", files=files)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_cabin_analysis_with_driver_token():
    if not FIXTURE.is_file():
        pytest.skip("test_frame.jpg missing")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "driver@bmwai.dev", "password": "driver1234"},
        )
        if login.status_code != 200:
            pytest.skip("demo driver not seeded")
        token = login.json()["access_token"]
        files = {"file": ("frame.jpg", FIXTURE.read_bytes(), "image/jpeg")}
        r = await client.post(
            "/api/v1/cabin/analysis",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "total_occupants" in data
    assert "occupant_map" in data
    assert data.get("phase") == "02"
