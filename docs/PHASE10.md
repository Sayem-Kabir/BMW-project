# Spec Phase 10 — Production Hardening & Observability

## Modules

| Module | Deliverable |
|--------|-------------|
| **10A** | Auth/risk pytest (existing) + Playwright `apps/frontend/e2e/` + k6/Locust under `scripts/load/` |
| **10B** | `SENTRY_DSN`, JSON `structlog`, `/metrics` + Celery/inference gauges, Grafana Phase 10 dashboard |
| **10C** | Login rate limit (5/min/IP → 429), upload MIME/size validation, secrets vault notes below |
| **10D** | Error envelope `{"error":{"code","message"}}`, list `limit`/`offset`, `Idempotency-Key` on vehicle create, `/api/v1` stability note |
| **10E** | Audit on event ack + `MODEL_PROMOTED` via `POST /api/v1/models/{name}/promote` |

## Exit criteria checklist

1. **Sentry** — set `SENTRY_DSN`, hit `GET /api/v1/debug/sentry-test`, confirm event in Sentry.
2. **Login 429** — six failed `POST /api/v1/auth/login` from same IP within 60s → HTTP 429.
3. **Dashboard queries** — see [sql/phase10_explain.sql](sql/phase10_explain.sql) for `EXPLAIN ANALYZE` helpers + recommended indexes.

## Secrets (production)

Do **not** commit production `.env`. Prefer:

- **Render** — secret files / dashboard env (see [DEPLOYMENT.md](DEPLOYMENT.md))
- **Doppler / AWS Secrets Manager** — inject `SECRET_KEY`, `DATABASE_URL`, `SENTRY_DSN`, MinIO keys at deploy time

Local: copy `.env.example` → `.env`.

## API versioning

`/api/v1/...` is stable. Breaking changes ship under `/api/v2/...` (package reserved; empty until needed).

## Load tests

```bash
# k6 WebSocket fan-out
k6 run scripts/load/ws_fleet_k6.js

# Locust HTTP
pip install locust
locust -f scripts/load/locustfile.py --host http://127.0.0.1:8000
```

## Playwright e2e

```bash
cd apps/frontend
pnpm install
npx playwright install chromium
# API + UI + seed users running
pnpm test:e2e
```
