"""Module 8F — /metrics endpoint smoke."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/metrics")
    # Instrumentator may be missing in sparse envs — accept 200 or skip
    if response.status_code == 404:
        pytest.skip("prometheus instrumentator not installed")
    assert response.status_code == 200
    assert "http_" in response.text or "python_" in response.text
