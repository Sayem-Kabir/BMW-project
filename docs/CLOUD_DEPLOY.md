# Cloud deploy checklist — Module 7F

## Backend (Render)

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → select repo → apply [`render.yaml`](../render.yaml).
3. After the first deploy succeeds, open the API URL:
   - `GET /health` → 200
   - `GET /ready` → 200 (DB up)
4. In Render → Environment, set:
   - `CORS_ORIGINS=https://YOUR_APP.vercel.app`
   - `PUBLIC_API_URL=https://YOUR_API.onrender.com`
5. Seed (Render Shell or local with cloud `DATABASE_URL`):

```bash
export PYTHONPATH=/app:/app/apps/backend
python /app/scripts/seed_safety_demo.py
# optional SHAP demo (needs ML models; may be heavy on free tier)
# python /app/scripts/seed_xai_shap_6g.py
```

Login: `demo@bmwai.dev` / `demo1234`

## Frontend (Vercel)

1. Vercel → **Add New Project** → import the same GitHub repo.
2. Set **Root Directory** to `apps/frontend`.
3. Environment variable:
   - `NEXT_PUBLIC_API_URL=https://YOUR_API.onrender.com`
4. Deploy → open the Vercel URL → Dashboard / Demo / Login.

## Smoke after both are live

Use the full Module 8G checklist: [`docs/CLOUD_ACCEPTANCE.md`](CLOUD_ACCEPTANCE.md)

- [ ] `/health` on Render (`phase` 8)
- [ ] `/metrics` scrapes
- [ ] Login from Vercel UI (`demo@bmwai.dev`)
- [ ] Viewer denied demo start (`viewer@bmwai.dev`)
- [ ] Fleet dashboard loads vehicles
- [ ] One XAI explain (Grad-CAM/IG or engine SHAP)
- [ ] Assistant offline fallback answer

## Local Docker build sanity

```bash
docker build -f Dockerfile.backend -t bmw-ai-api .
docker run --rm -p 8000:8000 -e DATABASE_URL=... -e REDIS_URL=... bmw-ai-api
```
