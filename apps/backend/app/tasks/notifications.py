"""Notification Celery tasks — Spec Phase 13 notifications queue."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.notifications.dispatch_critical")
def dispatch_critical(event: dict[str, Any], org_id: str | None = None) -> dict[str, Any]:
    """Async fan-out wrapper around notification_service (queue: notifications)."""

    async def _run() -> dict[str, Any]:
        from uuid import UUID

        from app.core.database import async_session_maker
        from app.services import notification_service

        org = UUID(org_id) if org_id else None
        async with async_session_maker() as session:
            return await notification_service.notify_critical_safety_event(
                session, event=event, org_id=org
            )

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        logger.warning("dispatch_critical failed: %s", exc)
        return {"ok": False, "error": str(exc), "phase": "13"}
