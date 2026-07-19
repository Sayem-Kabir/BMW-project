"""Module 3F — Kuksa VSS subscription, snapshots, and telemetry storage."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

logger = logging.getLogger(__name__)

VSS_TO_FIELD = {
    "Vehicle.Speed": "speed_kmh",
    "Vehicle.OBD.RPM": "rpm",
    "Vehicle.OBD.OilTemp": "oil_temp_c",
    "Vehicle.OBD.CoolantTemp": "coolant_temp_c",
    "Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure": "tire_pressure_fl",
    "Vehicle.Chassis.Axle.Row1.Wheel.Right.Tire.Pressure": "tire_pressure_fr",
    "Vehicle.Chassis.Axle.Row2.Wheel.Left.Tire.Pressure": "tire_pressure_rl",
    "Vehicle.Chassis.Axle.Row2.Wheel.Right.Tire.Pressure": "tire_pressure_rr",
    "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current": "battery_soc_pct",
    "Vehicle.Powertrain.TractionBattery.StateOfHealth": "battery_health_pct",
    "Vehicle.Chassis.Brake.PedalPosition": "brake_pedal_pct",
    "Vehicle.Chassis.SteeringWheel.Angle": "steering_angle_deg",
    "Vehicle.CurrentLocation.Latitude": "latitude",
    "Vehicle.CurrentLocation.Longitude": "longitude",
}
VSS_SIGNALS = tuple(VSS_TO_FIELD)


@dataclass(frozen=True)
class TelemetrySnapshot:
    vehicle_id: str
    timestamp: datetime
    speed_kmh: float | None = None
    rpm: int | None = None
    oil_temp_c: float | None = None
    coolant_temp_c: float | None = None
    battery_soc_pct: float | None = None
    battery_health_pct: float | None = None
    tire_pressure_fl: float | None = None
    tire_pressure_fr: float | None = None
    tire_pressure_rl: float | None = None
    tire_pressure_rr: float | None = None
    brake_pedal_pct: float | None = None
    steering_angle_deg: float | None = None
    latitude: float | None = None
    longitude: float | None = None

    @classmethod
    def from_vss(
        cls,
        vehicle_id: str,
        values: Mapping[str, Any],
        *,
        timestamp: datetime | None = None,
    ) -> "TelemetrySnapshot":
        fields: dict[str, Any] = {}
        for path, field in VSS_TO_FIELD.items():
            value = values.get(path)
            if value is None:
                continue
            fields[field] = int(round(float(value))) if field == "rpm" else float(value)
        return cls(
            vehicle_id=str(vehicle_id),
            timestamp=timestamp or datetime.now(timezone.utc),
            **fields,
        )

    def to_vss(self) -> dict[str, float | int]:
        values = asdict(self)
        return {
            path: values[field]
            for path, field in VSS_TO_FIELD.items()
            if values[field] is not None
        }

    def to_model_kwargs(self) -> dict[str, Any]:
        values = asdict(self)
        values["time"] = values.pop("timestamp")
        values["vehicle_id"] = UUID(self.vehicle_id)
        return values

    def as_context_dict(self) -> dict[str, Any]:
        """Flat dict for assistant / API consumers, including short aliases."""
        values = asdict(self)
        values.update(
            {
                "tire_fl": self.tire_pressure_fl,
                "tire_fr": self.tire_pressure_fr,
                "tire_rl": self.tire_pressure_rl,
                "tire_rr": self.tire_pressure_rr,
                "battery_soc": self.battery_soc_pct,
                "oil_temp": self.oil_temp_c,
            }
        )
        return values


class TelemetryStore(Protocol):
    async def store(self, snapshot: TelemetrySnapshot) -> None: ...


class InMemoryTelemetryStore:
    """Small async store for demos, tests, and broker-free development."""

    def __init__(self, *, max_points_per_vehicle: int = 500) -> None:
        if max_points_per_vehicle < 1:
            raise ValueError("max_points_per_vehicle must be positive")
        self.max_points_per_vehicle = max_points_per_vehicle
        self._points: dict[str, list[TelemetrySnapshot]] = defaultdict(list)

    async def store(self, snapshot: TelemetrySnapshot) -> None:
        points = self._points[snapshot.vehicle_id]
        points.append(snapshot)
        del points[: max(0, len(points) - self.max_points_per_vehicle)]

    def latest(self, vehicle_id: str) -> TelemetrySnapshot | None:
        points = self._points.get(str(vehicle_id), ())
        return points[-1] if points else None

    def history(self, vehicle_id: str) -> tuple[TelemetrySnapshot, ...]:
        return tuple(self._points.get(str(vehicle_id), ()))


class SqlAlchemyTelemetryStore:
    """Persist snapshots through the backend's async SQLAlchemy session factory."""

    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self.session_factory = session_factory

    async def store(self, snapshot: TelemetrySnapshot) -> None:
        try:
            from app.models.telemetry import VehicleTelemetry
        except ImportError as exc:
            raise RuntimeError(
                "Backend package is unavailable; add apps/backend to PYTHONPATH"
            ) from exc

        async with self.session_factory() as session:
            session.add(VehicleTelemetry(**snapshot.to_model_kwargs()))
            await session.commit()


