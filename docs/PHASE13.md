# Spec Phase 13 — Performance & Optimization Pass

## Deliverables

| Area | What shipped |
|------|----------------|
| **API** | `GZipMiddleware`; `Cache-Control` on `/analytics/fleet/leaderboard` + incidents; env-tunable DB pool (`DB_POOL_SIZE` / `DB_MAX_OVERFLOW`) |
| **WS** | Org vehicle filter + ~`WS_MAX_HZ` (default 4) throttle on `/api/v1/fleet/ws/{org_id}` |
| **Telemetry** | `BufferedTelemetryStore` (1–5s flush); LTTB `?max_points=` on telemetry history |
| **Risk** | Hard overrides evaluated **before** full 4A scoring; CRITICAL → short-circuit |
| **Assistant** | In-memory semantic cache (bag-of-words cosine) |
| **Celery** | Queues `ml_tasks` vs `notifications` + `app.tasks.notifications` |
| **DB** | Alembic `006` partial indexes on unacked `safety_events`; Timescale CAGG SQL stub |
| **CV** | Adaptive frame sampling + face gate ([docs/ml/phase13_cv_opts.md](ml/phase13_cv_opts.md)) |
| **Frontend** | Virtualized `VehicleGrid` (100+), `React.memo` charts, `next/dynamic` map/chart split |

## Exit criteria

1. Run Phase 10 k6 at scale: `k6 run scripts/load/ws_fleet_k6.js` — target p95 dashboard-related HTTP &lt; 300ms under load (measure locally).
2. `EXPLAIN ANALYZE` open-alert queries use `idx_safety_events_unacked` — see [sql/phase10_explain.sql](sql/phase10_explain.sql) + migration `006`.
3. CV throughput knobs documented in [ml/phase13_cv_opts.md](ml/phase13_cv_opts.md) (measure with `py-spy` when hardware available).

## Quick demos

```bash
# Gzip + cache headers
curl -I -H "Accept-Encoding: gzip" http://127.0.0.1:8001/api/v1/analytics/fleet/leaderboard \
  -H "Authorization: Bearer $TOKEN"

# LTTB downsample
curl "http://127.0.0.1:8001/api/v1/telemetry/$VID?max_points=40" -H "Authorization: Bearer $TOKEN"

# Override-first short-circuit (unit)
cd apps/backend
python -m pytest ../../ml/risk_engine/tests/test_rules.py -q
```

## Env (optional)

```
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
WS_MAX_HZ=4
TELEMETRY_BATCH_ENABLED=true
TELEMETRY_BATCH_FLUSH_SEC=2
ANALYTICS_CACHE_MAX_AGE_SEC=30
ASSISTANT_SEMANTIC_CACHE_TTL_SEC=300
ASSISTANT_SEMANTIC_CACHE_THRESHOLD=0.92
```

## Migration

```bash
cd apps/backend
alembic upgrade head
# optional Timescale CAGGs:
# psql $DATABASE_URL_SYNC -f ../../docs/sql/phase13_continuous_aggregates.sql
```

## Deferred (documented; optional hardening)

- Hardware HSM signing (HMAC demo in-repo)
- Live Stripe keys (SDK wired when `STRIPE_SECRET_KEY` set)
- Production Kafka cluster (producer + buffer drain API at `/industry/kafka/buffer`)
- Feast server (file-backed stub + `/industry/feast/entities`)
- Optical-flow beyond last-frame reuse; inference HPA; CDN for clips
