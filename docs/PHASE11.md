# Spec Phase 11 — ML/AI Maturity & Governance

## Modules

| Module | Deliverable |
|--------|-------------|
| **11A** | `POST /api/v1/models/{name}/promote` with eval gate (prod ≥ 0.80); MLflow when available, local registry fallback; `GET .../versions` |
| **11B** | PSI drift vs `ml/governance/baselines/telemetry_baseline.json` — `POST /api/v1/ml/drift/check` |
| **11C** | `POST /api/v1/events/detail/{id}/feedback` + `GET /api/v1/events/feedback/export` CSV; columns via alembic `004` |
| **11D** | Assistant input/output guardrails; RAGAS-inspired eval set + `POST /api/v1/ml/assistant/eval` |

## Exit criteria

1. **Promote gate:** `eval_metric_value < min` (or `< 0.80` for Production) → HTTP 400, no stage change.
2. **Assistant eval score:** `POST /api/v1/ml/assistant/eval` returns `score` and `pass` (≥ 0.75).

## Quick demos

```bash
# Drift (admin JWT)
curl -X POST http://127.0.0.1:8001/api/v1/ml/drift/check \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"features":{"speed_kmh":[120,125,130,140,150,155],"ear":[0.1,0.11,0.09],"braking_freq":[2,2.5,3]}}'

# Blocked promote
curl -X POST http://127.0.0.1:8001/api/v1/models/driver_monitor/promote \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"target_stage":"Production","eval_metric_value":0.5,"min_eval_metric":0.9}'

# RAG eval
curl -X POST http://127.0.0.1:8001/api/v1/ml/assistant/eval \
  -H "Authorization: Bearer $TOKEN"
```

## Migration

```bash
cd apps/backend
alembic upgrade head
# or rely on create_all for local dev (new feedback_* columns)
```
