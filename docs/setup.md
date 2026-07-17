# Local Setup

1. Copy env: `cp .env.example .env`
2. Start stack: `cd infra && docker compose up -d`
3. Backend (host): `cd apps/backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
4. Frontend: `cd apps/frontend && pnpm install && pnpm dev`
5. Migrate: `cd apps/backend && alembic upgrade head`

See root `README.md` for ports and credentials.
