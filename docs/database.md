# Database Schema

Nine domain tables (+ `users` for auth):

- `organizations`, `users`, `vehicles`, `drivers`
- `vehicle_telemetry` (TimescaleDB hypertable when extension present)
- `driver_sessions`, `safety_events`
- `maintenance_predictions`, `driver_scores`
- `assistant_conversations`

## Migrations

```bash
cd apps/backend
alembic upgrade head
```

Initial revision: `alembic/versions/001_initial_schema.py`
