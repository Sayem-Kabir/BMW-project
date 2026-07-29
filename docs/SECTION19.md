# Spec Section 19 — Advanced Industry-Level Features

Portfolio differentiators beyond the core Phases 0–13 product path.

## 19.1 Compliance & cybersecurity

| Item | Location |
|------|----------|
| ISO 21434 TARA | [docs/compliance/ISO21434_TARA.md](compliance/ISO21434_TARA.md) |
| Signed OTA weights | `ml/models/signed_ota.py` — HMAC `.sig` sidecar; `scripts/export_onnx.py` signs exports |
| ISO 26262-style fail-safe | `ml/risk_engine/fail_safe.py` wired in `risk_service.evaluate_risk` |

## 19.2 Edge AI & OTA

| Item | Location |
|------|----------|
| ONNX export | `python scripts/export_onnx.py --model ml/models/driver_monitor_best.pt` |
| Edge/cloud split | `GET /api/v1/industry/edge/decide?risk_score=` |
| OTA canary | `POST/GET /api/v1/industry/ota/canary` + UI `/admin/dashboard/ota` |

## 19.3 Event-driven backbone

| Item | Location |
|------|----------|
| Redpanda | `infra/docker-compose.yml` profile `industry` → `docker compose --profile industry up -d redpanda` |
| Kafka bus | `app/services/kafka_bus.py` + `GET /api/v1/industry/kafka/buffer` |
| Feast stub | `ml/feature_store/feast_stub.py` + `GET /api/v1/industry/feast/entities` |
| Event replay | `POST /api/v1/industry/replay` |

## 19.4 Advanced ML/AI

| Item | Location |
|------|----------|
| Kalman fusion demo | `GET /api/v1/industry/fusion/demo` |
| Multi-agent supervisor | `ml/assistant/agent.py` (`multi_agent=True`) |
| FedAvg round | `POST /api/v1/industry/federated/round` |
| Digital twin | `GET /api/v1/industry/twin/{id}` + UI `/fleet/dashboard/twin` |

## 19.5 Infrastructure & DevOps

| Item | Location |
|------|----------|
| Helm scaffold | `infra/helm/bmw-ai/` (+ optional `autoscaling.enabled` HPA) |
| Terraform scaffold | `infra/terraform/main.tf` |
| Chaos probe | `POST /api/v1/industry/chaos/{redis\|postgres\|both}` (super_admin) |

## 19.6 Business / SaaS

| Item | Location |
|------|----------|
| Stripe test checkout stub | `POST /api/v1/industry/billing/checkout` |
| Insurance telematics | `GET /api/v1/industry/insurance/{driver_id}` |
| EV carbon/efficiency | `GET /api/v1/industry/carbon/{vehicle_id}` |
| Webhooks | Phase 12A `/api/v1/notifications/webhooks` |
| Per-tenant rate limit | `tenant_rate_limit` dependency (`TENANT_RATE_LIMIT`) |
| GDPR export/erasure | `GET/DELETE /api/v1/users/{id}/export\|data` |
| Forgot/reset password | `POST /api/v1/auth/forgot-password`, `/reset-password` |

## Quick demos

```bash
# Edge vs cloud
curl "http://127.0.0.1:8001/api/v1/industry/edge/decide?risk_score=80" -H "Authorization: Bearer $TOKEN"

# Fusion + FedAvg
curl http://127.0.0.1:8001/api/v1/industry/fusion/demo -H "Authorization: Bearer $TOKEN"
curl -X POST http://127.0.0.1:8001/api/v1/industry/federated/round -H "Authorization: Bearer $TOKEN"

# Chaos (super_admin)
curl -X POST http://127.0.0.1:8001/api/v1/industry/chaos/redis -H "Authorization: Bearer $TOKEN"
```