def _unwrap_updates(updates: Mapping[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for path, datapoint in updates.items():
        if datapoint is None:
            continue
        values[path] = getattr(datapoint, "value", datapoint)
    return values


def _default_client_factory(host: str, port: int):
    try:
        from kuksa_client.grpc.aio import VSSClient
    except ImportError as exc:
        raise RuntimeError(
            "Kuksa support requires `pip install kuksa-client==0.5.2`"
        ) from exc
    return VSSClient(host, port)


class KuksaSignalSubscriber:
    """Consume partial VSS updates, build snapshots, and pass them to a store."""

    def __init__(
        self,
        vehicle_id: str,
        *,
        store: TelemetryStore,
        host: str = "localhost",
        port: int = 55555,
        signals: Sequence[str] = VSS_SIGNALS,
        client_factory: Callable[[str, int], Any] = _default_client_factory,
    ) -> None:
        self.vehicle_id = str(vehicle_id)
        self.store = store
        self.host = host
        self.port = int(port)
        self.signals = tuple(signals)
        self.client_factory = client_factory
        self._values: dict[str, Any] = {}

    async def current(self) -> TelemetrySnapshot:
        async with self.client_factory(self.host, self.port) as client:
            updates = await client.get_current_values(list(self.signals))
        self._values.update(_unwrap_updates(updates))
        return TelemetrySnapshot.from_vss(self.vehicle_id, self._values)

    async def stream(self, *, max_updates: int | None = None) -> AsyncIterator[TelemetrySnapshot]:
        count = 0
        async with self.client_factory(self.host, self.port) as client:
            logger.info(
                "Connected to Kuksa Databroker at %s:%s for vehicle %s",
                self.host,
                self.port,
                self.vehicle_id,
            )
            async for updates in client.subscribe_current_values(list(self.signals)):
                self._values.update(_unwrap_updates(updates))
                snapshot = TelemetrySnapshot.from_vss(
                    self.vehicle_id,
                    self._values,
                )
                await self.store.store(snapshot)
                yield snapshot
                count += 1
                if max_updates is not None and count >= max_updates:
                    break

    async def run(self, *, max_updates: int | None = None) -> int:
        count = 0
        async for _ in self.stream(max_updates=max_updates):
            count += 1
        return count


async def subscribe_and_store(
    vehicle_id: str,
    *,
    store: TelemetryStore,
    host: str = "localhost",
    port: int = 55555,
    max_updates: int | None = None,
) -> int:
    """Convenience entry point used by backend jobs and local demos."""
    subscriber = KuksaSignalSubscriber(
        vehicle_id,
        store=store,
        host=host,
        port=port,
    )
    return await subscriber.run(max_updates=max_updates)


async def get_current_telemetry(
    vehicle_id: str,
    *,
    host: str = "localhost",
    port: int = 55555,
    store: TelemetryStore | None = None,
    client_factory: Callable[[str, int], Any] | None = None,
) -> dict[str, Any]:
    """One-shot live snapshot for assistant / API consumers.

    Matches the Phase 5 telemetry_injector import contract:
    `from sdv.kuksa.signal_subscriber import get_current_telemetry`
    """
    kwargs: dict[str, Any] = {
        "store": store or InMemoryTelemetryStore(max_points_per_vehicle=1),
        "host": host,
        "port": port,
    }
    if client_factory is not None:
        kwargs["client_factory"] = client_factory
    snapshot = await KuksaSignalSubscriber(vehicle_id, **kwargs).current()
    return snapshot.as_context_dict()
