# ISO 21434 — Threat Analysis & Risk Assessment (TARA)
# Spec Section 19.1 — Automotive compliance & cybersecurity
#
# Scope: BMW AI Automotive Intelligence Platform (this repository)

## Assets

| ID | Asset | Description |
|----|-------|-------------|
| A1 | Kuksa VSS broker | Live vehicle signals (speed, GPS, tire, battery) |
| A2 | CV pipeline | Driver / road camera frames → risk engine |
| A3 | Risk / event store | Postgres `safety_events`, Redis pub-sub |
| A4 | Model weights | YOLO / XGBoost / RAG embeddings under `ml/models` |
| A5 | Auth tokens | JWT access + refresh, MFA secrets |
| A6 | Assistant LLM | Ollama / cloud LLM with vehicle context |

## Threats

| ID | Threat | Attack vector | Impact | Likelihood | Risk | Treatment |
|----|--------|---------------|--------|------------|------|-----------|
| T1 | Spoofed Kuksa signals | Malicious client publishes false VSS | False LOW risk / missed CRITICAL | Medium | High | mTLS to broker; signal plausibility checks; fail-safe on feed drop |
| T2 | Adversarial CV input | Crafted frames fool DMS / road YOLO | Missed drowsiness / phantom objects | Medium | High | Input size/MIME limits; face-gate; XAI review on CRITICAL |
| T3 | Unsigned model swap | Replace `.pt` on disk / OTA without verify | Malicious inference | Low | Critical | HMAC `.sig` sidecar (`ml.models.signed_ota`); promote gate |
| T4 | JWT theft | XSS / stolen refresh | Org data exfil | Medium | High | Short access TTL; refresh rotation; HttpOnly cookies in prod |
| T5 | Prompt injection | Jailbreak via assistant chat | Data leak / unsafe advice | High | Medium | Guardrails 11D; refuse ECU hack intents |
| T6 | Webhook abuse | SSRF via notification URL | Internal scan | Low | Medium | Allow-list HTTPS; secrets on webhook |

## Residual risk statement

Residual risk after treatments is **accepted for portfolio/demo** environments.
Production BMW deployments must re-run TARA with OEM-specific threat models,
hardware HSM signing, and UNECE R155 CSMS process integration.

## Related controls in this repo

- Phase 8 auth/RBAC + audit log
- Phase 10 rate limits + upload validation
- Phase 11 promote eval gate + drift PSI
- Section 19.1 signed OTA (`ml/models/signed_ota.py`)
- Section 19.1 fail-safe severity (`ml/risk_engine/fail_safe.py`)
