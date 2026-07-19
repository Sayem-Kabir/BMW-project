"""Backend entry points for Module 3F Kuksa telemetry ingestion."""

from __future__ import annotations

from uuid import UUID

from app.core.config import settings
from app.core.database import async_session_maker
from sdv.kuksa import (
    KuksaSignalSubscriber,
    SqlAlchemyTelemetryStore,
    TelemetrySnapshot,
)


def build_kuksa_subscriber(vehicle_id: UUID | str) -> KuksaSignalSubscriber:
    return KuksaSignalSubscriber(
        str(vehicle_id),
        host=settings.kuksa_host,
        port=settings.kuksa_port,
        store=SqlAlchemyTelemetryStore(async_session_maker),
    )


async def get_kuksa_snapshot(vehicle_id: UUID | str) -> TelemetrySnapshot:
    return await build_kuksa_subscriber(vehicle_id).current()


async def run_kuksa_subscription(
    vehicle_id: UUID | str,
    *,
    max_updates: int | None = None,
) -> int:
    return await build_kuksa_subscriber(vehicle_id).run(max_updates=max_updates)
