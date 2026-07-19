"""Module 3F — deterministic synthetic VSS telemetry for broker-free demos."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
from collections.abc import AsyncIterator
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sdv.kuksa.signal_subscriber import (
    InMemoryTelemetryStore,
    TelemetrySnapshot,
    TelemetryStore,
)

DEFAULT_VEHICLE_ID = "00000000-0000-0000-0000-000000000001"


class SensorSimulator:
    """Generate repeatable, physically plausible vehicle telemetry snapshots."""

    def __init__(
        self,
        vehicle_id: str = DEFAULT_VEHICLE_ID,
        *,
        seed: int = 42,
        interval_seconds: float = 1.0,
        degradation_rate: float = 1.0,
        start_time: datetime | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if degradation_rate < 0:
            raise ValueError("degradation_rate cannot be negative")
        self.vehicle_id = str(vehicle_id)
        self.interval_seconds = float(interval_seconds)
        self.degradation_rate = float(degradation_rate)
        self.start_time = start_time or datetime.now(timezone.utc)
        self._random = random.Random(seed)
        self._tick = 0

    def next_snapshot(self) -> TelemetrySnapshot:
        tick = self._tick
        elapsed = tick * self.interval_seconds
        cycle = math.sin(tick / 14.0)
        speed = max(0.0, 52.0 + 29.0 * cycle + self._random.gauss(0, 1.2))
        braking = max(0.0, -cycle * 50.0) if tick % 35 > 25 else 0.0
        steering = 18.0 * math.sin(tick / 9.0)
        degradation = self.degradation_rate * tick / 3600.0

        snapshot = TelemetrySnapshot(
            vehicle_id=self.vehicle_id,
            timestamp=self.start_time + timedelta(seconds=elapsed),
            speed_kmh=round(speed, 3),
            rpm=int(round(750.0 + speed * 34.0 + self._random.gauss(0, 35))),
            oil_temp_c=round(88.0 + 6.0 * math.sin(tick / 50.0), 3),
            coolant_temp_c=round(84.0 + 4.0 * math.sin(tick / 45.0), 3),
            battery_soc_pct=round(max(5.0, 88.0 - tick * 0.015), 3),
            battery_health_pct=round(max(60.0, 96.0 - degradation * 0.08), 3),
            tire_pressure_fl=round(33.2 - degradation * 0.025, 3),
            tire_pressure_fr=round(33.0 - degradation * 0.022, 3),
            tire_pressure_rl=round(34.1 - degradation * 0.030, 3),
            tire_pressure_rr=round(33.8 - degradation * 0.028, 3),
            brake_pedal_pct=round(min(100.0, braking), 3),
            steering_angle_deg=round(steering, 3),
            latitude=round(48.1351 + tick * 0.00001, 7),
            longitude=round(11.5820 + tick * 0.000015, 7),
        )
        self._tick += 1
        return snapshot

    async def stream(
        self,
        *,
        count: int | None = None,
        realtime: bool = True,
    ) -> AsyncIterator[TelemetrySnapshot]:
        emitted = 0
        while count is None or emitted < count:
            yield self.next_snapshot()
            emitted += 1
            if realtime and (count is None or emitted < count):
                await asyncio.sleep(self.interval_seconds)

    async def run(
        self,
        *,
        store: TelemetryStore,
        count: int,
        realtime: bool = True,
    ) -> int:
        emitted = 0
        async for snapshot in self.stream(count=count, realtime=realtime):
            await store.store(snapshot)
            emitted += 1
        return emitted


async def publish_to_kuksa(
    simulator: SensorSimulator,
    *,
    host: str,
    port: int,
    count: int,
    realtime: bool = True,
    client_factory: Any | None = None,
) -> int:
    """Publish simulator snapshots as current VSS values."""
    if client_factory is None:
        try:
            from kuksa_client.grpc import Datapoint
            from kuksa_client.grpc.aio import VSSClient
        except ImportError as exc:
            raise RuntimeError(
                "Kuksa publishing requires `pip install kuksa-client==0.5.2`"
            ) from exc

        client_factory = VSSClient
        datapoint_factory = Datapoint
    else:
        datapoint_factory = lambda value: value

    emitted = 0
    async with client_factory(host, port) as client:
        async for snapshot in simulator.stream(count=count, realtime=realtime):
            await client.set_current_values(
                {
                    path: datapoint_factory(value)
                    for path, value in snapshot.to_vss().items()
                }
            )
            emitted += 1
    return emitted


async def _main_async(args: argparse.Namespace) -> int:
    simulator = SensorSimulator(
        args.vehicle_id,
        seed=args.seed,
        interval_seconds=args.interval,
        degradation_rate=args.degradation_rate,
    )
    if args.publish:
        return await publish_to_kuksa(
            simulator,
            host=args.host,
            port=args.port,
            count=args.count,
            realtime=not args.no_wait,
        )

    store = InMemoryTelemetryStore(max_points_per_vehicle=args.count)
    async for snapshot in simulator.stream(
        count=args.count,
        realtime=not args.no_wait,
    ):
        await store.store(snapshot)
        print(json.dumps(asdict(snapshot), default=str))
    return len(store.history(args.vehicle_id))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Module 3F VSS telemetry")
    parser.add_argument("--vehicle-id", default=DEFAULT_VEHICLE_ID)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--degradation-rate", type=float, default=1.0)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=55555)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be positive")
    emitted = asyncio.run(_main_async(args))
    print(f"Emitted {emitted} telemetry snapshots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
