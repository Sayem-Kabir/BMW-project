"""Backend entry points for Module 3F Kuksa telemetry ingestion."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.database import async_session_maker

logger = logging.getLogger(__name__)

try:
    from sdv.kuksa import (
        KuksaSignalSubscriber,
        SqlAlchemyTelemetryStore,
        TelemetrySnapshot,
    )

    _KUKSA_AVAILABLE = True
except Exception as exc:  # noqa: BLE001
    _KUKSA_AVAILABLE = False
    logger.warning("Kuksa SDV package unavailable (%s) — using empty telemetry stubs", exc)

    @dataclass
    class TelemetrySnapshot:  # type: ignore[no-redef]
        speed_kmh: float | None = None
        latitude: float | None = None
        longitude: float | None = None
        battery_soc_pct: float | None = None
        rpm: float | None = None
        timestamp: datetime | None = None

        def as_context_dict(self) -> dict[str, Any]:
            return {
                "speed_kmh": self.speed_kmh,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "battery_soc_pct": self.battery_soc_pct,
                "rpm": self.rpm,
                "timestamp": self.timestamp or datetime.now(timezone.utc),
            }

    class KuksaSignalSubscriber:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError(
                "Kuksa SDV package not importable — start API with "
                "PYTHONPATH including the repo root (F:/BMW)"
            )

        async def current(self) -> TelemetrySnapshot:
            return TelemetrySnapshot()

        async def run(self, max_updates: int | None = None) -> int:
            return 0

    SqlAlchemyTelemetryStore = None  # type: ignore[misc, assignment]


def build_kuksa_subscriber(vehicle_id: UUID | str) -> Any:
    if not _KUKSA_AVAILABLE:
        raise RuntimeError(
            "Kuksa SDV package not importable — ensure repo root is on PYTHONPATH"
        )
    inner = SqlAlchemyTelemetryStore(async_session_maker)
    store: Any = inner
    if settings.telemetry_batch_enabled:
        try:
            from sdv.kuksa.buffered_store import BufferedTelemetryStore

            store = BufferedTelemetryStore(
                inner,
                flush_interval_sec=settings.telemetry_batch_flush_sec,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Buffered telemetry unavailable (%s) — direct writes", exc)
    return KuksaSignalSubscriber(
        str(vehicle_id),
        host=settings.kuksa_host,
        port=settings.kuksa_port,
        store=store,
    )


async def get_kuksa_snapshot(vehicle_id: UUID | str) -> TelemetrySnapshot:
    if not _KUKSA_AVAILABLE:
        return TelemetrySnapshot()
    return await build_kuksa_subscriber(vehicle_id).current()


async def run_kuksa_subscription(
    vehicle_id: UUID | str,
    *,
    max_updates: int | None = None,
) -> int:
    if not _KUKSA_AVAILABLE:
        return 0
    return await build_kuksa_subscriber(vehicle_id).run(max_updates=max_updates)
