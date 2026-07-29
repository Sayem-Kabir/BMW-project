"""Spec Phase 10 — rate limit, uploads, error envelope, models promote."""

from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import _buckets, check_rate_limit
from app.core.uploads import read_upload_bytes, sniff_image_mime
from app.main import app
from fastapi import UploadFile


def test_sniff_jpeg_png():
    assert sniff_image_mime(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert sniff_image_mime(b"\x89PNG\r\n\x1a\nrest") == "image/png"


@pytest.mark.asyncio
async def test_read_upload_rejects_non_image():
    upload = UploadFile(
        filename="x.txt",
        file=io.BytesIO(b"not-an-image"),
        headers={"content-type": "text/plain"},
    )
    with pytest.raises(Exception) as exc:
        await read_upload_bytes(upload)
    assert getattr(exc.value, "status_code", None) == 400


@pytest.mark.asyncio
async def test_login_rate_limit_memory():
    _buckets.clear()
    key = "test-login-ip"
    for _ in range(5):
        check_rate_limit(key, limit=5, window_sec=60)
    with pytest.raises(Exception) as exc:
        check_rate_limit(key, limit=5, window_sec=60)
    assert getattr(exc.value, "status_code", None) == 429
    _buckets.clear()


@pytest.mark.asyncio
async def test_error_envelope_on_401():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/admin/health")
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_models_promote_requires_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/models/driver_monitor/promote",
            json={"target_stage": "production", "eval_metric_value": 0.95},
        )
    assert response.status_code == 401
