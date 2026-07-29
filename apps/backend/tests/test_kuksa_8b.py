"""Module 8B unit tests — bridge status without live databroker."""

from __future__ import annotations

import pytest

from app.services import kuksa_bridge_service


@pytest.mark.asyncio
async def test_bridge_status_idle():
    await kuksa_bridge_service.stop_bridge()
    status = kuksa_bridge_service.bridge_status()
    assert status["running"] is False
    assert status["phase"] == "8B"
