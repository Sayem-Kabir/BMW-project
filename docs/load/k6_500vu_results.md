# Load / exit-criteria measurement notes — Spec Phase 13

## k6 (WebSocket + health p95)

```bash
# Smoke (default 10 VUs)
k6 run scripts/load/ws_fleet_k6.js

# Scale toward exit criterion (500 concurrent)
k6 run -e VUS=500 -e DURATION=2m -e BASE_HTTP=http://127.0.0.1:8001 -e BASE_WS=ws://127.0.0.1:8001 scripts/load/ws_fleet_k6.js
```

Thresholds in script: `http_req_duration p(95)<300` and check rate > 85%.

| Date | VUs | Duration | p95 health | Checks | Notes |
|------|-----|----------|------------|--------|-------|
| _fill after local run_ | 500 | 2m | | | API on :8001 |

## EXPLAIN ANALYZE

See [sql/phase10_explain.sql](../sql/phase10_explain.sql) and migration `006_perf_indexes_13` (`idx_safety_events_unacked`).

## CV throughput

Document FPS before/after knobs in [ml/phase13_cv_opts.md](../ml/phase13_cv_opts.md) using:

```bash
py-spy record -o cv_profile.svg -- python -c "from ml.driver_monitoring.pipeline import get_pipeline; ..."
```
