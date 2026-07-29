"""Buffered telemetry writes — Spec Phase 13 (1–5s flush)."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any

from sdv.kuksa.signal_subscriber import TelemetrySnapshot, TelemetryStore

logger = logging.getLogger(__name__)


class BufferedTelemetryStore:
    """Accumulate snapshots per vehicle and flush in batches."""

    def __init__(
        self,
        inner: TelemetryStore,
        *,
        flush_interval_sec: float = 2.0,
        max_buffer: int = 200,
    ) -> None:
        self.inner = inner
        self.flush_interval_sec = max(0.2, float(flush_interval_sec))
        self.max_buffer = max(1, int(max_buffer))
        self._buf: dict[str, list[TelemetrySnapshot]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._last_flush = time.monotonic()
        self._flushed_batches = 0
        self._flushed_rows = 0

    @property
    def stats(self) -> dict[str, Any]:
        pending = sum(len(v) for v in self._buf.values())
        return {
            "pending": pending,
            "flushed_batches": self._flushed_batches,
            "flushed_rows": self._flushed_rows,
            "flush_interval_sec": self.flush_interval_sec,
            "phase": "13",
        }

    async def store(self, snapshot: TelemetrySnapshot) -> None:
        async with self._lock:
            bucket = self._buf[snapshot.vehicle_id]
            bucket.append(snapshot)
            if len(bucket) > self.max_buffer:
                del bucket[: len(bucket) - self.max_buffer]
            due = (time.monotonic() - self._last_flush) >= self.flush_interval_sec
            overflow = sum(len(v) for v in self._buf.values()) >= self.max_buffer
            if due or overflow:
                await self._flush_unlocked()

    async def flush(self) -> int:
        async with self._lock:
            return await self._flush_unlocked()

    async def _flush_unlocked(self) -> int:
        items: list[TelemetrySnapshot] = []
        for vid in list(self._buf.keys()):
            items.extend(self._buf.pop(vid))
        if not items:
            self._last_flush = time.monotonic()
            return 0
        for snap in items:
            await self.inner.store(snap)
        self._flushed_batches += 1
        self._flushed_rows += len(items)
        self._last_flush = time.monotonic()
        logger.debug("Telemetry batch flush rows=%s", len(items))
        return len(items)
