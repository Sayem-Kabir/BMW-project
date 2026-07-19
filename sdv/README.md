# Module 3F — Kuksa VSS I/O

Module 3F converts Kuksa VSS updates into typed telemetry snapshots and stores
them either in memory or in the backend's `vehicle_telemetry` table.

## Broker-free demo

Generate deterministic JSON telemetry without Docker or vehicle hardware:

```powershell
python -m sdv.mock.sensor_simulator --count 10 --no-wait
```

Remove `--no-wait` to emit at the configured real-time interval. Use
`--seed`, `--interval`, and `--degradation-rate` to control the simulation.

## Kuksa Databroker demo

Start the broker already defined in `infra/docker-compose.yml`:

```powershell
docker compose -f infra/docker-compose.yml up -d kuksa-databroker
```

Publish simulated VSS values:

```powershell
python -m sdv.mock.sensor_simulator --count 100 --publish
```

The runtime dependency is `kuksa-client==0.5.2`. Host and port default to
`localhost:55555`; the backend reads `KUKSA_HOST` and `KUKSA_PORT`.

## Subscription and storage

`sdv.kuksa.KuksaSignalSubscriber` supports:

- `current()` for a one-shot snapshot
- `stream()` for async snapshots
- `run()` for continuous subscribe-and-store operation

For assistant / API consumers that want a flat dict (including short aliases
like `tire_fl` and `battery_soc`):

```python
from sdv.kuksa.signal_subscriber import get_current_telemetry

telemetry = await get_current_telemetry(vehicle_id)
```

Use `InMemoryTelemetryStore` for tests/demos. The backend service
`app.services.kuksa_service` builds a subscriber with
`SqlAlchemyTelemetryStore`, which persists to TimescaleDB/PostgreSQL through
the existing async session factory.

The VSS-to-database field contract is stored in
`sdv/kuksa/vss_config.json`. Partial Kuksa updates are merged with the latest
known values before each snapshot is stored.
