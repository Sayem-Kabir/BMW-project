# Deployment Guide — Phase 7E/7F

## Cloud deploy (Module 7F)

Step-by-step Render + Vercel checklist: [`docs/CLOUD_DEPLOY.md`](CLOUD_DEPLOY.md)

Artifacts:
- [`Dockerfile.backend`](../Dockerfile.backend) — monorepo API image (`ml/` + backend)
- [`render.yaml`](../render.yaml) — Blueprint (web + Redis + Postgres + uploads disk)
- [`apps/frontend/vercel.json`](../apps/frontend/vercel.json) — Next.js on Vercel

## Env matrix (Module 7E)

| Variable | Local | Production (Render / Vercel) |
|----------|-------|------------------------------|
| `ENVIRONMENT` | `development` | `production` |
| `SECRET_KEY` | any long string | random ≥24 chars |
| `REQUIRE_AUTH_WRITES` | `false` (optional `true` to test) | `true` |
| `DATABASE_URL` | `postgresql+asyncpg://...@localhost:5432/bmwai_db` | Render Postgres (`+asyncpg`) |
| `DATABASE_URL_SYNC` | `postgresql://...@localhost:5432/bmwai_db` | same host, sync driver |
| `REDIS_URL` | `redis://localhost:6379` | Render Redis / Upstash |
| `CORS_ORIGINS` | empty (localhost defaults) | `https://YOUR_APP.vercel.app` |
| `PUBLIC_API_URL` | `http://127.0.0.1:8000` | `https://YOUR_API.onrender.com` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | same as `PUBLIC_API_URL` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | empty / offline fallback OK |
| `MINIO_*` / uploads | local MinIO or `uploads/` | R2 or Render disk |

Templates: [`.env.example`](../.env.example), [`apps/frontend/.env.example`](../apps/frontend/.env.example).

## Local (Docker Compose)

```bash
cp .env.example .env
cd infra
docker compose -f docker-compose.yml up -d postgres redis
```

Backend:

```bash
cd apps/backend
pip install -r requirements.txt
set PYTHONPATH=F:\BMW;F:\BMW\apps\backend   # Windows
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd apps/frontend
cp .env.example .env.local
npm install
npm run dev
```

## Production target

| Layer | Service | Notes |
|-------|---------|-------|
| Frontend | Vercel | Set `NEXT_PUBLIC_API_URL` to Render API URL |
| Backend | Render (Docker via `Dockerfile.backend`) | Blueprint: [`render.yaml`](../render.yaml) |
| PostgreSQL | Render Postgres | Async URL: `postgresql+asyncpg://...` |
| Redis | Render Redis / Upstash | `REDIS_URL` |
| Objects | Cloudflare R2 or Render disk | clips / heatmaps (`uploads/`) |

## Render

1. Connect the GitHub repo.
2. Apply [`render.yaml`](../render.yaml) (or create a Web Service from `Dockerfile.backend`).
3. Set env vars:
   - `ENVIRONMENT=production`
   - `REQUIRE_AUTH_WRITES=true`
   - `SECRET_KEY` (random)
   - `DATABASE_URL` / `DATABASE_URL_SYNC`
   - `REDIS_URL`
   - `CORS_ORIGINS=https://YOUR_APP.vercel.app`
   - `PUBLIC_API_URL=https://YOUR_API.onrender.com`
4. After first deploy, seed:

```bash
# From a machine with network access to the Render DB
PYTHONPATH=. python scripts/seed_safety_demo.py
PYTHONPATH=. python scripts/seed_xai_shap_6g.py
```

> Render free Postgres may need `DATABASE_URL` rewritten to use `postgresql+asyncpg://` for the FastAPI app and `postgresql://` for sync seed scripts.

## Vercel

1. Import the monorepo; set **Root Directory** to `apps/frontend` (preferred) **or** use root `vercel.json`.
2. Environment:
   - `NEXT_PUBLIC_API_URL=https://YOUR_API.onrender.com`
3. Redeploy after Render URL is known.

## Health probes

- Liveness: `GET /health` → 200 when process is up
- Readiness: `GET /ready` → 200 when DB answers `SELECT 1`, otherwise **503**

Startup warns if `SECRET_KEY` / `CORS_ORIGINS` look unsafe in production.

## Auth (7D)

Demo user (after seed): `demo@bmwai.dev` / `demo1234`

In production, write/ack endpoints require a JWT (`REQUIRE_AUTH_WRITES=true` or `ENVIRONMENT=production`).

## Secrets vault (Phase 10C)

Never bake production secrets into images or git.

| Platform | Approach |
|----------|----------|
| Render | Dashboard env + [secret files](https://render.com/docs/environment-variables) for `SECRET_KEY`, DB URL, `SENTRY_DSN` |
| Doppler | Sync project secrets into deploy runtime |
| AWS | Secrets Manager / SSM Parameter Store → task env |

Required prod secrets: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `SENTRY_DSN` (optional but recommended), MinIO/S3 keys.
