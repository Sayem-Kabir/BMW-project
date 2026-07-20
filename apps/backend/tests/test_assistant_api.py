"""Module 5D assistant chat API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _assistant_payload() -> dict:
    return {
        "conversation_id": str(uuid4()),
        "vehicle_id": "00000000-0000-4000-8000-000000000003",
        "message": "Why is my TPMS warning on?",
        "reply": "Your TPMS light means one or more tires may be under-inflated.",
        "intent": "vehicle_warning",
        "route": "rag_with_telemetry",
        "citations": ["bmw_owner_manual.txt"],
        "obd_matches": [],
        "telemetry_context": "Current vehicle sensor readings:\n- Tire Pressures: RL=22 PSI",
        "maintenance_context": "Latest predictive maintenance status for this vehicle:\n- tire: health=0.62",
        "conversation_memory": "Prior conversation (most recent last):\nDriver: Why is my TPMS warning on?",
        "memory_message_count": 2,
        "llm_backend": "injected",
        "llm_model": "test-model",
        "warnings": [],
        "phase": "5G",
    }


@pytest.mark.asyncio
async def test_assistant_chat_sse_stream():
    payload = _assistant_payload()
    with patch(
        "app.services.assistant_service.chat",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Why is my TPMS warning on?",
                    "vehicle_id": "00000000-0000-4000-8000-000000000003",
                    "stream": True,
                    "persist": False,
                },
            )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "TPMS" in body
    assert "[DONE]" in body
    assert '"type": "meta"' in body or '"type":"meta"' in body


@pytest.mark.asyncio
async def test_assistant_chat_json_mode():
    payload = _assistant_payload()
    with patch(
        "app.services.assistant_service.chat",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/assistant/chat",
                json={
                    "message": "Why is my TPMS warning on?",
                    "stream": False,
                    "persist": False,
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "vehicle_warning"
    assert "TPMS" in data["reply"]
    assert data["phase"] == "5G"
    assert data["citations"] == ["bmw_owner_manual.txt"]
    assert "tire" in (data.get("maintenance_context") or "")
    assert data["memory_message_count"] == 2


@pytest.mark.asyncio
async def test_assistant_conversations_list_handles_db_failure():
    vehicle_id = "00000000-0000-4000-8000-000000000003"
    with patch(
        "app.services.assistant_service.list_conversations",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db down"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/api/v1/assistant/conversations/{vehicle_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["warning"]
    assert data["phase"] == "5G"


@pytest.mark.asyncio
async def test_assistant_conversation_detail_not_found():
    with patch(
        "app.services.assistant_service.get_conversation",
        new_callable=AsyncMock,
        return_value=None,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/v1/assistant/conversations/detail/{uuid4()}"
            )

    assert response.status_code == 404
