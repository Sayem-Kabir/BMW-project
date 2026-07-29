"""Spec Phase 12 — notifications, PDF report."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import notification_service, report_service


def test_weekly_pdf_bytes_valid():
    pdf = report_service.build_weekly_pdf(
        {
            "driver_id": "00000000-0000-4000-8000-000000000001",
            "safety_score": 87.5,
            "events": {"fatigue": 2, "distraction": 1},
            "sparkline": [80, 82, 85, 87],
        }
    )
    assert pdf.startswith(b"%PDF")
    assert b"%%EOF" in pdf
    assert b"Weekly Driver Report" in pdf


@pytest.mark.asyncio
async def test_notify_critical_console_mode():
    notification_service.clear_sent_log()
    # No DB session needed for send_email console path
    result = await notification_service.send_email(
        to="fleet@bmwai.dev",
        subject="CRITICAL: near_collision",
        html="<p>test</p>",
    )
    assert result["ok"] is True
    assert result["mode"] == "console"
    assert notification_service.sent_log()


@pytest.mark.asyncio
async def test_notify_sms_console_mode():
    notification_service.clear_sent_log()
    result = await notification_service.send_sms(
        to="+15555550100",
        body="BMW AI CRITICAL near_collision",
    )
    assert result["ok"] is True
    assert result["mode"] == "console"


@pytest.mark.asyncio
async def test_notification_prefs_require_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.get("/api/v1/notifications/preferences")
        assert r.status_code == 401
        r2 = await client.post("/api/v1/notifications/test/critical")
        assert r2.status_code == 401


@pytest.mark.asyncio
async def test_weekly_pdf_route_requires_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        r = await client.get(
            "/api/v1/analytics/driver/00000000-0000-4000-8000-000000000001/weekly.pdf"
        )
        assert r.status_code == 401
