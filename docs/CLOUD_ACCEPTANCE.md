# Cloud acceptance checklist — Module 8G

Run after [CLOUD_DEPLOY.md](CLOUD_DEPLOY.md) cutover. Fill in live URLs.

| Service | URL |
|---------|-----|
| Frontend (Vercel) | `https://YOUR_APP.vercel.app` |
| API (Render) | `https://YOUR_API.onrender.com` |

## Preflight

1. Render: `GET /health` → 200, `"phase": "8"`
2. Render: `GET /ready` → 200 (`database: ok`)
3. Render: `GET /metrics` → Prometheus text (Module 8F)
4. Vercel loads with `NEXT_PUBLIC_API_URL` pointing at Render
5. CORS: `CORS_ORIGINS` includes the Vercel origin

## Seed (once)

```bash
# Render shell or local with cloud DATABASE_URL
export PYTHONPATH=/app:/app/apps/backend
python /app/scripts/seed_safety_demo.py
```

Accounts:
- Operator / manager: `demo@bmwai.dev` / `demo1234` (`fleet_manager`)
- Viewer (read-only): `viewer@bmwai.dev` / `viewer1234` (Module 8E)

## Functional acceptance

- [ ] Login as demo user from Vercel `/login`
- [ ] Fleet `/dashboard` shows vehicles
- [ ] `/demo` Quick run starts (viewer account must get 403 on start)
- [ ] Safety / alerts ack as manager
- [ ] `/dashboard/xai` Grad-CAM + IG (`attribution=both`)
- [ ] Vehicle SHAP explain (if `seed_xai_shap_6g.py` run)
- [ ] Assistant offline answer for TPMS / OBD question
- [ ] Optional: Kuksa bridge status `GET /api/v1/kuksa/bridge/status` (broker may be offline on free Render)

## Models

Cold demo OK without weights. Optional: `python -m ml.models.download_registry --check` locally; see Module 8C/8D in [TRAINING.md](TRAINING.md).

## Sign-off

Date: ________  Reviewer: ________  Pass / Fail: ________
