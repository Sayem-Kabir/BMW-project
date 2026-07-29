"""Feature-gated API endpoints require auth (and role when present)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/v1/demo/status"),
        ("POST", "/api/v1/demo/start"),
        ("GET", "/api/v1/fleet/vehicles"),
        ("GET", "/api/v1/fleet/overview"),
        ("GET", "/api/v1/maintenance/status"),
        ("GET", "/api/v1/analytics/fleet/leaderboard"),
    ],
)
async def test_feature_routes_require_auth(method: str, path: str):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        if method == "GET":
            response = await client.get(path)
        else:
            response = await client.post(path, json={})
    assert response.status_code == 401
