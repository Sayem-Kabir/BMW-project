"""CRITICAL event alerting — Spec Phase 12A (Resend email + Twilio SMS + webhooks)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import NotificationPreference, NotificationWebhook
from app.models.user import User

logger = logging.getLogger(__name__)

# In-memory log for tests / demo when providers are unset
_SENT_LOG: list[dict[str, Any]] = []


def sent_log() -> list[dict[str, Any]]:
    return list(_SENT_LOG)


def clear_sent_log() -> None:
    _SENT_LOG.clear()


async def send_email(*, to: str, subject: str, html: str) -> dict[str, Any]:
    entry = {"channel": "email", "to": to, "subject": subject, "ok": False}
    if not settings.resend_api_key:
        entry["ok"] = True
        entry["mode"] = "console"
        logger.info("[notify:email:console] to=%s subject=%s", to, subject)
        _SENT_LOG.append(entry)
        return entry
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.resend_from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
        entry["ok"] = resp.status_code < 300
        entry["status_code"] = resp.status_code
        entry["mode"] = "resend"
    except Exception as exc:  # noqa: BLE001
        entry["error"] = str(exc)
        logger.warning("Resend email failed: %s", exc)
    _SENT_LOG.append(entry)
    return entry


async def send_sms(*, to: str, body: str) -> dict[str, Any]:
    entry = {"channel": "sms", "to": to, "ok": False}
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number):
        entry["ok"] = True
        entry["mode"] = "console"
        logger.info("[notify:sms:console] to=%s body=%s", to, body[:80])
        _SENT_LOG.append(entry)
        return entry
    try:
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{settings.twilio_account_sid}/Messages.json"
        )
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                data={"From": settings.twilio_from_number, "To": to, "Body": body},
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
        entry["ok"] = resp.status_code < 300
        entry["status_code"] = resp.status_code
        entry["mode"] = "twilio"
    except Exception as exc:  # noqa: BLE001
        entry["error"] = str(exc)
        logger.warning("Twilio SMS failed: %s", exc)
    _SENT_LOG.append(entry)
    return entry


async def dispatch_webhooks(
    session: AsyncSession,
    *,
    org_id: UUID | None,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    q = select(NotificationWebhook).where(NotificationWebhook.active.is_(True))
    if org_id is not None:
        q = q.where(
            (NotificationWebhook.org_id == org_id) | (NotificationWebhook.org_id.is_(None))
        )
    hooks = list((await session.execute(q)).scalars().all())
    results: list[dict[str, Any]] = []
    for hook in hooks:
        row = {"url": hook.url, "ok": False}
        try:
            headers = {"Content-Type": "application/json"}
            if hook.secret:
                headers["X-BMW-Webhook-Secret"] = hook.secret
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(hook.url, json=payload, headers=headers)
            row["ok"] = resp.status_code < 300
            row["status_code"] = resp.status_code
        except Exception as exc:  # noqa: BLE001
            row["error"] = str(exc)
            logger.warning("Webhook %s failed: %s", hook.url, exc)
        results.append(row)
        _SENT_LOG.append({"channel": "webhook", **row})
    return results


async def notify_critical_safety_event(
    session: AsyncSession,
    *,
    event: dict[str, Any],
    org_id: UUID | None = None,
) -> dict[str, Any]:
    """Fan-out email/SMS/webhooks for CRITICAL events (Phase 12A exit criterion)."""
    severity = str(event.get("severity") or "").upper()
    if severity != "CRITICAL":
        return {"skipped": True, "reason": "not_critical"}

    subject = f"[BMW AI] CRITICAL {event.get('event_type')} — vehicle {event.get('vehicle_id')}"
    html = (
        f"<h2>Critical safety event</h2>"
        f"<p><b>Type:</b> {event.get('event_type')}<br/>"
        f"<b>Vehicle:</b> {event.get('vehicle_id')}<br/>"
        f"<b>Time:</b> {event.get('timestamp')}<br/>"
        f"<b>Explanation:</b> {event.get('xai_explanation') or 'n/a'}</p>"
    )
    sms_body = (
        f"BMW CRITICAL: {event.get('event_type')} vehicle={event.get('vehicle_id')}"
    )

    emails_sent: list[dict[str, Any]] = []
    sms_sent: list[dict[str, Any]] = []

    # Org users with prefs
    users_q = select(User)
    if org_id is not None:
        users_q = users_q.where(User.org_id == org_id)
    users = list((await session.execute(users_q)).scalars().all())
    for user in users:
        pref_r = await session.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user.id)
        )
        pref = pref_r.scalar_one_or_none()
        email_on = True if pref is None else bool(pref.email_enabled)
        sms_on = False if pref is None else bool(pref.sms_enabled)
        critical_only = True if pref is None else bool(pref.critical_only)
        if critical_only and severity != "CRITICAL":
            continue
        if email_on and user.email:
            emails_sent.append(await send_email(to=user.email, subject=subject, html=html))
        if sms_on and pref and pref.phone_e164:
            sms_sent.append(await send_sms(to=pref.phone_e164, body=sms_body))

    if not emails_sent and settings.notify_critical_email_fallback:
        emails_sent.append(
            await send_email(
                to=settings.notify_critical_email_fallback,
                subject=subject,
                html=html,
            )
        )
    if not emails_sent:
        # Always leave a console trail so demos/tests see activity
        emails_sent.append(
            await send_email(to="demo-fallback@bmwai.dev", subject=subject, html=html)
        )

    hooks = await dispatch_webhooks(
        session,
        org_id=org_id,
        payload={"type": "safety_event", "severity": severity, "event": event},
    )
    return {
        "skipped": False,
        "emails": emails_sent,
        "sms": sms_sent,
        "webhooks": hooks,
        "phase": "12A",
    }
