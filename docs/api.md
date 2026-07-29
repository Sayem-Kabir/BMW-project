# API Reference

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Phase 0 endpoints (scaffolded)

| Area | Base path |
|------|-----------|
| Auth | `/api/v1/auth` |
| Driver monitoring | `/api/v1/driver` |
| Road understanding | `/api/v1/road` |
| Risk | `/api/v1/risk` |
| Maintenance | `/api/v1/maintenance` |
| Assistant | `/api/v1/assistant` |
| Fleet | `/api/v1/fleet` |
| Events | `/api/v1/events` |
| Analytics | `/api/v1/analytics` |
| XAI | `/api/v1/xai` |
| Telemetry | `/api/v1/telemetry` |
| Fleet WS | `/api/v1/fleet/ws/{org_id}` |

Full contract: section 11 of `BMW_AI_Platform_Complete_Spec.md`.

## Phase 10 API notes

- **Error envelope:** failures return `{"error": {"code": "...", "message": "..."}}` (not only FastAPI `detail`).
- **Pagination:** list endpoints accept `limit` + `offset` where noted (fleet alerts, admin audit).
- **Idempotency:** `POST /api/v1/fleet/vehicles` honors `Idempotency-Key` header.
- **Versioning:** `/api/v1` is stable; breaking changes go to `/api/v2`.
- **Rate limit:** `POST /api/v1/auth/login` — 5 attempts / minute / IP → `429`.
- **Models:** `GET/POST /api/v1/models/...` promote with eval gate (Phase 11A); optional MLflow.
- **ML governance:** `POST /api/v1/ml/drift/check`, `POST /api/v1/ml/assistant/eval`, guardrail probe.
- **Event feedback:** `POST /api/v1/events/detail/{id}/feedback`, `GET /api/v1/events/feedback/export`.
