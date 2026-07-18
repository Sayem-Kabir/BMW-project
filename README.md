# BMW AI Automotive Intelligence Platform

> A production-grade, full-stack automotive AI platform demonstrating ADAS, Software-Defined Vehicle (SDV), predictive maintenance, and explainable AI capabilities aligned with BMW Group's strategic direction.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ 
- Node.js 20+
- Docker Desktop 4.x (8GB RAM allocated)
- Git

### Phase 0 Setup (5 minutes)

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start all services
cd infra
docker compose -f docker-compose.yml up -d

# 3. Wait for services to be healthy
docker compose ps
```

This starts:
- PostgreSQL + TimescaleDB (port 5432)
- Redis (port 6379)
- ChromaDB (port 8001)
- MinIO (port 9000 / 9001)
- FastAPI backend (port 8000)
- Next.js frontend (port 3000)
- MLflow (port 5000)
- Ollama LLM (port 11434)
- Kuksa Databroker (port 55555)
- Prometheus (port 9090)
- Grafana (port 3001)

### Access Points

| Service | URL | Login |
|---------|-----|-------|
| Frontend Dashboard | http://localhost:3000 | N/A |
| API Docs (Swagger) | http://localhost:8000/docs | N/A |
| MLflow Tracking | http://localhost:5000 | N/A |
| MinIO Admin | http://localhost:9001 | minioadmin / minioadmin123 |
| Grafana Monitoring | http://localhost:3001 | admin / admin123 |

## 📊 Project Structure

```
bmw-ai-platform/
├── apps/
│   ├── frontend/           # Next.js 14 React dashboard
│   └── backend/            # FastAPI REST + WebSocket API
├── ml/
│   ├── driver_monitoring/  # Drowsiness, phone usage detection
│   ├── cabin_intelligence/ # Occupancy, child detection
│   ├── road_understanding/ # Segmentation, YOLO/ByteTrack, MiDaS depth
│   ├── predictive_maintenance/  # Component failure forecasting
│   ├── risk_engine/        # Risk scoring aggregation
│   ├── assistant/          # LangGraph RAG agent
│   ├── xai/                # Grad-CAM + SHAP explanations
│   └── training/           # Kaggle/Colab training scripts
├── sdv/                    # Eclipse Kuksa VSS integration
├── infra/                  # Docker Compose + monitoring
└── notebooks/              # Development Jupyter notebooks
```

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts |
| **Backend** | FastAPI, SQLAlchemy 2.0 async, Celery, Redis |
| **Database** | PostgreSQL 16 + TimescaleDB (time-series) + ChromaDB (vector store) |
| **Computer Vision** | PyTorch, YOLOv8, DeepLabV3+, OpenCV, MediaPipe, Dlib |
| **LLM/RAG** | LangGraph, Ollama (local LLM), Sentence Transformers |
| **XAI** | pytorch-grad-cam, SHAP, Captum |
| **Vehicle SDV** | Eclipse Kuksa Databroker, VSS signals |
| **MLOps** | MLflow, Docker, GitHub Actions |

## 📋 The 10 Modules

| # | Module | Description |
|---|--------|-------------|
| **01** | Driver Monitoring | Real-time drowsiness (EAR), yawning (MAR), head pose, phone/smoking detection |
| **02** | Cabin Intelligence | Seat occupancy detection, child detection, unattended vehicle alerts |
| **03** | Road Understanding | Segmentation, YOLO/ByteTrack, MiDaS depth, HSV traffic lights, Caltech temporal pedestrian localization |
| **04** | Risk Prediction | Weighted risk scoring (0–100) with hard override rules |
| **05** | Driver Behavior | Weekly safety scoring, harsh braking/speeding tracking |
| **06** | Predictive Maintenance | Modules 3A–3I: datasets, engine/brake/battery/tire models, Kuksa I/O, pipeline, API, UI |
| **07** | AI Assistant | LangGraph agent with RAG + live Kuksa telemetry context |
| **08** | Safety Events | TTC calculation, incident detection, video clip logging |
| **09** | Fleet Dashboard | Multi-vehicle real-time monitoring with WebSocket updates |
| **10** | Explainable AI | Grad-CAM heatmaps + SHAP values + natural language explanations |

## 🎯 Development Roadmap

### Phase 0 — Setup & Database (Days 1–5) ✅ COMPLETE
- Docker environment (12 services)
- SQLAlchemy models + Alembic `001_initial_schema`
- FastAPI `/api/v1/*` router scaffold (REST + WebSocket + SSE)
- Auth (JWT register/login), Redis + Celery stubs
- Next.js landing + dashboard scaffold, CI workflow
- Docs under `docs/`

### Phase 1 — Driver Monitoring (Days 6–22) — NEXT
- EAR/MAR detection with Dlib
- Head pose estimation with MediaPipe
- YOLO training on DMD dataset (Kaggle)
- WebSocket streaming endpoint

### Phase 2 — Road Understanding (Days 15–28)
- DeepLabV3+ road segmentation on BDD100K
- YOLO road-object detection for box-based downstream modules
- YOLOv8n-LSTM temporal pedestrian localization (Caltech Pedestrian YOLO)
- ByteTrack object tracking
- Pretrained MiDaS relative depth (metric distance requires camera calibration)
- HSV red/amber/green traffic-light state classification
- Unified stateful frame pipeline with partial-failure handling (Module 2G)
- Real JPEG/PNG REST inference and binary-frame WebSocket streaming (Module 2H)
- Live road-camera/upload UI with overlays and pipeline diagnostics (Module 2I)

### Phase 3 — Predictive Maintenance (Days 22–35)
- Feature engineering: AI4I 2020 loaders + synthetic degradation generators (Module 3A)
- LSTM autoencoder engine-health anomaly scoring (Module 3B)
- XGBoost brake-wear pad-thickness regression (Module 3C)
- Battery SoH / months-to-replacement model (Module 3D)
- Tire wear % / km-to-replacement model (Module 3E)
- Kuksa VSS subscribe/store + mock sensor simulator (Module 3F)
- Unified maintenance pipeline with partial-failure handling and SHAP (Module 3G)
- REST + Celery batch predictions persisted to the DB (Module 3H)
- Maintenance UI: component health cards, alerts, feature contributions (Module 3I)

### Phase 4 — Risk Engine & Events (Days 28–40)
- Composite risk aggregation
- Safety event detection (TTC, drowsiness)
- MinIO video clip storage

### Phase 5 — AI Assistant (Days 35–50)
- LangGraph stateful agent
- RAG knowledge base (owner manual + OBD codes)
- Ollama local LLM integration

### Phase 6 — Dashboard & XAI (Days 45–62)
- Fleet real-time WebSocket updates
- Driver leaderboard
- Grad-CAM heatmaps
- SHAP explanations

### Phase 7 — Integration & Demo (Days 60–75)
- End-to-end testing
- Live demo mode with replayed video
- Deployment to Render + Vercel

## 🔧 Environment Setup

```bash
# Create .env from template
cp .env.example .env

# The defaults work for local Docker setup:
# - PostgreSQL: bmwai:bmwai_secret @ localhost:5432
# - Redis: localhost:6379
# - Ollama: http://localhost:11434
# - All other services on localhost
```

## 📦 Installing Backend Dependencies

```bash
cd apps/backend
pip install -r requirements.txt
```

## 📦 Installing Frontend Dependencies

```bash
cd apps/frontend
pnpm install
```

## 🧪 Running Tests

```bash
# Backend tests
cd apps/backend
pytest tests/ -v

# Frontend linting
cd apps/frontend
pnpm lint
```

## 🚀 Running the Project Locally (Without Docker)

### Terminal 1 — PostgreSQL + Redis (via Docker)
```bash
docker run -d \
  -e POSTGRES_USER=bmwai \
  -e POSTGRES_PASSWORD=bmwai_secret \
  -e POSTGRES_DB=bmwai_db \
  -p 5432:5432 \
  timescale/timescaledb:latest-pg16

docker run -d -p 6379:6379 redis:7-alpine
```

### Terminal 2 — FastAPI Backend
```bash
cd apps/backend
uvicorn app.main:app --reload --port 8000
```

### Terminal 3 — Next.js Frontend
```bash
cd apps/frontend
pnpm dev
```

### Terminal 4 — Ollama LLM
```bash
ollama serve
```

Then pull the 3B LLM:
```bash
ollama pull llama3.2:3b
```

## 📚 Training Models on Kaggle

All ML training happens on **Kaggle Free GPU** (P100/T4) to keep costs at $0.

1. Create Kaggle account + enable GPU
2. Upload datasets (DMD, BDD100K, Caltech Pedestrian YOLO)
3. Create notebooks from `notebooks/train_*.py` scripts
4. Download trained `.pt` weights to `ml/models/`

See [TRAINING.md](docs/TRAINING.md) for detailed instructions.

## 🌐 Deployment

**Production** (estimated **$7–15/month**):
- Frontend: Vercel (free)
- Backend: Render ($7/month)
- Database: Render Postgres (1GB free)
- Redis: Upstash (free tier)
- Storage: Cloudflare R2 (10GB free)

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for full cloud setup.

## 📖 Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Database Schema](docs/database.md)
- [Training Guide](docs/TRAINING.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## 🎓 Learning Resources

| Technology | Resource |
|-----------|----------|
| FastAPI | https://fastapi.tiangolo.com/tutorial/ |
| SQLAlchemy 2.0 | https://docs.sqlalchemy.org/20/orm/quickstart.html |
| YOLOv8 | https://github.com/ultralytics/ultralytics |
| LangGraph | https://python.langchain.com/docs/langgraph/ |
| Next.js 14 | https://nextjs.org/learn |
| Dlib | http://dlib.net/python/index.html |
| MediaPipe | https://mediapipe.dev/ |
| Eclipse Kuksa | https://github.com/eclipse-kuksa/kuksa-databroker |

## 📝 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes
3. Run tests: `pytest` + `pnpm lint`
4. Commit: `git commit -am 'Add feature'`
5. Push and open a PR

## 📄 License

© 2026 BMW AI Platform. Built for educational and portfolio purposes.

---

**Built to demonstrate production-grade automotive AI engineering aligned with BMW Group's strategic direction: Software-Defined Vehicle (SDV), ADAS, Predictive Analytics, and Responsible AI under EU AI Act compliance.**
