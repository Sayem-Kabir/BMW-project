import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["phase"] == "0"


@pytest.mark.asyncio
async def test_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


@pytest.mark.asyncio
async def test_driver_analysis_scaffold():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/driver/analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "LOW"
    assert data["phase"] == "scaffold"


@pytest.mark.asyncio
async def test_fleet_overview_scaffold():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/fleet/overview")
    assert response.status_code == 200
    data = response.json()
    assert "vehicle_count" in data


@pytest.mark.asyncio
async def test_xai_explain_scaffold():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/xai/explain", json={})
    assert response.status_code == 200
    assert response.json()["phase"] == "scaffold"
