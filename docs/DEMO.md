# Demo Checklist — Phase 7G

Hand-off checklist for a BMW-facing walkthrough. Cold demo works **without GPU weights** (CPU/synthetic fallbacks).

## Local prep (5–10 min)

1. Start Postgres + Redis (`infra/docker-compose.yml` or the containers in the README).
2. Start backend (`uvicorn` on `:8000`) and frontend (`npm run dev` / `pnpm dev` on `:3000`).
3. Seed (from repo root; use a Python that has backend deps):

```bash
# Windows PowerShell
$env:PYTHONPATH = "F:\BMW;F:\BMW\apps\backend"
python scripts/seed_safety_demo.py
python scripts/seed_xai_shap_6g.py   # optional; needs trained maintenance models
```

```bash
# Linux / macOS / Render shell
export PYTHONPATH=/path/to/BMW:/path/to/BMW/apps/backend
python scripts/seed_safety_demo.py
```

4. Optional video: place `ml/demo/assets/demo_drive.mp4` (otherwise synthetic frames).

## Walkthrough (operator)

1. Open [http://localhost:3000/demo](http://localhost:3000/demo) → **Start demo** (or Quick run).
2. [Dashboard](http://localhost:3000/dashboard) — fleet cards / alerts update.
3. [Safety](http://localhost:3000/safety) — risk gauge + event feed.
4. Vehicle detail → select **engine** → **Explain SHAP** (Module 6G).
5. [Alerts](http://localhost:3000/dashboard/alerts) — acknowledge + XAI panel.
6. [Vision XAI](http://localhost:3000/dashboard/xai) — Grad-CAM and/or Integrated Gradients (8A).
7. [Assistant](http://localhost:3000/assistant) — ask “Why is my TPMS warning on?”
8. Login: `demo@bmwai.dev` / `demo1234` (manager). Viewer: `viewer@bmwai.dev` / `viewer1234` (8E read-only).
9. Optional Kuksa: `POST /api/v1/kuksa/bridge/start` when databroker is up (8B).
10. Metrics: `GET http://localhost:8000/metrics` (8F).

## CLI alternative

```bash
export PYTHONPATH=.
python -m ml.demo.demo_runner --synthetic-only --max-frames 30 --fps 4
```

## Cloud demo

After [CLOUD_DEPLOY.md](CLOUD_DEPLOY.md) / [DEPLOYMENT.md](DEPLOYMENT.md) — full sign-off: [CLOUD_ACCEPTANCE.md](CLOUD_ACCEPTANCE.md).

| Layer | URL placeholder |
|-------|-----------------|
| Frontend (Vercel) | `https://YOUR_APP.vercel.app` |
| API (Render) | `https://YOUR_API.onrender.com` |

1. Confirm `NEXT_PUBLIC_API_URL` points at Render.
2. Hit `GET /health` and `GET /ready` on the API; seed once if the DB is empty.
3. Run the same walkthrough against the public URLs.

## Models (gitignored)

Large weights stay **untracked** (`yolov8*.pt`, `ml/models/*.pt`). Without them, driver/road paths use CPU/synthetic fallbacks — enough for a cold demo.

Optional download (Ultralytics auto-fetches on first use, or place manually):

```bash
# Example: medium YOLO weights at repo root or apps/backend/ (both gitignored)
# ultralytics will pull yolov8n.pt / yolov8m.pt when first invoked
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

Trained domain weights from Kaggle go in `ml/models/` — see [TRAINING.md](TRAINING.md).
