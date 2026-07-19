"""Tests for Module 3F Kuksa subscription and mock telemetry."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sdv.kuksa import (
    InMemoryTelemetryStore,
    KuksaSignalSubscriber,
    TelemetrySnapshot,
    VSS_TO_FIELD,
    get_current_telemetry,
)
from sdv.mock import SensorSimulator, publish_to_kuksa


class Datapoint:
    def __init__(self, value):
        self.value = value


class FakeClient:
    def __init__(self, updates=()):
        self.updates = list(updates)
        self.requested_signals = None
        self.published = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def get_current_values(self, signals):
        self.requested_signals = signals
        return self.updates[0]

    async def subscribe_current_values(self, signals):
        self.requested_signals = signals
        for update in self.updates:
            yield update

    async def set_current_values(self, values):
        self.published.append(values)


def test_snapshot_round_trips_vss_values():
    values = {
        "Vehicle.Speed": 72.5,
        "Vehicle.OBD.RPM": 2400.4,
        "Vehicle.Powertrain.TractionBattery.StateOfHealth": 91.0,
    }
    snapshot = TelemetrySnapshot.from_vss(
        "00000000-0000-0000-0000-000000000001",
        values,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert snapshot.speed_kmh == 72.5
    assert snapshot.rpm == 2400
    assert snapshot.battery_health_pct == 91.0
    assert snapshot.to_vss() == {
        "Vehicle.Speed": 72.5,
        "Vehicle.OBD.RPM": 2400,
        "Vehicle.Powertrain.TractionBattery.StateOfHealth": 91.0,
    }


@pytest.mark.asyncio
async def test_subscriber_merges_partial_updates_and_stores_snapshots():
    client = FakeClient(
        [
            {"Vehicle.Speed": Datapoint(30.0)},
            {"Vehicle.OBD.RPM": Datapoint(1800)},
        ]
    )
    store = InMemoryTelemetryStore()
    subscriber = KuksaSignalSubscriber(
        "vehicle-1",
        store=store,
        client_factory=lambda _host, _port: client,
    )

    assert await subscriber.run(max_updates=2) == 2
    history = store.history("vehicle-1")
    assert len(history) == 2
    assert history[0].speed_kmh == 30.0
    assert history[0].rpm is None
    assert history[1].speed_kmh == 30.0
    assert history[1].rpm == 1800


@pytest.mark.asyncio
async def test_memory_store_enforces_history_limit():
    store = InMemoryTelemetryStore(max_points_per_vehicle=2)
    simulator = SensorSimulator(interval_seconds=0.01)
    assert await simulator.run(store=store, count=3, realtime=False) == 3
    history = store.history(simulator.vehicle_id)
    assert len(history) == 2
    assert history[-1].timestamp > history[0].timestamp


def test_simulator_is_deterministic_for_same_seed_and_time():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = SensorSimulator(seed=7, start_time=start).next_snapshot()
    second = SensorSimulator(seed=7, start_time=start).next_snapshot()
    assert first == second
    assert 0.0 <= first.speed_kmh <= 150.0
    assert 0.0 <= first.battery_soc_pct <= 100.0


@pytest.mark.asyncio
async def test_simulator_can_publish_without_real_broker():
    client = FakeClient()
    simulator = SensorSimulator(seed=1, interval_seconds=0.01)
    emitted = await publish_to_kuksa(
        simulator,
        host="unused",
        port=55555,
        count=2,
        realtime=False,
        client_factory=lambda _host, _port: client,
    )
    assert emitted == 2
    assert len(client.published) == 2
    assert "Vehicle.Speed" in client.published[0]


def test_json_signal_contract_matches_python_mapping():
    path = Path(__file__).parents[1] / "kuksa" / "vss_config.json"
    assert json.loads(path.read_text(encoding="utf-8")) == VSS_TO_FIELD


@pytest.mark.asyncio
async def test_get_current_telemetry_exposes_assistant_aliases():
    client = FakeClient(
        [
            {
                "Vehicle.Speed": Datapoint(64.0),
                "Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure": Datapoint(32.5),
                "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current": Datapoint(
                    77.0
                ),
                "Vehicle.OBD.OilTemp": Datapoint(91.0),
            }
        ]
    )
    telemetry = await get_current_telemetry(
        "vehicle-1",
        client_factory=lambda _host, _port: client,
    )
    assert telemetry["speed_kmh"] == 64.0
    assert telemetry["tire_fl"] == 32.5
    assert telemetry["battery_soc"] == 77.0
    assert telemetry["oil_temp"] == 91.0
