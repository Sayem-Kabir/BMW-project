# BMW AI Automotive Intelligence Platform
## Complete Build Guide — Datasets, Training Strategy, Frameworks & Phase-by-Phase Workflow

> **Target Audience:** Software engineers building a production-grade automotive AI portfolio for BMW.
> **Training Environment:** Kaggle Free Tier + Google Colab Free Tier (zero cost).
> **Goal:** A working, demo-ready full-stack platform covering SDV, ADAS, Predictive Maintenance, RAG, and XAI.

> 🆕 **Update note:** This revision adds Sections 14–19 covering authentication/RBAC, personalized role-based dashboards, production hardening, ML/AI governance, advanced industry-level features, and a dedicated performance/optimization pass (Phase 13). All new or changed content is tagged **🆕 NEW** or **✏️ UPDATED** so you can find it quickly. Original Phases 0–7 and Modules 01–10 are unchanged.

---

## Table of Contents

1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [Frameworks You Must Know](#2-frameworks-you-must-know)
3. [Server & Hardware Requirements](#3-server--hardware-requirements)
4. [Complete Tech Stack Reference](#4-complete-tech-stack-reference)
5. [Official Datasets — Updated](#5-official-datasets--updated)
6. [All 10 Modules — Detailed Breakdown](#6-all-10-modules--detailed-breakdown)
7. [Project Folder Structure](#7-project-folder-structure)
8. [Phase-by-Phase Workflow](#8-phase-by-phase-workflow)
9. [Training Strategy — Kaggle & Colab Optimized](#9-training-strategy--kaggle--colab-optimized)
10. [Database Schema](#10-database-schema)
11. [API Endpoints Reference](#11-api-endpoints-reference)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Reference Repositories](#13-reference-repositories)
14. 🆕 [Phase 8 — Authentication, RBAC & Multi-Tenancy](#14-phase-8--authentication-rbac--multi-tenancy-new)
15. 🆕 [Phase 9 — Personalized Role-Based Dashboards](#15-phase-9--personalized-role-based-dashboards-new)
16. 🆕 [Phase 10 — Production Hardening & Observability](#16-phase-10--production-hardening--observability-new)
17. 🆕 [Phase 11 — ML/AI Maturity & Governance](#17-phase-11--mlai-maturity--governance-new)
18. 🆕 [Phase 12 — Notifications & Product Polish](#18-phase-12--notifications--product-polish-new)
19. 🆕 [Advanced Industry-Level Features](#19-advanced-industry-level-features-new)
20. 🆕 [Phase 13 — Performance & Optimization Pass](#20-phase-13--performance--optimization-pass-new)

---

## 1. Project Overview & Architecture

This is a production-grade, full-stack AI automotive intelligence platform demonstrating capabilities that BMW's Software-Defined Vehicle and ADAS teams are building internally. Every technology choice maps directly to what modern automotive companies use in production.

### What Makes This BMW-Relevant

- Uses **Eclipse Kuksa Databroker** — the industry-standard VSS signal layer adopted by BMW, Bosch, and Mercedes-Benz
- Implements the same **ADAS detection pipeline** (driver monitoring + road scene understanding) used in BMW's driver assistance systems
- Demonstrates **Explainable AI (XAI)** — a regulatory requirement under EU AI Act for automotive applications
- Uses **LangGraph** for agentic AI workflows — the industry standard for production LLM systems
- Full-stack engineering from embedded-style VSS signal ingestion through to a React dashboard with real-time WebSocket streaming

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Input Layer                                 │
│  Camera Feed / Kuksa VSS Signals / OBD-II Port          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Computer Vision Workers                     │
│  YOLOv8 (detection) + MediaPipe (pose) + Dlib (landmarks)│
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Risk Aggregation Engine                     │
│  Weighted scoring → Redis pub-sub → Alert routing       │
└──────────────┬─────────────────────┬───────────────────┘
               │                     │
┌──────────────▼──────┐   ┌──────────▼──────────────────┐
│  FastAPI Backend    │   │  Celery Background Workers   │
│  REST + WebSocket   │   │  ML scoring, event logging   │
└──────────────┬──────┘   └──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│              Data Layer                                  │
│  PostgreSQL + TimescaleDB + ChromaDB + MinIO            │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│              React / Next.js Dashboard                   │
│  Real-time fleet monitoring, charts, AI chat            │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│              AI Intelligence Layer                       │
│  LangGraph + RAG (ChromaDB) + Ollama LLM               │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│              XAI Layer                                   │
│  Grad-CAM heatmaps + SHAP values + NL explanations     │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Frameworks You Must Know

This section covers every framework in the stack with what you need to learn, why it matters for BMW, and the best learning resources for each.

---

### 2.1 Backend — Python & FastAPI

**Why it matters for BMW:** FastAPI is the de facto standard for AI/ML service APIs in the automotive industry. BMW's internal ML microservices, inference endpoints, and vehicle data APIs are built on async Python frameworks.

**What you need to know:**

| Concept | What to Learn | Priority |
|---------|--------------|----------|
| Async/await in Python | `asyncio`, `async def`, `await` for non-blocking I/O | Critical |
| FastAPI routing | `APIRouter`, path/query/body parameters, dependency injection | Critical |
| Pydantic v2 models | Request validation, response schemas, `model_validator` | Critical |
| FastAPI WebSockets | `@router.websocket`, `accept()`, `send_json()`, `receive_bytes()` | High |
| Server-Sent Events (SSE) | `StreamingResponse` with `text/event-stream` for LLM streaming | High |
| FastAPI middleware | CORS, auth middleware, request logging | Medium |
| Background tasks | `BackgroundTasks`, when to use vs. Celery | Medium |

**Minimum learning path (3–5 days):**
1. Complete the official FastAPI tutorial at `fastapi.tiangolo.com/tutorial/` — do all chapters
2. Build a small async REST API with PostgreSQL using SQLAlchemy async
3. Add a WebSocket endpoint that streams data to a browser client

---

### 2.2 Task Queue — Celery + Redis

**Why it matters for BMW:** ML inference jobs (training, scoring batches of drivers) cannot block the web server. Celery is the standard Python task queue used in production AI systems.

**What you need to know:**

| Concept | What to Learn | Priority |
|---------|--------------|----------|
| Celery app setup | `Celery(app, broker=redis_url)`, `@shared_task` decorator | Critical |
| Task routing | Queues for different task types (ml_tasks, notifications) | High |
| Celery beat scheduler | Periodic tasks — running driver scoring every hour | High |
| Result backends | Storing task results in Redis for status polling | Medium |
| Flower monitoring | Web UI for monitoring task queue health | Medium |

**Redis pub-sub (separate from Celery):** You will use Redis as a real-time message bus. When the risk engine computes a new score, it publishes to a Redis channel. The FastAPI WebSocket handler subscribes and pushes to browser clients. Learn `redis-py` async and `pubsub.subscribe()`.

---

### 2.3 Database Layer — PostgreSQL, SQLAlchemy, TimescaleDB

**Why it matters for BMW:** Vehicle telemetry is time-series data. BMW's ADAS systems generate thousands of sensor readings per second. TimescaleDB handles time-series at scale while keeping a standard SQL interface.

**What you need to know:**

| Concept | What to Learn | Priority |
|---------|--------------|----------|
| SQLAlchemy 2.0 async ORM | `AsyncSession`, `select()`, `relationship()`, `mapped_column()` | Critical |
| Alembic migrations | `alembic revision --autogenerate`, `upgrade head` | Critical |
| TimescaleDB hypertables | `create_hypertable()`, time-based partitioning | High |
| PostgreSQL JSONB | Storing telemetry snapshots, SHAP values as JSON in SQL | High |
| Async database patterns | `async with session:`, avoiding N+1 queries | High |

**Key insight:** SQLAlchemy 2.0 changed significantly from 1.x. Make sure you learn the new 2.0 style with `select()` statements and `Mapped[]` type annotations, not the legacy `Query` API.

---

### 2.4 Computer Vision — PyTorch, YOLOv8, OpenCV, MediaPipe

**Why it matters for BMW:** This is the core of ADAS. Every driver monitoring, road scene understanding, and object detection feature runs through this stack.

**What you need to know:**

| Concept | What to Learn | Priority |
|---------|--------------|----------|
| PyTorch tensors | `torch.Tensor`, `.to(device)`, `.unsqueeze()`, `.squeeze()` | Critical |
| YOLOv8 inference | `YOLO("model.pt")`, `model(frame)`, reading results | Critical |
| YOLOv8 fine-tuning | `model.train(data=yaml, epochs=50)`, dataset YAML format | Critical |
| OpenCV basics | `cv2.VideoCapture`, `cv2.cvtColor`, drawing bounding boxes | Critical |
| MediaPipe Face Mesh | 468 facial landmarks, `FaceMesh`, landmark indexing | High |
| Dlib landmarks | 68-point predictor, EAR/MAR formula implementation | High |
| ONNX export | Exporting PyTorch models to ONNX for faster CPU inference | Medium |

**Training tip:** You do NOT need to understand PyTorch autograd in depth to use YOLOv8. The `ultralytics` library abstracts the training loop. Focus on understanding how to prepare datasets in YOLO format (YAML + label `.txt` files) and how to read inference results.

---

### 2.5 LLM Orchestration — LangChain, LangGraph, ChromaDB

**Why it matters for BMW:** BMW's conversational assistant in iDrive uses LLM agents with RAG. LangGraph is the modern standard for production agentic AI — it replaces the older LangChain "Agents" API.

**What you need to know:**

| Concept | What to Learn | Priority |
|---------|--------------|----------|
| LangGraph `StateGraph` | Defining nodes, edges, conditional routing | Critical |
| RAG pipeline | Embed → store in vector DB → retrieve on query → pass to LLM | Critical |
| ChromaDB | `from_documents()`, `similarity_search()`, `persist()` | Critical |
| Sentence Transformers | `HuggingFaceEmbeddings`, embedding model selection | High |
| LangChain document loaders | `PyMuPDFLoader`, `TextSplitter`, chunk size tuning | High |
| Streaming LLM responses | `llm.stream()`, `async for chunk in stream` | High |
| Ollama local LLM | Running `llama3.2:3b` locally for zero-cost inference | High |

**Key insight:** LangGraph thinks in terms of a **graph of stateful nodes**. Each node is a function that reads from and writes to a shared `State` dict. Edges define control flow. Study the LangGraph quickstart before implementing the AI assistant module.

---

### 2.6 XAI — Grad-CAM, SHAP, Captum

**Why it matters for BMW:** EU AI Act (effective 2026) requires automotive AI systems to provide explanations for safety-critical decisions. BMW engineers actively work on explainability for their ADAS systems.

**What you need to know:**

| Concept | What to Learn | Priority |
|---------|--------------|----------|
| Grad-CAM intuition | Class Activation Maps — which image regions drive a prediction | Critical |
| `pytorch-grad-cam` library | `EigenCAM`, target layers in YOLOv8 model, heatmap overlay | High |
| SHAP TreeExplainer | For XGBoost/tree models — which features drove the prediction | High |
| SHAP values interpretation | Positive = pushes toward class, negative = pushes away | High |
| Captum | Integrated Gradients for more accurate attribution than Grad-CAM | Medium |

---

### 2.7 SDV Layer — Eclipse Kuksa

**Why it matters for BMW:** Eclipse Kuksa is the open-source project that BMW, Bosch, and others use as the in-vehicle signal broker. It implements the COVESA Vehicle Signal Specification (VSS) — the standard schema for all vehicle data signals.

**What you need to know:**

| Concept | What to Learn | Priority |
|---------|--------------|----------|
| VSS signal paths | `Vehicle.Speed`, `Vehicle.OBD.RPM`, `Vehicle.Chassis.Axle...` | Critical |
| kuksa-client Python | `VSSClient`, `get_current_values()`, `subscribe_current_values()` | Critical |
| Kuksa Databroker | Running as Docker service, gRPC interface | High |
| Vehicle App pattern | Velocitas SDK, structured subscription/publish model | Medium |

**Learning path:** Run the Kuksa Databroker Docker container, connect with `kuksa-client` CLI, and practice reading/writing VSS signals. This hands-on experience is exactly what BMW interviews test for.

---

### 2.8 Frontend — React, Next.js 14, TypeScript, Tailwind

**Why it matters for BMW:** The fleet dashboard is the demo interface. BMW engineers will judge the platform's sophistication partly by the UI quality and real-time responsiveness.

**What you need to know:**

| Concept | What to Learn | Priority |
|---------|--------------|----------|
| Next.js 14 App Router | `app/` directory, `page.tsx`, `layout.tsx`, Server Components | Critical |
| React hooks | `useState`, `useEffect`, `useRef`, `useCallback` | Critical |
| WebSocket in React | `useEffect` + `useRef` for persistent WebSocket connections | Critical |
| Zustand state management | `create()`, `set()`, slices pattern for global state | High |
| React Query (TanStack) | `useQuery`, `useMutation`, automatic background refetch | High |
| Recharts | `LineChart`, `AreaChart`, `BarChart` with real-time data | High |
| TypeScript interfaces | Typing API responses, component props, store state | High |

---

### 2.9 MLOps — MLflow, Docker, Docker Compose

**Why it matters for BMW:** Automotive AI requires rigorous experiment tracking. BMW's ML teams use tools like MLflow to track every training run, compare models, and register production models.

**What you need to know:**

| Concept | What to Learn | Priority |
|---------|--------------|----------|
| MLflow tracking | `mlflow.start_run()`, `log_params()`, `log_metrics()`, `log_artifact()` | Critical |
| MLflow model registry | Registering models, staging, production promotion | High |
| Docker basics | `Dockerfile`, `COPY`, `RUN`, `CMD`, multi-stage builds | Critical |
| Docker Compose | `docker-compose.yml`, service dependencies, volumes, networking | Critical |
| Environment variables | `.env` files, never hardcoding secrets | Critical |

---

### 2.10 Server Frameworks Summary Table

| Layer | Framework | Learn In | Difficulty |
|-------|-----------|----------|------------|
| API server | FastAPI | 3–5 days | Medium |
| ORM | SQLAlchemy 2.0 async | 2–3 days | Medium |
| Task queue | Celery + Redis | 1–2 days | Easy |
| CV inference | Ultralytics YOLOv8 | 1–2 days | Easy |
| CV preprocessing | OpenCV 4 | 2–3 days | Medium |
| Face analysis | MediaPipe + Dlib | 1–2 days | Easy |
| Deep learning | PyTorch 2.x | 3–5 days | Hard |
| LLM agents | LangGraph 0.1 | 2–3 days | Medium |
| Vector store | ChromaDB | 1 day | Easy |
| Embeddings | Sentence Transformers | 1 day | Easy |
| Local LLM | Ollama | 0.5 days | Very Easy |
| XAI | pytorch-grad-cam + SHAP | 2 days | Medium |
| SDV signals | kuksa-client | 1 day | Easy |
| Frontend framework | Next.js 14 | 3–5 days | Medium |
| Styling | Tailwind CSS | 1–2 days | Easy |
| State management | Zustand | 0.5 days | Easy |
| Charts | Recharts | 1 day | Easy |
| MLOps | MLflow | 1 day | Easy |
| Containerization | Docker + Compose | 2–3 days | Medium |

**Total estimated ramp-up time (with existing dev experience):** 4–6 weeks of parallel learning while building.

---

## 3. Server & Hardware Requirements

### 3.1 Local Development Machine

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4-core Intel i5 / AMD Ryzen 5 | 8-core Intel i7/i9 or Ryzen 7/9 |
| RAM | 16 GB | 32 GB |
| Storage | 100 GB free SSD | 250 GB NVMe SSD |
| GPU | None (CPU inference ~8–12 FPS) | NVIDIA GTX 1060 6GB or better (30+ FPS) |
| OS | Ubuntu 22.04 LTS / macOS 13+ / Windows 11 + WSL2 | Ubuntu 22.04 LTS (native, best compatibility) |
| Python | 3.11+ | 3.11.x |
| Node.js | 18 LTS | 20 LTS |
| Docker | Desktop 4.x | Desktop 4.x with 8 GB memory allocation |

> **Note on GPU:** You do NOT need a local GPU. All model training happens on Kaggle/Colab (free GPU). Locally, you only run inference with small YOLOv8n models that work fine on CPU.

### 3.2 Docker Resource Allocation

In Docker Desktop settings, allocate:
- **CPU:** 4 cores minimum
- **Memory:** 8 GB minimum
- **Swap:** 2 GB
- **Disk image:** 60 GB

### 3.3 Free Cloud Training (Kaggle + Colab)

| Platform | GPU Available | VRAM | Session Limit | Best For |
|----------|--------------|------|---------------|---------|
| Kaggle Free | NVIDIA P100 / T4 | 16 GB | 30 hrs/week | YOLOv8 training, LSTM training |
| Google Colab Free | T4 (intermittent) | 15 GB | ~2–3 hrs/session | Quick experiments, debugging |
| Google Colab Pro | A100 (when available) | 40 GB | Better limits | Large model training (paid) |

**Strategy:** Use Kaggle as your primary training platform (more reliable GPU access). Use Colab for quick experiments and development debugging. Save trained model weights (`.pt` files) to Google Drive and pull them locally or to your server.

### 3.4 Local Docker Services — Port Map

| Service | Port | Purpose |
|---------|------|---------|
| FastAPI backend | 8000 | Main REST API + WebSocket |
| Next.js frontend | 3000 | Dashboard UI |
| PostgreSQL | 5432 | Primary relational database |
| Redis | 6379 | Cache + pub-sub message bus |
| ChromaDB | 8001 | Vector store for RAG |
| MinIO | 9000 / 9001 | Object storage + admin UI |
| MLflow | 5000 | Experiment tracking |
| Grafana | 3001 | Monitoring dashboard |
| Prometheus | 9090 | Metrics collection |
| Kuksa Databroker | 55555 | VSS signal broker |
| Ollama | 11434 | Local LLM inference server |

### 3.5 Cloud Deployment (Live Demo for BMW)

| Service | Provider | Spec | Monthly Cost |
|---------|----------|------|-------------|
| Backend API | Render | 2 vCPU, 4 GB RAM | ~$7/month |
| Frontend | Vercel | Free tier | $0 |
| PostgreSQL | Render Postgres | 1 GB | Free tier |
| Redis | Upstash | Free (10K cmd/day) | $0 |
| Object Storage | Cloudflare R2 | Free 10 GB | $0 |
| ChromaDB | Self-hosted on Render | Bundled | $0 extra |

**Total estimated demo deployment cost: ~$7–15/month**

---

## 4. Complete Tech Stack Reference

### 4.1 Frontend Layer

| Technology | Version | Role |
|-----------|---------|------|
| React | 18.x | Component-based UI |
| Next.js | 14.x | Full-stack framework, SSR, App Router |
| TypeScript | 5.x | Static typing across the entire frontend |
| Tailwind CSS | 3.x | Utility-first styling system |
| Recharts | 2.x | Time-series charts, telemetry graphs |
| D3.js | 7.x | Custom visualizations (risk heatmaps) |
| Zustand | 4.x | Lightweight global state management |
| TanStack Query | 5.x | Server state, caching, background refetch |
| Socket.io-client | 4.x | Real-time WebSocket for fleet updates |
| React Webcam | 7.x | Browser camera capture for live demo |

### 4.2 Backend Layer

| Technology | Version | Role |
|-----------|---------|------|
| Python | 3.11+ | Primary backend language |
| FastAPI | 0.111 | Async REST API + WebSocket server |
| Uvicorn | 0.30 | ASGI server (development) |
| Gunicorn | 22.0 | Production WSGI/ASGI process manager |
| SQLAlchemy | 2.0 | Async ORM for PostgreSQL |
| Alembic | 1.13 | Schema migrations |
| Pydantic v2 | 2.8 | Validation, settings management |
| Celery | 5.4 | Background task queue |
| Redis-py | 5.0 | Redis client (cache + pub-sub) |
| Structlog | 24 | Structured JSON logging |

### 4.3 Database Layer

| Database | Version | Role |
|---------|---------|------|
| PostgreSQL | 16 | Primary relational store (users, vehicles, events) |
| TimescaleDB | 2.x | Time-series extension — vehicle telemetry at scale |
| Redis | 7.x | In-memory cache + real-time pub-sub bus |
| ChromaDB | 0.5 | Vector embeddings for RAG assistant |
| MinIO | Latest | S3-compatible object store for videos, heatmaps |

### 4.4 AI & Computer Vision

| Library | Version | Role |
|---------|---------|------|
| PyTorch | 2.3 | Primary deep learning framework |
| Ultralytics YOLOv8 | 8.2 | Object detection backbone for all CV modules |
| OpenCV | 4.10 | Frame processing, image manipulation, video I/O |
| MediaPipe | 0.10 | Face mesh (468 landmarks), head pose estimation |
| Dlib | 19.24 | 68-point facial landmarks, EAR/MAR calculation |
| ONNX Runtime | 1.18 | Optimized CPU/GPU inference for deployment |

### 4.5 LLM / RAG Stack

| Library | Version | Role |
|---------|---------|------|
| LangChain | 0.2 | Document loaders, text splitters, retrieval chains |
| LangGraph | 0.1 | Stateful agentic workflows for the AI assistant |
| ChromaDB | 0.5 | Vector store with persistence |
| Sentence Transformers | 3.0 | Text embedding generation (all-MiniLM-L6-v2) |
| Ollama | 0.3 | Local LLM runtime (Llama 3.2 3B, Mistral 7B) |
| PyMuPDF | 1.24 | PDF parsing for BMW owner manuals |

### 4.6 XAI Stack

| Library | Version | Role |
|---------|---------|------|
| pytorch-grad-cam | 1.5 | Grad-CAM / EigenCAM heatmaps over YOLO models |
| Captum | 0.7 | Integrated Gradients, LayerGradCam attribution |
| SHAP | 0.45 | TreeExplainer for XGBoost maintenance models |

### 4.7 SDV / Connected Vehicle

| Library | Role |
|---------|------|
| Eclipse Kuksa Databroker | VSS signal broker (gRPC, industry standard for BMW/Bosch) |
| Eclipse Kuksa Canvas | HMI vehicle signal visualization |
| Eclipse Velocitas Python SDK | Structured Vehicle App subscription pattern |
| kuksa-client | Python gRPC client for VSS signal reads/writes |

### 4.8 MLOps

| Tool | Role |
|------|------|
| MLflow | Experiment tracking, model registry, artifact store |
| Optuna | Hyperparameter optimization for maintenance models |
| Docker + Compose | Full-stack containerization |
| GitHub Actions | CI/CD — lint, test, build, deploy on merge |
| Prometheus | Metrics scraping from FastAPI |
| Grafana | Monitoring dashboards |

---

## 5. Official Datasets — Updated

All datasets below are free to access and optimized for Kaggle/Colab training workflows.

---

### 5.1 Driver Monitoring & Drowsiness Detection

#### DMD — Driver Monitoring Dataset
- **URL:** https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset
- **What it contains:** 41 hours of annotated in-cabin video across 37 drivers. Covers drowsiness, distraction, mobile phone usage, eating, smoking, and seatbelt detection. Recorded with RGB, depth, and IR cameras.
- **Why it's better than YawDD:** Multi-sensor, more diverse drivers, richer annotation schema, directly used in automotive research.
- **Size:** ~50 GB total (request via the GitHub page — academic use is free)
- **For training:** Use the RGB subset. Annotations include bounding boxes for phone, smoke, and activity labels. Convert to YOLO format using the provided scripts.
- **Kaggle training:** Upload the RGB subset (~8 GB) to a Kaggle dataset and train YOLOv8n for phone/seatbelt/smoking detection. Achieves ~30 hrs training time on P100.

#### Alternative — Kaggle Drowsiness Detection Datasets (no request needed)
- **URL:** Search Kaggle for "driver drowsiness detection" — several pre-cleaned datasets with EAR-labeled eye images
- **What to use:** For EAR-based detection you do NOT need to train a model — it's a geometric formula on Dlib landmarks. Use the Kaggle datasets to validate your EAR threshold settings.

---

### 5.2 Cabin Intelligence — Seat Occupancy & Passenger Detection

#### TICaM — Time-of-Flight In-Car Cabin Monitoring Dataset
- **URL:** https://hyper.ai/datasets/21108
- **What it contains:** Time-of-flight depth images of vehicle interiors with occupancy annotations per seat zone. 31 subjects, multiple vehicle types.
- **Why it matters:** Directly targets the cabin monitoring use case — seat occupancy, child detection, and passenger counting.
- **Size:** ~2 GB compressed
- **For training:** Train a custom YOLOv8n classification head on seat ROI crops. Binary classification per zone: occupied / empty.
- **Kaggle training:** Import as Kaggle dataset, train for 50 epochs. Expected mAP50: ~0.85+ on seat occupancy.

---

### 5.3 Road Scene Understanding

#### BDD100K — Berkeley DeepDrive
- **URL:** https://bdd-data.berkeley.edu/
- **Toolkit:** https://github.com/bdd100k/bdd100k
- **What it contains:** 100,000 diverse driving videos with full annotations — bounding boxes, drivable areas, lane markings, instance segmentation. Covers 11 object categories relevant to road scenes.
- **Why it's BMW-relevant:** The most widely cited autonomous driving dataset. Used in virtually every ADAS benchmark. Covers weather, time-of-day, and geographic diversity.
- **Size:** ~6 GB (images only, compressed) — full video is 1.8 TB (use images only)
- **For training on Kaggle:** Use the 100K images subset. Available as a Kaggle dataset directly (search "BDD100K"). Train YOLOv8m for road object detection.
- **Expected training time:** ~8–12 hours on Kaggle P100 for 50 epochs at 640px.
- **Expected mAP50:** ~0.55–0.65 (BDD100K is intentionally challenging)

#### Caltech Pedestrian YOLO Dataset
- **URL:** https://www.kaggle.com/datasets/abhinavsasikumar/caltech-pedestrian-yolo/data
- **What it contains:** Consecutive urban-driving frames with YOLO-format pedestrian bounding boxes derived from the Caltech Pedestrian benchmark.
- **Why it matters:** It supports temporal pedestrian localization, confidence smoothing, and recovery through short detector dropouts.
- **Task boundary:** The annotations contain pedestrian boxes, not crossing-intent labels. Module 2F must not emit crossing/not-crossing claims.
- **For training:** Feed five consecutive 224px frames through a YOLOv8n feature backbone and LSTM; regress the primary pedestrian's normalized box and confidence.
- **Export:** `best_pedestrian_yololstm.pt`

---

### 5.4 Predictive Maintenance

#### AI4I 2020 Predictive Maintenance Dataset
- **URL:** https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset
- **What it contains:** Synthetic dataset of 10,000 data points with 5 machine features (air temperature, process temperature, rotational speed, torque, tool wear) and 6 failure modes. A direct analog to vehicle sensor data with labeled failures.
- **Why it's better than generating from scratch:** Real failure distribution with realistic sensor correlations. Industry-standard benchmark for predictive maintenance ML.
- **Size:** ~500 KB — no GPU needed, no upload needed, downloads in seconds
- **For training:** Available directly from UCI via `pip install ucimlrepo`. Train XGBoost for failure classification and LightGBM for remaining useful life regression.
- **Training environment:** Train locally or on Colab CPU — this dataset is tiny. Focus on feature engineering and SHAP explanations.

```python
# Direct import — no file download needed
from ucimlrepo import fetch_ucirepo
ai4i = fetch_ucirepo(id=601)
X = ai4i.data.features
y = ai4i.data.targets
```

---

### 5.5 AI Vehicle Assistant — Conversational Training

#### OpenAssistant Conversations — OASST1
- **URL:** https://huggingface.co/datasets/OpenAssistant/oasst1
- **What it contains:** 161,000 human-generated assistant-style conversations across 35 languages. High-quality instruction-following data used to fine-tune assistant LLMs.
- **Why it matters:** Used to fine-tune Llama 3.2 or Mistral specifically for automotive Q&A style responses. The base Ollama model already handles general conversation — you use OASST1 to fine-tune a vehicle-domain style.
- **Important note:** Full fine-tuning on Colab is too expensive. Use this dataset for **LoRA fine-tuning** with the PEFT library — a 3B model with LoRA trains in ~2 hours on Colab T4.
- **Realistic approach for portfolio:** Skip fine-tuning for now. Use the base Llama 3.2 3B through Ollama with a well-crafted system prompt. Fine-tuning is a "Phase 2" enhancement.

---

### 5.6 Additional Supporting Datasets

| Dataset | URL | Use | Size |
|---------|-----|-----|------|
| CEW (Closed Eyes in the Wild) | Kaggle: search "closed eyes detection" | EAR threshold validation | ~200 MB |
| OBD-II Codes Database | GitHub: myvin/obd2codes | RAG knowledge base for diagnostic codes | 5 MB |
| CARLA Simulator Recordings | carla.org | Synthetic data augmentation for road scenes | On demand |
| nuScenes (mini) | nuscenes.org | 3D object detection reference | 4 GB mini |

---

### 5.7 Dataset Download & Management Strategy

#### For Kaggle Training:
1. Upload datasets to **Kaggle Datasets** (your own private datasets) for persistence
2. In your training notebooks, reference datasets via the `+Add Data` button — datasets mount instantly without re-uploading
3. Save trained models to `/kaggle/working/` and download the `.pt` file, or push directly to Google Drive via the `drive` API

#### For Colab Training:
1. Mount Google Drive at the start of every notebook: `drive.mount('/content/drive')`
2. Keep all datasets in `MyDrive/bmw_datasets/`
3. Save model checkpoints to Drive every 10 epochs to survive session disconnects
4. Use `gdown` for downloading from Google Drive in notebooks

```python
# Standard Colab notebook header
from google.colab import drive
drive.mount('/content/drive')

import os
DRIVE_PATH = '/content/drive/MyDrive/bmw_datasets'
MODEL_SAVE_PATH = '/content/drive/MyDrive/bmw_models'
os.makedirs(MODEL_SAVE_PATH, exist_ok=True)
```

---

## 6. All 10 Modules — Detailed Breakdown

### Module 01 — Driver Monitoring System

**Objective:** Detect dangerous driver behaviors in real time using the vehicle cabin camera.

**Detection capabilities:**

| Behavior | Detection Method | Model | Threshold |
|----------|-----------------|-------|-----------|
| Drowsiness | Eye Aspect Ratio (EAR) via Dlib | Geometric formula | EAR < 0.25 for 30+ consecutive frames |
| Yawning | Mouth Aspect Ratio (MAR) via Dlib | Geometric formula | MAR > 0.60 |
| Head distraction | Head pose via MediaPipe | solvePnP | Pitch/yaw deviation > 15° |
| Phone usage | Object detection | YOLOv8n (DMD fine-tuned) | Confidence > 0.70 |
| Smoking | Object detection | YOLOv8n (DMD fine-tuned) | Confidence > 0.65 |
| Seatbelt absence | Classification | YOLOv8n (DMD fine-tuned) | Confidence > 0.80 |

**EAR formula:**
```
Left eye landmarks (Dlib): points 36–41
Right eye landmarks: points 42–47

EAR = (|p2-p6| + |p3-p5|) / (2 × |p1-p4|)

Where p1..p6 are the 6 eye landmark points.
Average left and right EAR for the final score.
```

**Output schema:**
```json
{
  "alertness_score": 84,
  "risk_level": "MEDIUM",
  "ear_value": 0.21,
  "mar_value": 0.42,
  "yawn_count": 3,
  "head_pose": { "pitch": -8.2, "yaw": 18.5, "roll": 2.1 },
  "phone_detected": true,
  "seatbelt_worn": true,
  "consecutive_drowsy_frames": 18,
  "xai_heatmap_url": "/api/v1/xai/heatmap/session_abc123_frame_42.png"
}
```

**Training dataset:** DMD Dataset (RGB subset). Fine-tune YOLOv8n for phone/seatbelt/smoking. EAR/MAR detection requires no training.

---

### Module 02 — Cabin Intelligence System

**Objective:** Understand seat occupancy and detect unsafe cabin configurations.

**Detection capabilities:**
- Seat occupancy per zone (driver, front passenger, rear left, rear right, rear center)
- Child detection via bounding box size heuristic (height ratio < 0.5 relative to seat zone)
- Unattended vehicle alert (occupants detected, no motion from driver seat for > 5 minutes)
- Object left in vehicle (bag, package detected on seat without occupant)

**Algorithm:** YOLOv8n with custom Region of Interest (ROI) zones defined per camera mount position. Person bounding boxes are filtered by zone membership and size classification.

**Training dataset:** TICaM dataset for seat zone occupancy classification. Standard COCO pretrained YOLOv8n covers person detection out of the box.

**Output schema:**
```json
{
  "total_occupants": 4,
  "driver_present": true,
  "front_passenger": true,
  "rear_passengers": 2,
  "child_detected": false,
  "child_alert": false,
  "unattended_vehicle": false,
  "occupant_map": {
    "driver": true, "front_right": true,
    "rear_left": true, "rear_right": true, "rear_center": false
  }
}
```

---

### Module 03 — Road Understanding System

**Objective:** Detect, classify, track, and estimate distance to all objects in the driving environment.

**Detection categories:**

| Category | Objects | Model |
|----------|---------|-------|
| Vehicles | Car, truck, bus, motorcycle, bicycle | YOLOv8m (BDD100K) |
| Vulnerable users | Pedestrian, cyclist | YOLOv8m + Caltech YOLO-LSTM temporal localizer |
| Infrastructure | Traffic light (+ state), stop sign, crosswalk | YOLOv8m |
| Hazards | Road debris, obstacles | YOLOv8m (BDD100K custom class) |

**Pipeline stages:**
1. **Detection:** YOLOv8m inference on each frame → bounding boxes + class labels + confidence scores
2. **Tracking:** ByteTrack (via `supervision` library) → persistent track IDs across frames
3. **Depth estimation:** Pretrained MiDaS (Intel ISL) → relative inverse-depth map; populate meters only after fitting scale/offset with known-distance samples for the target camera
4. **Traffic light classification:** Crop tracked traffic-light bounding box → HSV color masks + confidence/dominance gates → red/amber/green/unknown state
5. **Temporal pedestrian localization:** Caltech-trained YOLOv8n-LSTM over five frames → primary pedestrian box + confidence; associate it with ByteTrack for temporal confirmation
6. **Unified orchestration (2G):** One stateful pipeline per camera stream runs stages 2B–2F in dependency order, preserves successful partial results, and reports per-stage timing/warnings
7. **Live road UI (2I):** Next.js `/road` supports environment-camera WebSocket streaming and JPEG/PNG uploads with projected boxes, object/depth/light details, stage timings, and warnings

**Training datasets:** BDD100K for optional YOLOv8m fine-tuning and Caltech Pedestrian YOLO for the temporal pedestrian localizer.

**Output schema:**
```json
{
  "objects": [
    {"id": "track_12", "class": "car", "confidence": 0.94, "bbox": [120, 200, 380, 420], "distance_m": 8.3},
    {"id": "track_7", "class": "pedestrian", "confidence": 0.89, "distance_m": 15.1, "temporally_confirmed": true, "temporal_confidence": 0.91},
    {"id": "track_3", "class": "traffic_light", "state": "GREEN", "distance_m": 45.0}
  ],
  "frame_id": 1847,
  "timestamp": "2024-11-14T14:35:21.443Z"
}
```

---

### Module 04 — Risk Prediction Engine

**Objective:** Aggregate all sensor and vision inputs into a composite, explainable real-time risk score.

**Scoring weights:**

| Risk Factor | Weight | Trigger Condition |
|-------------|--------|------------------|
| Driver drowsiness | 0.35 | EAR < 0.25 for 30+ consecutive frames |
| Phone usage | 0.25 | YOLO confidence > 0.70 |
| No seatbelt | 0.15 | Seatbelt class not detected |
| Pedestrian proximity | 0.15 | Pedestrian within 10m |
| Aggressive vehicle nearby | 0.10 | Estimated relative speed > threshold |

**Risk levels:**

| Level | Score Range | Action |
|-------|-------------|--------|
| LOW | 0–40 | Normal operation, log telemetry |
| MEDIUM | 41–65 | UI amber warning, increase logging frequency |
| HIGH | 66–85 | Audio alert, push notification to fleet manager |
| CRITICAL | 86–100 | Emergency alert, save video clip, log event |

**Hard override rules (YAML config):**
```yaml
risk_overrides:
  - condition: "drowsy AND pedestrian_distance_m < 10"
    result: CRITICAL
    reason: "Drowsy driver with pedestrian in immediate path"
  - condition: "no_seatbelt AND speed_kmh > 60"
    result: HIGH
    reason: "Unbelted at highway speed"
  - condition: "phone_detected AND school_zone"
    result: CRITICAL
    reason: "Phone usage in school zone"
```

**Real-time distribution:** Redis `PUBLISH risk:{vehicle_id} {json_payload}` — fleet WebSocket subscribers receive score updates within 100ms.

---

### Module 05 — Driver Behavior Analytics

**Objective:** Build a persistent long-term driving profile per driver for insurance scoring, fleet management, and coaching.

**Behavior metrics:**

| Metric | Calculation Method | Source Signal |
|--------|--------------------|--------------|
| Harsh braking | Δspeed < -8 km/h per second | Kuksa `Vehicle.Acceleration.Longitudinal` |
| Rapid acceleration | Δspeed > 8 km/h per second | Same |
| Aggressive steering | Steering angle rate > 45°/s | Kuksa `Vehicle.Chassis.SteeringWheel.Angle` |
| Speeding | Speed > posted limit (GPS + map data) | Kuksa `Vehicle.Speed` |
| Fatigue events | Drowsiness detected > 3 times per session | Module 01 output |
| Phone events | Module 01 phone detection | Module 01 output |

**Safety score formula (rolling 7-day window):**
```
base_score = 100

penalties:
  harsh_braking    → -3 per event
  speeding         → -4 per event
  drowsiness       → -8 per event
  phone_usage      → -6 per event
  no_seatbelt      → -5 per event

safety_score = max(0, min(100, base_score + sum(penalties)))
```

**Weekly report JSON:**
```json
{
  "driver_id": "drv_001",
  "week": "2024-W46",
  "safety_score": 88,
  "trend": "+4 vs last week",
  "risk_tier": "LOW",
  "events": {
    "harsh_braking": 5,
    "speeding": 2,
    "drowsiness": 1,
    "phone_usage": 0,
    "no_seatbelt": 0
  },
  "recommendations": [
    "Maintain 3-second following distance — your braking events cluster in morning rush hour",
    "Reduce speed by 5-10 km/h on highway segments"
  ]
}
```

---

### Module 06 — Predictive Maintenance System

**Objective:** Predict component failures before they happen using VSS telemetry signals and ML models.

**ML models per component:**

| Component | Algorithm | Input Features | Output | Training Data |
|-----------|-----------|---------------|--------|--------------|
| Engine health | Classifier (+ optional LSTM AE) | NEV voltage/current/RPM/temp/vibration | Fault class / anomaly 0–1 | `NEV_fault_dataset.csv` |
| Brake condition | XGBoost Classifier | Usage, load, temperatures, vibration, diagnostics | Good / Fair / Poor | Logistics maintenance CSV |
| Battery (EV) | XGBoost | Cycle, voltage, current, temperature, discharge time | SOH % | `EV_Battery_Dataset_1.csv` |
| Tires | XGBoost Regressor | Tire pressure, vibration, load, usage, service age, road/weather codes | TPI-derived wear proxy % | `logistics_predictive_maintenanceV2.csv` |

**Pipeline stages (Phase 3 submodules):**
1. **Feature engineering and datasets (3A):** Local loaders for EVIoT, battery cycle SoH, NEV fault, and logistics tire CSVs under `data/predictive_maintenance/`; feature transforms; train-ready frames for 3B–3E notebooks
2. **Engine health (3B):** NEV fault classifier (+ optional LSTM autoencoder on motor telemetry); warn / critical on anomaly or fault probability
3. **Brake condition (3C):** XGBoost classifier on logistics telemetry → `Good`, `Fair`, or `Poor`; maps to normal / warning / critical
4. **Battery (EV) (3D):** Leakage-safe XGBoost on cycle-level `SOH_pct`; chronological evaluation; warn < 80%, critical < 65%
5. **Tire wear (3E):** XGBoost regression of logistics-derived `Tire_Wear_pct` (from `TPI`) using the dataset's predefined Train / Validation / Test partitions; raw `TPI` and downstream maintenance indexes are excluded; warn ≥ 70%, critical ≥ 90%. This is a wear-risk proxy, not measured tread depth.
6. **Kuksa VSS I/O (3F):** Databroker subscribe/store plus mock sensor simulator for demos without hardware
7. **Unified maintenance pipeline (3G):** Nested component inputs or one enriched feature map → independent 3B–3E inference with partial-failure handling, alert thresholds, and the top three native XGBoost SHAP contributions in the same response. Raw 3F VSS lacks several dataset-specific fields, so unavailable components report their missing feature contract rather than receiving fabricated values.
8. **Backend API and jobs (3H):** REST endpoints + Celery batch predictions persisted to `maintenance_predictions`
9. **Maintenance UI (3I):** Next.js component health cards, alerts, and SHAP/feature contribution views

**Training note:** Modules 3B–3E train locally in notebooks (CPU is enough). Module 3A only prepares features/frames — it does not train models.

**Scope rules:** 3B–3E train/infer independently; 3F may run in parallel via the mock simulator; 3G tolerates partial model failures (same spirit as Module 2G); 3H wires 3G; 3I wires 3H. Training is CPU-friendly — no GPU detector requirement.

**Alert thresholds:**

| Component | Metric | Warning | Critical |
|-----------|--------|---------|---------|
| Engine | Fault / anomaly score | > 0.60 | > 0.80 |
| Brakes | Condition class | Fair | Poor |
| Battery | Health percentage | < 80% | < 65% |
| Tires | Wear percentage | > 70% | > 90% |

**VSS signals consumed:**
```
Vehicle.Speed
Vehicle.OBD.RPM
Vehicle.OBD.OilTemp
Vehicle.OBD.CoolantTemp
Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure
Vehicle.Chassis.Axle.Row1.Wheel.Right.Tire.Pressure
Vehicle.Chassis.Axle.Row2.Wheel.Left.Tire.Pressure
Vehicle.Chassis.Axle.Row2.Wheel.Right.Tire.Pressure
Vehicle.Powertrain.TractionBattery.StateOfCharge.Current
Vehicle.Powertrain.TractionBattery.StateOfHealth
Vehicle.Powertrain.Transmission.TravelledDistance
```

---

### Module 07 — AI Vehicle Assistant

**Objective:** Provide a context-aware, RAG-grounded conversational assistant with live vehicle telemetry awareness.

**Knowledge base sources:**
- BMW owner manual PDF (vehicle-specific, user-uploaded)
- OBD-II diagnostic trouble code database (GitHub: myvin/obd2codes)
- Service interval specifications (oil, filters, brakes, tires, spark plugs)
- Vehicle's own maintenance history from PostgreSQL (personalized context)
- Live Kuksa telemetry snapshot injected at query time

**LangGraph agent architecture:**

```
User Query
    ↓
[Node: classify_intent]
    │
    ├── "vehicle warning light" → [Node: rag_retriever] → ChromaDB similarity search
    │                                  ↓
    │                             [Node: telemetry_injector] → Fetch live Kuksa signals
    │
    ├── "maintenance question" → [Node: db_lookup] → PostgreSQL maintenance history
    │
    ├── "OBD diagnostic code" → [Node: obd_lookup] → OBD-II code database
    │
    └── "general car question" → [Node: direct_llm] → LLM with vehicle context
              ↓ (all paths merge)
    [Node: response_generator] → LLM with all context → streaming SSE output
```

**Example interaction with live telemetry:**
```
User: "Why is my tire pressure warning on?"

System action: Fetches live Kuksa signals
Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure  → 32 PSI
Vehicle.Chassis.Axle.Row1.Wheel.Right.Tire.Pressure → 34 PSI
Vehicle.Chassis.Axle.Row2.Wheel.Left.Tire.Pressure  → 22 PSI  ← LOW
Vehicle.Chassis.Axle.Row2.Wheel.Right.Tire.Pressure → 33 PSI

RAG retrieves: BMW owner manual chunk on TPMS warnings

AI response:
"Your rear-left tire (Tire 3) is reading 22 PSI, which is 10 PSI below
the recommended 32–35 PSI range for your vehicle. This is what triggered
the TPMS warning light. I recommend inflating it to 33 PSI at your next
fuel stop. Driving on an under-inflated tire increases fuel consumption by
up to 3%, reduces handling response, and accelerates uneven tread wear.
Would you like me to log a service reminder and find the nearest tire
center?"
```

---

### Module 08 — Safety Event Detection System

**Objective:** Automatically detect, classify, and log critical driving incidents with video evidence.

**Event types and detection methods:**

| Event Type | Detection Method | Threshold | Severity |
|-----------|-----------------|-----------|---------|
| Near collision | TTC = distance / relative_speed | TTC < 2.0 seconds | CRITICAL |
| Driver asleep | Consecutive drowsy frames | > 60 frames (2 seconds) | CRITICAL |
| Lane departure | Optical flow + Hough lane detection | > 0.5m lateral deviation | HIGH |
| Unsafe following distance | TTC at highway speed | TTC < 4.0s at speed > 60 km/h | HIGH |
| Sudden hard braking | Longitudinal deceleration | Δspeed < -12 km/h/s | MEDIUM |
| Prolonged phone usage | YOLOv8 detection duration | > 5 consecutive seconds | HIGH |
| Pedestrian proximity hazard | Confirmed pedestrian track + depth/TTC | Distance < 15m with closing motion | HIGH |

**Event record schema:**
```json
{
  "event_id": "evt_20241114_bmwx5_001",
  "vehicle_id": "bmw_x5_vin_123",
  "driver_id": "drv_001",
  "event_type": "NEAR_COLLISION",
  "severity": "CRITICAL",
  "timestamp": "2024-11-14T14:35:21.443Z",
  "latitude": 48.1351,
  "longitude": 11.5820,
  "telemetry_snapshot": {
    "speed_kmh": 58,
    "ttc_seconds": 1.7,
    "object_class": "car",
    "object_distance_m": 9.8,
    "driver_ear": 0.22,
    "risk_score_at_event": 94
  },
  "video_clip_url": "minio://safety-events/evt_20241114_001.mp4",
  "acknowledged": false,
  "xai_explanation": "Near collision detected because TTC dropped to 1.7s (threshold: 2.0s). Driver EAR of 0.22 indicates borderline drowsiness."
}
```

---

### Module 09 — Fleet Management Dashboard

**Objective:** Provide real-time multi-vehicle monitoring for fleet operators.

**Dashboard pages:**

**1. Fleet Overview**
- Vehicle grid (status cards: operational / maintenance required / critical alert)
- Real-time active alerts counter with severity badges
- Fleet-wide risk score distribution histogram
- Live map of vehicle locations (Leaflet.js + GPS coordinates from Kuksa)

**2. Vehicle Detail**
- Real-time telemetry time-series charts (speed, RPM, tire pressure, battery SoC)
- Driver monitoring live feed overlay
- Current session events timeline
- Maintenance prediction status per component
- Embedded AI assistant chat for this vehicle

**3. Driver Leaderboard**
- Safety score ranking table with 7-day trend sparklines
- Color-coded risk tier badges (green/amber/red)
- Click-through to full driver profile

**4. Analytics**
- Fleet-wide incident trends (line chart by week)
- Maintenance cost projection (bar chart by component)
- Driver performance distribution (histogram)
- Alert volume by vehicle, driver, time-of-day

**5. Alerts Center**
- All active unacknowledged alerts sorted by severity
- One-click acknowledge with timestamp
- Link to associated video clip
- XAI explanation preview

**Real-time WebSocket update frequency:**
```
ws://api/v1/fleet/ws/{org_id}

Server pushes every 5 seconds:
  - Risk score changes for all vehicles
  - New safety events
  - New maintenance alerts
  - Vehicle online/offline status changes
```

---

### Module 10 — Explainable AI (XAI)

**Objective:** Make every AI decision transparent and understandable — a regulatory requirement under EU AI Act and a BMW trust requirement for safety-critical systems.

**XAI coverage per module:**

| Module | XAI Method | Visual Output | Text Output |
|--------|-----------|--------------|------------|
| Drowsiness detection | Grad-CAM (EigenCAM) on YOLOv8 | Heatmap overlaid on eye region | "Eyes closed region activated detector" |
| Road hazard detection | Grad-CAM on YOLOv8m | Heatmap on hazard pixels | "Debris in lane center activated" |
| Predictive maintenance | SHAP TreeExplainer | SHAP waterfall plot | Top 3 feature contributions |
| Risk engine | Rule trace JSON | N/A | Which rules triggered and their weights |
| AI assistant | Source citation | N/A | "Source: BMW Manual, p.142, TPMS section" |

**Natural language explanation pipeline:**
```python
def generate_nl_explanation(event_type, shap_values, gradcam_description, vehicle_state):
    """
    1. Get Grad-CAM heatmap → identify activated image region
    2. Get SHAP values → rank top 3 contributing sensor features
    3. Compose structured prompt → call LLM
    4. Return plain-English explanation for driver or fleet manager
    """
    prompt = f"""
You are a vehicle safety AI assistant. A {event_type} was detected.

Sensor evidence: {shap_values[:3]}
Visual evidence: {gradcam_description}
Vehicle state: speed={vehicle_state['speed_kmh']} km/h, time={vehicle_state['timestamp']}

Write a 2-3 sentence plain English explanation of:
1. What was detected
2. The key evidence that triggered it
3. What the driver should do

Do not use technical jargon. Be direct and actionable.
"""
    return llm.invoke(prompt)
```

**Example XAI output:**
```
Drowsiness alert triggered:
• Eyes were partially closed for 2.7 consecutive seconds (measured EAR: 0.18, safe threshold: 0.25)
• 4 yawns detected in the past 3 minutes
• Head tilted 22° downward — above the 15° attention threshold

Grad-CAM heatmap: High activation concentrated on left and right eye regions (87% of activation mass)
Confidence: 91%

Action: Please pull over safely and rest for at least 20 minutes.
```

---

## 7. Project Folder Structure

```
bmw-ai-platform/
│
├── apps/
│   ├── frontend/                          # Next.js 14 React dashboard
│   │   ├── src/
│   │   │   ├── app/                       # Next.js App Router
│   │   │   │   ├── layout.tsx             # Root layout, fonts, providers
│   │   │   │   ├── page.tsx               # Landing / login page
│   │   │   │   ├── dashboard/
│   │   │   │   │   └── page.tsx           # Fleet overview dashboard
│   │   │   │   ├── vehicle/[id]/
│   │   │   │   │   └── page.tsx           # Individual vehicle detail
│   │   │   │   ├── driver/[id]/
│   │   │   │   │   └── page.tsx           # Driver profile & analytics
│   │   │   │   ├── assistant/
│   │   │   │   │   └── page.tsx           # AI vehicle assistant chat
│   │   │   │   └── alerts/
│   │   │   │       └── page.tsx           # Safety alerts center
│   │   │   ├── components/
│   │   │   │   ├── monitoring/
│   │   │   │   │   ├── DriverMonitor.tsx  # Webcam + WebSocket + overlay
│   │   │   │   │   ├── RiskGauge.tsx      # Animated risk score gauge
│   │   │   │   │   └── AlertBanner.tsx    # Real-time alert notification
│   │   │   │   ├── charts/
│   │   │   │   │   ├── TelemetryChart.tsx # Recharts time-series wrapper
│   │   │   │   │   ├── SafetyScoreChart.tsx
│   │   │   │   │   └── MaintenanceBar.tsx
│   │   │   │   ├── fleet/
│   │   │   │   │   ├── VehicleGrid.tsx    # Status card grid
│   │   │   │   │   ├── FleetMap.tsx       # Leaflet vehicle location map
│   │   │   │   │   └── DriverLeaderboard.tsx
│   │   │   │   └── ui/
│   │   │   │       ├── Button.tsx
│   │   │   │       ├── Badge.tsx          # Risk tier color badges
│   │   │   │       └── Card.tsx
│   │   │   ├── lib/
│   │   │   │   ├── api.ts                 # Axios API client with interceptors
│   │   │   │   ├── socket.ts              # Socket.io client singleton
│   │   │   │   ├── store.ts               # Zustand store definitions
│   │   │   │   └── types.ts               # Shared TypeScript interfaces
│   │   │   └── hooks/
│   │   │       ├── useFleetWebSocket.ts   # Fleet real-time hook
│   │   │       └── useDriverStream.ts     # Driver monitoring stream hook
│   │   ├── public/
│   │   ├── package.json
│   │   ├── tailwind.config.ts
│   │   └── tsconfig.json
│   │
│   └── backend/                           # FastAPI Python API
│       ├── app/
│       │   ├── main.py                    # App factory, lifespan, routers
│       │   ├── core/
│       │   │   ├── config.py              # Pydantic Settings from .env
│       │   │   ├── security.py            # JWT creation/verification
│       │   │   ├── database.py            # Async SQLAlchemy engine + session
│       │   │   └── redis.py               # Redis connection pool
│       │   ├── api/
│       │   │   └── v1/
│       │   │       ├── auth.py            # Login, register, JWT endpoints
│       │   │       ├── driver.py          # Driver monitoring REST + WebSocket
│       │   │       ├── road.py            # Road understanding endpoints
│       │   │       ├── risk.py            # Risk score endpoints
│       │   │       ├── maintenance.py     # Maintenance predictions REST (3H)
│       │   │       ├── assistant.py       # AI chat with SSE streaming
│       │   │       ├── fleet.py           # Fleet management endpoints
│       │   │       ├── events.py          # Safety event CRUD
│       │   │       ├── analytics.py       # Driver behavior analytics
│       │   │       ├── xai.py             # XAI explanation endpoints
│       │   │       └── ws.py              # Fleet WebSocket handlers
│       │   ├── models/                    # SQLAlchemy ORM models
│       │   │   ├── vehicle.py
│       │   │   ├── driver.py
│       │   │   ├── session.py
│       │   │   ├── event.py
│       │   │   └── maintenance.py        # maintenance_predictions ORM (3H)
│       │   ├── schemas/                   # Pydantic request/response schemas
│       │   │   ├── driver.py
│       │   │   ├── risk.py
│       │   │   ├── event.py
│       │   │   └── maintenance.py        # Maintenance API schemas (3H)
│       │   ├── services/                  # Business logic layer
│       │   │   ├── driver_service.py      # Orchestrates CV pipeline
│       │   │   ├── risk_service.py        # Risk aggregation
│       │   │   ├── assistant_service.py   # LangGraph invocation
│       │   │   └── maintenance_service.py # ML model inference via 3G (3H)
│       │   └── tasks/                     # Celery task definitions
│       │       ├── scoring.py             # Periodic driver score updates
│       │       ├── events.py              # Event post-processing
│       │       └── maintenance.py         # Batch maintenance predictions (3H)
│       ├── alembic/                       # DB migration scripts
│       │   └── versions/
│       ├── tests/
│       │   ├── test_driver_api.py
│       │   ├── test_risk_engine.py
│       │   └── fixtures/
│       │       └── test_frame.jpg
│       ├── requirements.txt
│       └── Dockerfile
│
├── ml/                                    # All ML / CV code
│   ├── driver_monitoring/
│   │   ├── ear_detector.py               # EAR formula, Dlib integration
│   │   ├── mar_detector.py               # MAR formula for yawn detection
│   │   ├── head_pose.py                  # MediaPipe solvePnP head pose
│   │   ├── yolo_detector.py              # Phone/seatbelt/smoking YOLO
│   │   └── pipeline.py                   # Combined frame → JSON pipeline
│   ├── cabin_intelligence/
│   │   ├── occupancy_detector.py         # Seat zone ROI + person detection
│   │   └── child_classifier.py           # Bounding box size heuristic
│   ├── road_understanding/
│   │   ├── road_segmenter.py             # DeepLabV3+ BDD100K road masks (2B)
│   │   ├── object_detector.py            # Optional YOLO boxes for downstream tasks
│   │   ├── tracker.py                    # ByteTrack via supervision
│   │   ├── depth_estimator.py            # MiDaS monocular depth
│   │   ├── traffic_light.py              # HSV traffic light state classifier
│   │   ├── pedestrian_temporal.py        # Caltech YOLO-LSTM localization
│   │   └── pipeline.py                    # Unified stateful 2B–2F pipeline (2G)
│   ├── predictive_maintenance/
│   │   ├── config.py                     # Local CSV paths + thresholds (3A)
│   │   ├── datasets.py                   # Loaders + train-ready frames (3A)
│   │   ├── features.py                   # Feature engineering transforms (3A)
│   │   ├── data_generator.py             # prepare_all_module_frames facade (3A)
│   │   ├── engine_model.py               # Engine / fault model (3B)
│   │   ├── brake_model.py                # Brake condition classification (3C)
│   │   ├── battery_model.py              # Battery SoH models (3D)
│   │   ├── tire_model.py                 # Tire wear from logistics TPI (3E)
│   │   └── pipeline.py                   # Unified 3B–3E orchestration + SHAP (3G)
│   ├── risk_engine/
│   │   ├── aggregator.py                 # Composite weighted risk scoring
│   │   ├── rules.yaml                    # Hard override rule configurations
│   │   └── event_detector.py             # TTC + safety event detection
│   ├── assistant/
│   │   ├── knowledge_base.py             # PDF ingestion → ChromaDB indexing
│   │   ├── agent.py                      # LangGraph agent graph definition
│   │   └── evaluator.py                  # RAG evaluation on 50-pair test set
│   ├── xai/
│   │   ├── gradcam.py                    # EigenCAM for YOLOv8 models
│   │   ├── shap_explainer.py             # SHAP TreeExplainer wrapper (used by 3G)
│   │   └── nl_explainer.py               # LLM-powered NL explanation generator
│   ├── training/                          # Training helpers
│   │   ├── train_driver_yolo.py          # DMD → YOLOv8n fine-tuning
│   │   ├── train_road_yolo.py            # Optional BDD100K object detector
│   │   ├── train_pedestrian_temporal.py  # Caltech frames → YOLO-LSTM
│   │   └── mlflow_logger.py              # MLflow tracking wrapper
│   └── demo/
│       ├── demo_runner.py                # Replay recorded video + telemetry
│       └── assets/
│           └── demo_drive.mp4            # Sample drive footage for demos
│
├── sdv/                                   # Software-Defined Vehicle layer
│   ├── kuksa/
│   │   ├── vehicle_app.py                # Velocitas Vehicle App definition
│   │   ├── signal_subscriber.py          # VSS signal subscription + storage (3F)
│   │   └── vss_config.json               # VSS path mappings for this vehicle
│   └── mock/
│       └── sensor_simulator.py           # Synthetic VSS signal generator for demo (3F)
│
├── infra/
│   ├── docker-compose.yml                # All 12 services
│   ├── docker-compose.prod.yml           # Production overrides
│   ├── nginx.conf                        # Reverse proxy
│   ├── prometheus.yml                    # Metrics scraping config
│   └── grafana/
│       └── dashboards/
│           ├── fleet_overview.json
│           └── api_performance.json
│
├── .github/
│   └── workflows/
│       ├── ci.yml                        # Lint + test on PR
│       └── deploy.yml                    # Deploy on push to main
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── setup.md
│
├── notebooks/                            # Development/exploration notebooks
│   ├── 01_ear_threshold_validation.ipynb
│   ├── 02_bdd100k_exploration.ipynb
│   ├── 03_maintenance_feature_engineering.ipynb  # Local EVIoT/NEV/logistics frames (3A)
│   ├── train_engine_fault_3b.ipynb        # Local NEV XGBoost classifier (3B)
│   ├── train_brake_wear_3c.ipynb          # Local logistics classifier (3C)
│   ├── train_battery_soh_3d.ipynb          # Chronological SoH regression (3D)
│   └── 04_rag_evaluation.ipynb
│
├── .env.example
└── README.md
```

---

## 8. Phase-by-Phase Workflow

### Phase 0 — Environment Setup & Project Scaffold
**Timeline: Days 1–5**

**What you achieve:** A fully running local development environment with all 12 Docker services, initialized database schema, and scaffolded frontend and backend. Before writing a single line of ML code, everything is wired together.

#### Step 0.1 — Prerequisites Installation

```bash
# Ubuntu 22.04 (recommended)
sudo apt update && sudo apt install -y \
  python3.11 python3.11-dev python3-pip \
  build-essential cmake git curl wget \
  libopencv-dev libgl1-mesa-glx \
  nodejs npm

# Install pnpm (faster than npm)
npm install -g pnpm

# Install pyenv for clean Python version management
curl https://pyenv.run | bash
pyenv install 3.11.9
pyenv global 3.11.9

# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop/
# Set memory: 8GB, CPU: 4 cores, Disk: 60GB in Docker Desktop settings
```

#### Step 0.2 — Project Scaffold

```bash
# Initialize repository
mkdir bmw-ai-platform && cd bmw-ai-platform
git init
git remote add origin https://github.com/YOUR_USERNAME/bmw-ai-platform

# Create Next.js frontend
pnpm create next-app apps/frontend --typescript --tailwind --app --no-src-dir
# Then move to src/ structure manually or use --src-dir flag on newer versions

# Create backend structure
mkdir -p apps/backend/app/{core,api/v1,models,schemas,services,tasks}
mkdir -p apps/backend/{alembic,tests}
mkdir -p ml/{driver_monitoring,cabin_intelligence,road_understanding,predictive_maintenance,risk_engine,assistant,xai,training,demo/assets}
mkdir -p sdv/{kuksa,mock}
mkdir -p infra/grafana/dashboards
mkdir -p notebooks docs
```

#### Step 0.3 — Docker Compose Setup

Create `infra/docker-compose.yml`:

```yaml
version: '3.9'

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: bmwai
      POSTGRES_PASSWORD: bmwai_secret
      POSTGRES_DB: bmwai_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bmwai"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --save 20 1 --loglevel warning

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    volumes:
      - minio_data:/data

  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.14.3
    ports:
      - "5000:5000"
    command: mlflow server --host 0.0.0.0 --backend-store-uri /mlflow

  kuksa-databroker:
    image: ghcr.io/eclipse-kuksa/kuksa-databroker:0.4.4
    ports:
      - "55555:55555"
    command: ["--insecure"]

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    depends_on:
      - prometheus

  backend:
    build: ../apps/backend
    ports:
      - "8000:8000"
    env_file: ../.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      chromadb:
        condition: service_started
    volumes:
      - ../apps/backend:/app
      - ../ml:/ml

  frontend:
    build: ../apps/frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
  chroma_data:
  minio_data:
  ollama_data:
```

#### Step 0.4 — Environment Configuration

Create `.env` in project root:

```bash
# ── Database ──────────────────────────────────
DATABASE_URL=postgresql+asyncpg://bmwai:bmwai_secret@localhost:5432/bmwai_db
DATABASE_URL_SYNC=postgresql://bmwai:bmwai_secret@localhost:5432/bmwai_db

# ── Redis ─────────────────────────────────────
REDIS_URL=redis://localhost:6379

# ── Security ──────────────────────────────────
SECRET_KEY=change-this-to-a-real-random-string-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── LLM APIs (optional — Ollama works without these) ──
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# ── Storage ───────────────────────────────────
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_EVENTS=safety-events
MINIO_BUCKET_HEATMAPS=xai-heatmaps

# ── ChromaDB ──────────────────────────────────
CHROMA_HOST=localhost
CHROMA_PORT=8001

# ── Kuksa ─────────────────────────────────────
KUKSA_HOST=localhost
KUKSA_PORT=55555

# ── MLflow ────────────────────────────────────
MLFLOW_TRACKING_URI=http://localhost:5000

# ── Ollama ────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

#### Step 0.5 — FastAPI Backend Skeleton

Create `apps/backend/app/main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import auth, driver, road, risk, maintenance, assistant, fleet, events, analytics, xai, ws

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if not exist (Alembic handles migrations in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: close connections
    await engine.dispose()

app = FastAPI(
    title="BMW AI Automotive Intelligence Platform",
    description="Production-grade automotive AI: ADAS, SDV, Predictive Maintenance, XAI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
for router_module in [auth, driver, road, risk, maintenance, assistant, fleet, events, analytics, xai, ws]:
    app.include_router(router_module.router)
```

Create `apps/backend/app/core/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    kuksa_host: str = "localhost"
    kuksa_port: int = 55555
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    mlflow_tracking_uri: str = "http://localhost:5000"

    class Config:
        env_file = ".env"

settings = Settings()
```

#### Step 0.6 — Initialize Database

```bash
cd apps/backend
pip install -r requirements.txt

# Initialize Alembic
alembic init alembic

# Edit alembic/env.py to use your models and async engine
# Then generate and run the first migration:
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head

# Verify tables were created
psql -U bmwai -d bmwai_db -h localhost -c "\dt"
```

#### Step 0.7 — Install Ollama LLM

```bash
# Start Ollama service (already running via Docker)
# Pull the LLM model (3B parameter — works on CPU too)
docker exec -it bmw-ai-platform-ollama-1 ollama pull llama3.2:3b

# Test it works
curl http://localhost:11434/api/generate -d '{"model": "llama3.2:3b", "prompt": "Hello"}'
```

#### Step 0.8 — GitHub Actions CI

Create `.github/workflows/ci.yml`:

```yaml
name: CI Pipeline

on: [push, pull_request]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_USER: test
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install -r apps/backend/requirements.txt
      - run: cd apps/backend && python -m pytest tests/ -v --tb=short
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test
          SECRET_KEY: test-secret-key

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
      - run: cd apps/frontend && pnpm install
      - run: cd apps/frontend && pnpm lint
      - run: cd apps/frontend && pnpm build
```

---

### Phase 1 — Driver Monitoring System (Module 01)
**Timeline: Days 6–22 | Training: Kaggle**

**What you achieve:** A working real-time driver monitoring system that processes webcam frames and detects drowsiness, yawning, head pose, and dangerous objects — all with XAI heatmap output.

#### Step 1.1 — Download Dlib Facial Landmark Predictor

```bash
# Required for EAR/MAR calculation
wget http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
bzip2 -dk shape_predictor_68_face_landmarks.dat.bz2
mkdir -p ml/models
mv shape_predictor_68_face_landmarks.dat ml/models/
```

#### Step 1.2 — Implement EAR and MAR Detectors

Create `ml/driver_monitoring/ear_detector.py`:

```python
import dlib
import cv2
import numpy as np
from scipy.spatial import distance
from dataclasses import dataclass
from typing import Optional

PREDICTOR_PATH = "ml/models/shape_predictor_68_face_landmarks.dat"
EAR_THRESHOLD = 0.25          # Below this = eye closing
MAR_THRESHOLD = 0.60          # Above this = yawning
DROWSY_FRAME_COUNT = 30       # Frames before triggering drowsy alert

# Dlib landmark indices
LEFT_EYE_IDX = list(range(36, 42))
RIGHT_EYE_IDX = list(range(42, 48))
MOUTH_IDX = list(range(60, 68))

@dataclass
class DriverFaceState:
    ear: Optional[float]
    mar: Optional[float]
    is_drowsy: bool
    is_yawning: bool
    face_detected: bool

_detector = dlib.get_frontal_face_detector()
_predictor = dlib.shape_predictor(PREDICTOR_PATH)

def _landmark_to_array(landmarks, indices):
    return np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in indices], dtype=np.float64)

def _compute_ear(eye_points: np.ndarray) -> float:
    """Eye Aspect Ratio — vertical distances over horizontal distance."""
    A = distance.euclidean(eye_points[1], eye_points[5])
    B = distance.euclidean(eye_points[2], eye_points[4])
    C = distance.euclidean(eye_points[0], eye_points[3])
    return (A + B) / (2.0 * C)

def _compute_mar(mouth_points: np.ndarray) -> float:
    """Mouth Aspect Ratio — measures mouth openness."""
    A = distance.euclidean(mouth_points[2], mouth_points[6])
    B = distance.euclidean(mouth_points[0], mouth_points[4])
    return A / B if B > 0 else 0.0

def analyze_frame(frame: np.ndarray) -> DriverFaceState:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = _detector(gray, 0)

    if not faces:
        return DriverFaceState(ear=None, mar=None, is_drowsy=False, is_yawning=False, face_detected=False)

    face = faces[0]  # Use the largest face (closest to camera)
    landmarks = _predictor(gray, face)

    left_eye = _landmark_to_array(landmarks, LEFT_EYE_IDX)
    right_eye = _landmark_to_array(landmarks, RIGHT_EYE_IDX)
    mouth = _landmark_to_array(landmarks, MOUTH_IDX)

    ear = (_compute_ear(left_eye) + _compute_ear(right_eye)) / 2.0
    mar = _compute_mar(mouth)

    return DriverFaceState(
        ear=round(ear, 4),
        mar=round(mar, 4),
        is_drowsy=ear < EAR_THRESHOLD,
        is_yawning=mar > MAR_THRESHOLD,
        face_detected=True,
    )
```

#### Step 1.3 — Head Pose Estimation with MediaPipe

Create `ml/driver_monitoring/head_pose.py`:

```python
import mediapipe as mp
import cv2
import numpy as np

mp_face_mesh = mp.solutions.face_mesh

# 3D reference model points (standard face model)
FACE_3D_MODEL = np.array([
    [0.0, 0.0, 0.0],          # Nose tip
    [0.0, -330.0, -65.0],     # Chin
    [-225.0, 170.0, -135.0],  # Left eye left corner
    [225.0, 170.0, -135.0],   # Right eye right corner
    [-150.0, -150.0, -125.0], # Left mouth corner
    [150.0, -150.0, -125.0]   # Right mouth corner
], dtype=np.float64)

DISTRACTION_PITCH_THRESHOLD = 15.0   # degrees — looking down at phone
DISTRACTION_YAW_THRESHOLD = 15.0     # degrees — looking sideways

class HeadPoseEstimator:
    def __init__(self):
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def estimate(self, frame: np.ndarray) -> dict:
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "distracted": False}

        landmarks = results.multi_face_landmarks[0].landmark

        # MediaPipe landmark indices for the 6 reference points
        lm_indices = [4, 152, 263, 33, 287, 57]
        face_2d = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in lm_indices], dtype=np.float64)

        focal_length = w
        cam_matrix = np.array([[focal_length, 0, w / 2],
                                [0, focal_length, h / 2],
                                [0, 0, 1]], dtype=np.float64)

        _, rvec, _ = cv2.solvePnP(FACE_3D_MODEL, face_2d, cam_matrix, np.zeros((4, 1)))
        rmat, _ = cv2.Rodrigues(rvec)
        angles, *_ = cv2.RQDecomp3x3(rmat)
        pitch, yaw, roll = angles[0] * 360, angles[1] * 360, angles[2] * 360

        distracted = abs(pitch) > DISTRACTION_PITCH_THRESHOLD or abs(yaw) > DISTRACTION_YAW_THRESHOLD

        return {
            "pitch": round(pitch, 2),
            "yaw": round(yaw, 2),
            "roll": round(roll, 2),
            "distracted": distracted
        }
```

#### Step 1.4 — Kaggle Training Notebook for DMD Dataset

Create a Kaggle notebook `notebooks/train_driver_yolo_kaggle.py` (paste into Kaggle notebook UI):

```python
# === KAGGLE NOTEBOOK: YOLOv8 Driver Monitoring Training ===
# Runtime: GPU T4 x2 | Estimated time: 3-5 hours
# Dataset: Add DMD dataset from your Kaggle uploads

import os
from pathlib import Path
from ultralytics import YOLO
import mlflow

# ── Dataset structure verification ──
DATASET_YAML = "/kaggle/input/dmd-driver-monitoring/dataset.yaml"

# Verify dataset.yaml content:
# path: /kaggle/input/dmd-driver-monitoring
# train: images/train
# val:   images/val
# nc: 3
# names: [phone, smoking, no_seatbelt]

# ── Training configuration ──
model = YOLO("yolov8n.pt")  # Start from COCO pretrained weights

results = model.train(
    data=DATASET_YAML,
    epochs=100,
    imgsz=640,
    batch=32,          # T4 can handle 32 at 640px
    device=0,          # Use GPU
    patience=15,       # Early stopping
    save_period=10,    # Save checkpoint every 10 epochs
    project="/kaggle/working/runs",
    name="driver_monitor_dmd_v1",
    # Data augmentation
    flipud=0.0,        # Don't flip upside down (cars have gravity)
    fliplr=0.5,        # Horizontal flip is fine
    mosaic=1.0,
    mixup=0.1,
)

print(f"Best mAP50: {results.results_dict['metrics/mAP50(B)']:.4f}")
print(f"Best mAP50-95: {results.results_dict['metrics/mAP50-95(B)']:.4f}")

# ── Save best weights to Google Drive (optional) ──
# from google.colab import drive
# drive.mount('/content/drive')
# import shutil
# shutil.copy("runs/detect/driver_monitor_dmd_v1/weights/best.pt",
#             "/content/drive/MyDrive/bmw_models/driver_monitor_best.pt")

# The best.pt file is in /kaggle/working/runs/detect/driver_monitor_dmd_v1/weights/
# Download it from the Kaggle output panel
```

#### Step 1.5 — Combined Driver Analysis Pipeline

Create `ml/driver_monitoring/pipeline.py`:

```python
import cv2
import numpy as np
from typing import Optional
from .ear_detector import analyze_frame, DriverFaceState
from .head_pose import HeadPoseEstimator
from .yolo_detector import YOLODriverDetector
from ..xai.gradcam import generate_gradcam_heatmap

class DriverMonitoringPipeline:
    def __init__(self, yolo_model_path: str):
        self.head_pose = HeadPoseEstimator()
        self.yolo = YOLODriverDetector(yolo_model_path)
        self._drowsy_frame_count = 0
        self._yawn_count = 0

    def process_frame(self, frame: np.ndarray, vehicle_id: str, session_id: str) -> dict:
        # 1. EAR/MAR analysis
        face_state = analyze_frame(frame)

        # 2. Head pose
        pose = self.head_pose.estimate(frame)

        # 3. YOLO detection (phone, smoking, seatbelt)
        yolo_detections = self.yolo.detect(frame)

        # 4. Consecutive drowsy frame counter
        if face_state.is_drowsy:
            self._drowsy_frame_count += 1
        else:
            self._drowsy_frame_count = 0

        if face_state.is_yawning:
            self._yawn_count += 1

        # 5. Compute alertness score (inverse risk from driver state alone)
        alertness = 100
        if face_state.ear and face_state.ear < 0.25:
            alertness -= 30
        if pose["distracted"]:
            alertness -= 20
        if yolo_detections.get("phone_detected"):
            alertness -= 25
        if not yolo_detections.get("seatbelt_worn", True):
            alertness -= 15
        alertness = max(0, alertness)

        return {
            "vehicle_id": vehicle_id,
            "session_id": session_id,
            "alertness_score": alertness,
            "risk_level": "CRITICAL" if alertness < 30 else "HIGH" if alertness < 50 else "MEDIUM" if alertness < 75 else "LOW",
            "ear_value": face_state.ear,
            "mar_value": face_state.mar,
            "is_drowsy": face_state.is_drowsy,
            "is_yawning": face_state.is_yawning,
            "consecutive_drowsy_frames": self._drowsy_frame_count,
            "yawn_count": self._yawn_count,
            "head_pose": pose,
            "phone_detected": yolo_detections.get("phone_detected", False),
            "smoking_detected": yolo_detections.get("smoking_detected", False),
            "seatbelt_worn": yolo_detections.get("seatbelt_worn", True),
            "face_detected": face_state.face_detected,
        }
```

#### Step 1.6 — FastAPI Driver Endpoint

Create `apps/backend/app/api/v1/driver.py`:

```python
from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect
import numpy as np
import cv2
from app.services.driver_service import get_pipeline

router = APIRouter(prefix="/api/v1/driver", tags=["driver-monitoring"])

@router.post("/analysis")
async def analyze_single_frame(file: UploadFile = File(...)):
    """Analyze a single image frame — useful for testing."""
    image_bytes = await file.read()
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    pipeline = await get_pipeline()
    result = pipeline.process_frame(frame, vehicle_id="test", session_id="test")
    return result

@router.websocket("/stream/{vehicle_id}/{session_id}")
async def driver_stream(websocket: WebSocket, vehicle_id: str, session_id: str):
    """Real-time driver monitoring stream — receives JPEG frames, sends analysis JSON."""
    await websocket.accept()
    pipeline = await get_pipeline()

    try:
        while True:
            frame_bytes = await websocket.receive_bytes()
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is not None:
                result = pipeline.process_frame(frame, vehicle_id=vehicle_id, session_id=session_id)
                await websocket.send_json(result)
    except WebSocketDisconnect:
        pass
```

---

### Phase 2 — Road Understanding System (Module 03)
**Timeline: Days 15–28 | Training: Kaggle (parallel with Phase 1)**

**What you achieve:** A real-time road scene pipeline that detects and tracks objects, estimates distance, classifies traffic lights, and temporally confirms the primary pedestrian through short detector dropouts.

#### Step 2.1 — Kaggle Training Notebook for BDD100K

```python
# === KAGGLE NOTEBOOK: YOLOv8m Road Scene Training ===
# Dataset: Search "BDD100K" on Kaggle — use the official dataset
# Runtime: GPU P100 | Estimated time: 8–12 hours for 50 epochs

from ultralytics import YOLO

# BDD100K has 100K images — train on the full set
model = YOLO("yolov8m.pt")  # Medium model for better road scene accuracy

results = model.train(
    data="/kaggle/input/bdd100k-yolo/bdd100k.yaml",
    epochs=50,
    imgsz=640,
    batch=16,             # YOLOv8m is larger — reduce batch size
    device=0,
    patience=10,
    project="/kaggle/working/road_detection",
    name="road_yolov8m_bdd100k_v1",
    # BDD100K-specific settings
    rect=True,            # Rectangular training reduces padding, speeds up training
    cache=True,           # Cache images in RAM (P100 has enough RAM)
)

# Expected results after 50 epochs on BDD100K:
# mAP50: ~0.58, mAP50-95: ~0.38
# Best classes: car (mAP50 ~0.72), traffic light (~0.65), pedestrian (~0.52)
```

#### Step 2.2 — Caltech Temporal Pedestrian Localization Training

```python
# Full implementation: notebooks/train_pedestrian_temporal.ipynb
# Dataset: https://www.kaggle.com/datasets/abhinavsasikumar/caltech-pedestrian-yolo/data
# Runtime: GPU T4 recommended

import torch
import torch.nn as nn
from ultralytics import YOLO

class TemporalPedestrianYOLOLSTM(nn.Module):
    """Five RGB frames → primary normalized pedestrian bbox + confidence."""
    def __init__(self, hidden_size=256):
        super().__init__()
        yolo = YOLO("yolov8n.pt")
        self.backbone = nn.Sequential(*list(yolo.model.model.children())[:10])
        self.lstm = nn.LSTM(
            input_size=256 * 7 * 7,
            hidden_size=hidden_size,
            batch_first=True,
        )
        self.fc_bbox = nn.Linear(hidden_size, 4)
        self.fc_conf = nn.Linear(hidden_size, 1)

    def forward(self, frames):
        batch, steps, channels, height, width = frames.shape
        features = self.backbone(
            frames.reshape(batch * steps, channels, height, width)
        )
        features = features.flatten(1).reshape(batch, steps, -1)
        _, (hidden, _) = self.lstm(features)
        return (
            torch.sigmoid(self.fc_bbox(hidden[-1])),
            torch.sigmoid(self.fc_conf(hidden[-1])).squeeze(-1),
        )

# Train with sequence-group-level splits. Regress normalized YOLO xywh for the
# largest pedestrian in the final frame and BCE confidence for empty/positive
# frames. Save as /kaggle/working/best_pedestrian_yololstm.pt.
```

---

### Phase 3 — Predictive Maintenance System (Module 06)
**Timeline: Days 22–35 | Training: Colab or Local**

**What you achieve:** ML models that predict vehicle component failures from sensor data, integrated with Kuksa VSS signals.

**Submodules (implement in order; 3F may run parallel to 3B–3E):**

| ID | Name | Deliverable |
|----|------|-------------|
| 3A | Feature engineering and datasets | Local loaders for EVIoT / battery / NEV / logistics + feature frames |
| 3B | Engine health | NEV fault classifier (+ optional autoencoder) — local notebook |
| 3C | Brake condition | XGBoost Good/Fair/Poor classifier on logistics data — local notebook |
| 3D | Battery (EV) | Chronological SoH regression on cycle-aging CSV — local notebook |
| 3E | Tire wear | Leakage-safe XGBoost `Tire_Wear_pct` proxy from logistics `TPI` — local notebook |
| 3F | Kuksa VSS I/O | Databroker subscribe/store + mock simulator |
| 3G | Unified maintenance pipeline | Partial-failure 3B–3E orchestration + native XGBoost SHAP explanations |
| 3H | Backend API and jobs | REST + Celery → `maintenance_predictions` |
| 3I | Maintenance UI | Next.js health cards, alerts, feature contributions |

#### Step 3.1 — Local feature preparation and 3B fault training

Module 3A loads the four local CSVs from `data/predictive_maintenance/`.
Run `notebooks/03_maintenance_feature_engineering.ipynb` to inspect the
train-ready frames.

Module 3B uses `NEV_fault_dataset.csv` to train a four-class XGBoost
classifier:

```python
from ml.predictive_maintenance import prepare_engine_fault_frame

frame = prepare_engine_fault_frame()
X_train, X_test, y_train, y_test = frame.train_test_split(stratify=True)
```

The complete leakage-safe train/validation/test workflow, early stopping,
metrics, confusion matrix, feature importance, artifact metadata, and reload
check live in `notebooks/train_engine_fault_3b.ipynb`. It writes
`ml/models/engine_fault_clf.joblib`, consumed by
`ml.predictive_maintenance.EngineFaultClassifier`.

Module 3C trains locally in `notebooks/train_brake_wear_3c.ipynb`. The original
EVIoT pad-wear regression was rejected after it failed to beat the mean
baseline. Option A redefines 3C as logistics `Brake_Condition` classification
(`Good`, `Fair`, `Poor`) using leakage-safe telemetry and usage features. It
saves `ml/models/brake_condition_xgb.joblib`, consumed by
`ml.predictive_maintenance.BrakeConditionClassifier`.

Module 3D trains locally in `notebooks/train_battery_soh_3d.ipynb` using the
cycle-aging CSV. It excludes `Capacity_Ah` because capacity directly defines
`SOH_pct`, and excludes EVIoT SoH after profiling found no telemetry
relationship. A chronological 70/15/15 split measures future-cycle behavior
against a last-known-SOH baseline. The accepted model is refit on all cycles
and saved as `ml/models/battery_soh_xgb.joblib`.

#### Step 3.2 — Kuksa Signal Subscription (3F)

Implemented in:

- `sdv/kuksa/signal_subscriber.py` — async `kuksa_client.grpc.aio.VSSClient`
  adapter, typed `TelemetrySnapshot`, partial-update merging, one-shot reads,
  streaming, and injectable stores
- `sdv/kuksa/vss_config.json` — VSS path → database field contract
- `apps/backend/app/services/kuksa_service.py` — backend-configured subscriber
  with `SqlAlchemyTelemetryStore` persistence to `vehicle_telemetry`
- `sdv/mock/sensor_simulator.py` — deterministic broker-free telemetry and
  optional publishing of current values to Kuksa

The live broker remains optional in tests. `InMemoryTelemetryStore` and an
injectable client factory let subscription, storage, and partial-update
behavior run without Docker or vehicle hardware. Production/demo connectivity
uses `KUKSA_HOST`, `KUKSA_PORT`, `kuksa-client==0.5.2`, and the Databroker
service in `infra/docker-compose.yml`.

#### Step 3.3 — Unified Maintenance Pipeline (3G)

Implemented in `ml/predictive_maintenance/pipeline.py` with shared native
TreeSHAP extraction in `ml/xai/shap_explainer.py`.

`MaintenancePipeline.predict()` accepts either nested `engine`, `brake`,
`battery`, and `tire` feature mappings or one flat enriched mapping. It
validates each model's exact training contract, runs 3B–3E independently,
derives normalized severity/maintenance alerts, and preserves successful
component results when another model, artifact, feature set, or explanation is
unavailable. Each successful XGBoost result includes the top three local SHAP
contributions and risk direction.

The models were trained on heterogeneous sources, so a raw Kuksa snapshot is
not silently coerced into incompatible normalized NEV, cycle-aging, or
logistics fields. Missing inputs remain explicit in the component result until
3H or a telemetry-enrichment adapter joins VSS readings with stored vehicle
history.

#### Step 3.4 — Backend API, Celery jobs, and persistence (3H)

Implemented in:

- `apps/backend/app/services/maintenance_service.py` — lazily builds one
  shared `MaintenancePipeline`, exposes artifact readiness, and maps
  successful component results to `maintenance_predictions` rows (severity,
  maintenance flag, raw result, and SHAP contributions stored in the
  `shap_explanation` JSONB column; `ml_model_version="phase3-3g-v1"`)
- `apps/backend/app/api/v1/maintenance.py` — real REST endpoints replacing the
  Phase 0 scaffold
- `apps/backend/app/tasks/maintenance.py` —
  `app.tasks.maintenance.run_batch_predictions` Celery task that runs the 3G
  pipeline off the request path and persists rows via
  `async_session_maker`

REST surface:

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/maintenance/status` | Artifact readiness + per-component feature contracts, no inference |
| `POST /api/v1/maintenance/{vehicle_id}/predict` | Run 3G synchronously, persist successful components, return the full pipeline contract |
| `POST /api/v1/maintenance/{vehicle_id}/trigger` | Enqueue the Celery batch task; returns `task_id` |
| `GET /api/v1/maintenance/{vehicle_id}` | Latest persisted prediction per component |
| `GET /api/v1/maintenance/{vehicle_id}/history` | Recent predictions, newest first (bounded `limit`) |
| `GET /api/v1/maintenance/{vehicle_id}/{component}` | Latest row incl. SHAP payload for `engine`/`brake`/`battery`/`tire` |

Design decisions: `predict` accepts the same nested-or-flat telemetry payload
as 3G, so partial results (`unavailable` components with explicit missing
features) flow through the API unchanged; persistence failures degrade to
`persisted: 0` without discarding the inference response; the Celery task
requires an explicit telemetry payload because raw VSS alone does not satisfy
the 3B–3E training contracts. Tests live in
`apps/backend/tests/test_maintenance_api.py` with ML inference and the DB
session mocked.

#### Step 3.5 — Predictive maintenance dashboard (3I)

Implemented as a responsive Next.js 14 App Router page at
`apps/frontend/src/app/maintenance/page.tsx`, backed by:

- `apps/frontend/src/components/maintenance/MaintenanceDashboard.tsx` —
  vehicle selection, model readiness, synchronous 3G inference, component
  health cards, maintenance alerts, persisted health trends, explicit
  unavailable/error states, and top native XGBoost SHAP contributions
- `apps/frontend/src/lib/api.ts` — typed 3H status, latest, history, and
  prediction requests through the shared authenticated Axios client
- `apps/frontend/src/lib/types.ts` — end-to-end TypeScript contracts for 3H
  responses, component states, severity, persisted rows, and explanations

The dashboard displays model health scores on a 0–100% presentation scale
while retaining the API's normalized 0–1 values. A JSON telemetry editor can
generate its nested feature template directly from the 3H status contract;
the operator supplies real values before inference. Missing fields and
component failures remain visible rather than being replaced with synthetic
telemetry. Recharts visualizes persisted engine, brake, battery, and tire
health history, and each component card shows risk direction for its top
three local feature contributions. Home, driver, road, and fleet dashboard
navigation now link to `/maintenance`.

Frontend verification uses `npm run type-check`, `npm run lint`, and
`npm run build`. The backend prediction row schema includes `created_at` so
the trend chart can use actual persistence timestamps.

---

### Phase 4 — Risk Engine + Event Detection (Modules 04 & 08)
**Timeline: Days 28–40 | No training needed**

**What you achieve:** A real-time risk scoring system that combines all module outputs and a safety event detection system with TTC calculation. Events are logged with video clips stored in MinIO.

**Phase 4 module breakdown (4A–4G):**

| Module | Scope | Deliverable |
|---|---|---|
| 4A | Risk scoring core | `ml/risk_engine/aggregator.py` — pure weighted scoring from driver/road/telemetry states, LOW–CRITICAL levels, human-readable reasons; no I/O |
| 4B | Hard override rules | `ml/risk_engine/rules.yaml` + rule evaluator — declarative overrides (drowsy+pedestrian → CRITICAL, unbelted at highway speed → HIGH) |
| 4C | Redis risk distribution | Publish `risk:{vehicle_id}` payloads; backend `risk_service` + WebSocket fan-out to fleet subscribers |
| 4D | TTC + event detectors | `ml/risk_engine/event_detector.py` — TTC from confirmed tracks + depth, drowsy/phone/hard-braking/pedestrian-proximity detectors with Module 08 thresholds |
| 4E | Event persistence + clips | `safety_events` rows with telemetry snapshot and natural-language XAI explanation; 30 s video clips to MinIO |
| 4F | Risk/event REST + jobs | Real `/api/v1/risk` and `/api/v1/events` endpoints replacing scaffolds; Celery post-processing |
| 4G | Live risk + events UI | Next.js risk gauge fed by WebSocket, event feed with acknowledge flow and clip links |

**Scope rules:** 4A and 4B are pure Python with unit tests (no services); 4C requires Redis; 4D consumes 1G/2G pipeline outputs and 3F telemetry but tolerates missing sources; 4E requires Postgres + MinIO; 4F wires 4A–4E; 4G wires 4F. No model training anywhere in Phase 4.

#### Step 4.1 — Risk Aggregation Engine

Module 4A is implemented in `ml/risk_engine/aggregator.py` as a deterministic,
side-effect-free scoring core. `compute_risk()` accepts driver state, road
objects, and the future telemetry contract, then returns immutable
`RiskResult` / `RiskFactor` dataclasses. Every triggered factor records its
weight, contribution, reason, and evidence. It supports both `class` and
`class_name` road object contracts, chooses the nearest pedestrian within
10 m, and detects vehicles closing faster than 20 km/h. Invalid object
measurements are ignored safely; scores are capped at 100 and mapped across
continuous LOW (≤40), MEDIUM (≤65), HIGH (≤85), and CRITICAL (>85) bands.

The 4A core intentionally performs no Redis, database, API, or filesystem I/O.
Hard overrides from the original combined sketch below move to 4B, and Redis
publishing moves to 4C. Public symbols are exported by
`ml/risk_engine/__init__.py`; 22 boundary, contribution, explanation, malformed
input, and serialization tests live in
`ml/risk_engine/tests/test_aggregator.py`.

Original combined design sketch (superseded by the 4A–4C split):

```python
import asyncio
import json
import redis.asyncio as aioredis
from datetime import datetime
from typing import Optional

WEIGHTS = {
    "drowsy": 0.35,
    "phone_usage": 0.25,
    "no_seatbelt": 0.15,
    "pedestrian_proximity": 0.15,
    "aggressive_vehicle": 0.10,
}

RISK_LEVELS = {
    (0, 40): "LOW",
    (41, 65): "MEDIUM",
    (66, 85): "HIGH",
    (86, 100): "CRITICAL",
}

def _get_risk_level(score: float) -> str:
    for (low, high), level in RISK_LEVELS.items():
        if low <= score <= high:
            return level
    return "CRITICAL"

async def compute_and_publish_risk(
    vehicle_id: str,
    driver_state: dict,
    road_state: dict,
    telemetry: Optional[dict] = None
) -> dict:
    score = 0.0
    reasons = []

    # Driver state contributions
    if driver_state.get("is_drowsy"):
        score += WEIGHTS["drowsy"] * 100
        reasons.append(f"Drowsiness detected (EAR: {driver_state.get('ear_value', '?'):.2f})")

    if driver_state.get("phone_detected"):
        score += WEIGHTS["phone_usage"] * 100
        reasons.append("Phone usage detected")

    if not driver_state.get("seatbelt_worn", True):
        score += WEIGHTS["no_seatbelt"] * 100
        reasons.append("Seatbelt not worn")

    # Road state contributions
    objects = road_state.get("objects", [])
    pedestrians_near = [o for o in objects if o["class"] == "pedestrian" and o.get("distance_m", 999) < 10]
    if pedestrians_near:
        score += WEIGHTS["pedestrian_proximity"] * 100
        reasons.append(f"Pedestrian within {min(p['distance_m'] for p in pedestrians_near):.1f}m")

    # Hard override rules
    risk_level = _get_risk_level(score)
    if driver_state.get("is_drowsy") and pedestrians_near:
        score = 100.0
        risk_level = "CRITICAL"
        reasons.append("OVERRIDE: Drowsy driver with pedestrian in path")

    speed = telemetry.get("speed_kmh", 0) if telemetry else 0
    if not driver_state.get("seatbelt_worn", True) and speed > 60:
        score = max(score, 75.0)
        risk_level = "HIGH"
        reasons.append("OVERRIDE: No seatbelt at highway speed")

    result = {
        "vehicle_id": vehicle_id,
        "risk_score": round(min(score, 100.0), 1),
        "risk_level": risk_level,
        "reasons": reasons,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Publish to Redis for WebSocket distribution
    r = aioredis.from_url("redis://localhost:6379")
    await r.publish(f"risk:{vehicle_id}", json.dumps(result))
    await r.close()

    return result
```

#### Step 4.2 — Declarative Hard Override Rules (4B)

Module 4B is implemented in `ml/risk_engine/rules.yaml` and
`ml/risk_engine/rules.py`.

The versioned YAML contract currently defines three safety overrides:

| Rule | Conditions | Result floor |
|---|---|---|
| `drowsy_pedestrian_path` | Driver drowsy AND nearest pedestrian distance < 10 m | score 100, CRITICAL |
| `unbelted_highway_speed` | Seatbelt not worn AND speed > 60 km/h | score 75, HIGH |
| `phone_in_school_zone` | Phone detected AND `school_zone=true` | score 100, CRITICAL |

Rules use structured `source`, `field`, `operator`, and `value` conditions;
the evaluator never executes YAML strings or calls `eval`. Allowed sources and
operators are validated, rule IDs must be unique, score floors must remain
within 0–100, and unknown/malformed/non-finite values fail closed. Overrides
can only increase score/severity; later rules never downgrade an existing
CRITICAL result.

`compute_risk_with_overrides()` composes the 4A weighted result with 4B and
returns an immutable `RiskDecision`. Its audit trail preserves the base
score/level plus every matching rule's evidence, previous/resulting score,
previous/resulting level, and `OVERRIDE:` reason. The evaluator remains pure
Python with no Redis, database, API, or filesystem writes. Module 4A + 4B have
39 unit tests, including threshold boundaries, multiple-rule ordering,
disabled rules, missing telemetry, safe YAML rejection, and serialization.

#### Step 4.3 — Redis risk distribution and fleet WebSocket fan-out (4C)

Implemented in:

- `apps/backend/app/services/risk_service.py` — runs
  `compute_risk_with_overrides`, normalizes the Redis payload
  (`score`/`level` plus `risk_score`/`risk_level` aliases), caches
  `risk:latest:{vehicle_id}` for 300 s, and publishes
  `risk:{vehicle_id}`
- `apps/backend/app/core/redis.py` — `publish_json` and
  `iter_pattern_messages` helpers for JSON pub/sub
- `apps/backend/app/api/v1/risk.py` — real endpoints:
  - `POST /api/v1/risk/{vehicle_id}/compute` evaluates + optionally
    publishes/caches
  - `GET /api/v1/risk/current/{vehicle_id}` returns the latest cache
    (or an empty LOW placeholder)
  - `GET /api/v1/risk/history/{vehicle_id}` currently returns the
    latest cache only; durable history remains Module 4F
- `apps/backend/app/api/v1/ws.py` — `/api/v1/fleet/ws/{org_id}`
  replaces the echo scaffold with a Redis `risk:*` pattern
  subscription and pushes `{"type":"risk_update","data":...}` frames;
  clients may send `ping` for `pong`

Design decisions: scoring stays pure in `ml/risk_engine`; I/O lives in
the backend service. Publish/cache failures degrade gracefully so the
HTTP response still carries the computed decision. Organization-scoped
channel filtering is deferred until fleet auth lands — every connected
WS client currently receives the full `risk:*` stream. Tests live in
`apps/backend/tests/test_risk_api.py` with Redis mocked.

#### Step 4.4 — TTC calculation and safety event detectors (4D)

Implemented in `ml/risk_engine/event_detector.py` as a pure, side-effect-free
detector layer that consumes Phase 1 driver monitoring (1G), Phase 2 road
understanding (2G), and Phase 3 Kuksa telemetry (3F). Missing inputs are
tolerated — each detector skips when its required fields are absent and records
the skip in `EventDetectionResult.skipped_detectors`.

**TTC helper** — `compute_ttc_seconds(distance_m, relative_speed_kmh)` uses
`distance / (relative_speed_kmh / 3.6)` and returns `None` when the object is
not closing fast enough to produce a finite TTC.

**Stateful `EventDetector`** — maintains phone-duration frames and speed history
for deceleration; call `reset()` before a new drive stream. `process_frame()`
returns immutable `SafetyEvent` / `EventDetectionResult` dataclasses with
evidence and a telemetry snapshot (speed, EAR, risk score, GPS when present).

| Event type | Trigger (Module 08) | Severity |
|---|---|---|
| `NEAR_COLLISION` | Confirmed vehicle track, TTC < 2.0 s | CRITICAL |
| `DRIVER_ASLEEP` | `consecutive_drowsy_frames` > 60 (2 s @ 30 fps) | CRITICAL |
| `UNSAFE_FOLLOWING_DISTANCE` | TTC < 4.0 s and speed > 60 km/h | HIGH |
| `SUDDEN_HARD_BRAKING` | Longitudinal decel < −12 km/h/s | MEDIUM |
| `PROLONGED_PHONE_USAGE` | Phone detected > 5 consecutive seconds | HIGH |
| `PEDESTRIAN_PROXIMITY_HAZARD` | Confirmed/temporal pedestrian < 15 m with closing motion | HIGH |

Design decisions: TTC uses confirmed vehicle tracks with `distance_m` and
`relative_speed_kmh` from the 2G object contract; pedestrian hazards accept
`temporally_confirmed` tracks. Near-collision takes precedence over unsafe-
following for the same object (TTC < 2 s does not also emit unsafe-following).
No Redis, database, API, or MinIO I/O — persistence and clips remain Module 4E.
Public symbols are exported by `ml/risk_engine/__init__.py`; 14 unit tests live
in `ml/risk_engine/tests/test_event_detector.py`.

#### Step 4.5 — Event persistence and MinIO video clips (4E)

Implemented in:

- `ml/risk_engine/explanations.py` — deterministic rule-template XAI strings
  for every Module 4D event type (no LLM required at runtime)
- `apps/backend/app/services/event_service.py` — runs 4D detection, maps
  results to `safety_events` rows, materializes a 30 s rolling clip, and
  uploads MP4 objects to MinIO
- `apps/backend/app/services/video_clip_buffer.py` — per-vehicle JPEG ring
  buffer sized for 30 s @ 30 fps
- `apps/backend/app/services/clip_encoder.py` — JPEG sequence → MP4 via
  OpenCV when `opencv-python` is installed
- `apps/backend/app/core/minio.py` — bucket ensure + `minio://` URL helper
- `apps/backend/app/tasks/events.py` — Celery `post_process_event` retries
  clip upload when MinIO was unavailable during the initial persist

**Persistence flow**

1. Stream JPEG frames into `append_frame(vehicle_id, bytes)` (rolling buffer).
2. `detect_and_persist(...)` runs 4D, writes one `safety_events` row per
   detection with `telemetry_snapshot` + `xai_explanation`.
3. The last 30 s of buffered frames are encoded to MP4 and uploaded as
   `{vehicle_id}/{event_id}.mp4` in the `safety-events` bucket.
4. `video_clip_url` is stored as `minio://safety-events/...` on the row.

Design decisions: Postgres persistence is required; clip upload degrades
gracefully when MinIO or OpenCV is unavailable (rows still save without
`video_clip_url`). REST ingestion endpoints remain Module 4F; 4E exposes the
service layer and Celery retry hook only. Tests live in
`ml/risk_engine/tests/test_explanations.py` and
`apps/backend/tests/test_event_service.py`.

#### Step 4.6 — Risk and safety event REST + Celery jobs (4F)

Implemented in:

- `apps/backend/app/models/risk_score.py` + Alembic `002_risk_scores` —
  durable `risk_scores` history rows (score, level, full JSON payload)
- `apps/backend/app/services/risk_service.py` — extended with
  `persist_risk_score`, `list_risk_history`, and `evaluate_persist_and_publish`;
  `evaluate_and_publish` now accepts `persist` and records history without
  failing publish/cache
- `apps/backend/app/api/v1/risk.py` — real 4F endpoints:
  - `POST /api/v1/risk/{vehicle_id}/compute` — evaluate, cache, publish, persist
  - `POST /api/v1/risk/{vehicle_id}/trigger` — Celery background evaluation
  - `GET /api/v1/risk/history/{vehicle_id}` — Postgres time-series history
  - `GET /api/v1/risk/current/{vehicle_id}` — unchanged Redis cache read
- `apps/backend/app/api/v1/events.py` — real 4F endpoints:
  - `POST /api/v1/events/{vehicle_id}/detect` — 4D detect + 4E persist
  - `POST /api/v1/events/{vehicle_id}/trigger` — Celery background detect
  - `POST /api/v1/events/{vehicle_id}/frame` — append JPEG to clip buffer
  - `POST /api/v1/events/detail/{event_id}/acknowledge` — mark event acknowledged
  - `GET /api/v1/events/{vehicle_id}` — filtered/paginated list with DB fallback
  - `GET /api/v1/events/detail/{event_id}` — single event with XAI + clip URL
  - `GET /api/v1/events/{vehicle_id}/export` — CSV export
- `apps/backend/app/tasks/risk.py` — `run_risk_evaluation` Celery task
- `apps/backend/app/tasks/events.py` — `detect_and_persist_events`,
  `process_safety_tick` (risk + events in one job), and clip retry task

Design decisions: Postgres/Redis/MinIO failures degrade independently — risk
compute still returns even if history persistence fails; event list returns an
empty list + warning when the DB is down. Combined `process_safety_tick` passes
the computed risk score into event detection for richer telemetry snapshots.
Tests live in `apps/backend/tests/test_events_api.py` with updates to
`test_risk_api.py`.

#### Step 4.7 — Live risk and safety events UI (4G)

Implemented in the Next.js frontend at `/safety`:

- `apps/frontend/src/hooks/useFleetRiskWebSocket.ts` — subscribes to
  `/api/v1/fleet/ws/{org_id}` and surfaces live `risk_update` frames
- `apps/frontend/src/components/safety/SafetyDashboard.tsx` — composite risk
  gauge (reuses `RiskGauge`), reasons/overrides panel, persisted history chart,
  JSON demo inputs for compute/detect, and event feed with acknowledge + MinIO
  clip links
- `apps/frontend/src/lib/api.ts` — typed clients for 4F risk/events endpoints
- `apps/frontend/src/lib/types.ts` — `RiskScore`, `SafetyEvent`, and WebSocket
  message contracts
- `apps/frontend/src/app/safety/page.tsx` — Module 4G route

UI capabilities:

| Area | Behavior |
|---|---|
| Live risk | WebSocket updates + `GET /risk/current` fallback |
| History | Line chart from `GET /risk/history/{vehicle_id}` |
| Demo actions | `POST /risk/.../compute` and `POST /events/.../detect` |
| Event feed | `GET /events/{vehicle_id}` with acknowledge via `POST /events/detail/{id}/acknowledge` |
| Clips | `minio://` URLs linked to MinIO console browse path |

Navigation links added from home, dashboard, monitor, road, and maintenance
pages. Phase 4 (Modules 4A–4G) is now complete end-to-end.

---

### Phase 5 — AI Vehicle Assistant (Module 07)
**Timeline: Days 35–50 | No training, RAG setup only**

**What you achieve:** A LangGraph-powered vehicle assistant that answers questions about the car using BMW manual PDFs, live Kuksa telemetry, and maintenance history.

#### Step 5.1 — Build the Knowledge Base

Create `ml/assistant/knowledge_base.py`:

```python
import os
from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

CHROMA_PERSIST_DIR = "./chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, good quality, runs on CPU

def build_knowledge_base(document_paths: list[str]) -> Chroma:
    """
    Ingest PDFs and text files into ChromaDB for RAG retrieval.
    
    Documents to include:
    - BMW owner manual PDF (vehicle-specific)
    - OBD-II diagnostic codes (plain text or PDF)
    - Service interval guidelines
    """
    all_docs = []
    for path in document_paths:
        if path.endswith(".pdf"):
            loader = PyMuPDFLoader(path)
        else:
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(path)
        all_docs.extend(loader.load())

    print(f"Loaded {len(all_docs)} documents")

    # Chunk documents for RAG retrieval
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=64,
        separators=["\n\n", "\n", ". ", " "]
    )
    chunks = splitter.split_documents(all_docs)
    print(f"Created {len(chunks)} chunks")

    # Embed and store in ChromaDB
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"}  # No GPU needed for embeddings
    )
    vectorstore = Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
        collection_name="vehicle_knowledge"
    )
    vectorstore.persist()
    print(f"ChromaDB indexed at {CHROMA_PERSIST_DIR}")
    return vectorstore


if __name__ == "__main__":
    docs = [
        "data/bmw_owner_manual.pdf",
        "data/obd2_codes.txt",
        "data/service_intervals.txt",
    ]
    build_knowledge_base(docs)
```

#### Step 5.2 — LangGraph Assistant Agent

Create `ml/assistant/agent.py`:

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import operator

# ── State definition ──
class AssistantState(TypedDict):
    messages: Annotated[list, operator.add]
    user_query: str
    vehicle_id: str
    intent: str
    retrieved_context: str
    telemetry_context: str
    final_response: str

# ── LLM setup ──
llm = Ollama(model="llama3.2:3b", base_url="http://localhost:11434")

# ── Vectorstore setup ──
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    collection_name="vehicle_knowledge"
)

# ── Nodes ──
def classify_intent_node(state: AssistantState) -> AssistantState:
    query = state["user_query"].lower()
    if any(w in query for w in ["warning", "light", "tire", "pressure", "battery", "engine"]):
        intent = "vehicle_warning"
    elif any(w in query for w in ["oil", "service", "maintenance", "replace", "when"]):
        intent = "maintenance_question"
    elif any(w in query for w in ["p0", "p1", "p2", "code", "fault", "error"]):
        intent = "obd_code"
    else:
        intent = "general_question"
    return {**state, "intent": intent}

async def rag_retriever_node(state: AssistantState) -> AssistantState:
    docs = vectorstore.similarity_search(state["user_query"], k=4)
    context = "\n\n".join([f"[Source: {doc.metadata.get('source', 'Manual')}]\n{doc.page_content}" for doc in docs])
    return {**state, "retrieved_context": context}

async def telemetry_injector_node(state: AssistantState) -> AssistantState:
    """Fetch live Kuksa signals to provide real-time context."""
    from sdv.kuksa.signal_subscriber import get_current_telemetry
    try:
        telemetry = await get_current_telemetry(state["vehicle_id"])
        context = f"""
Current vehicle sensor readings:
- Speed: {telemetry.get('speed_kmh', 'N/A')} km/h
- Tire Pressures: FL={telemetry.get('tire_fl', 'N/A')} PSI, FR={telemetry.get('tire_fr', 'N/A')} PSI, RL={telemetry.get('tire_rl', 'N/A')} PSI, RR={telemetry.get('tire_rr', 'N/A')} PSI
- Battery SoC: {telemetry.get('battery_soc', 'N/A')}%
- Oil Temp: {telemetry.get('oil_temp', 'N/A')}°C
"""
    except Exception:
        context = "Live telemetry unavailable."
    return {**state, "telemetry_context": context}

async def response_generator_node(state: AssistantState) -> AssistantState:
    system_prompt = f"""You are an intelligent automotive assistant for a BMW vehicle.
You have access to the vehicle's owner manual and current sensor data.
Be helpful, precise, and safety-conscious. If the vehicle has a safety-critical issue, always recommend professional service.

Vehicle Manual Context:
{state.get('retrieved_context', '')}

{state.get('telemetry_context', '')}
"""
    response = llm.invoke(f"{system_prompt}\n\nDriver question: {state['user_query']}\n\nAssistant:")
    return {**state, "final_response": response}

def route_intent(state: AssistantState) -> str:
    intent = state["intent"]
    if intent in ("vehicle_warning", "obd_code"):
        return "rag_with_telemetry"
    elif intent == "maintenance_question":
        return "rag_only"
    return "direct_response"

# ── Build graph ──
def build_assistant_graph():
    graph = StateGraph(AssistantState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("rag_retriever", rag_retriever_node)
    graph.add_node("telemetry_injector", telemetry_injector_node)
    graph.add_node("response_generator", response_generator_node)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges("classify_intent", route_intent, {
        "rag_with_telemetry": "rag_retriever",
        "rag_only": "rag_retriever",
        "direct_response": "response_generator"
    })
    graph.add_edge("rag_retriever", "telemetry_injector")
    graph.add_edge("telemetry_injector", "response_generator")
    graph.add_edge("response_generator", END)

    return graph.compile()

assistant_graph = build_assistant_graph()
```

---

### Phase 6 — Fleet Dashboard & XAI (Modules 09 & 10)
**Timeline: Days 45–62 | Frontend-heavy phase**

**What you achieve:** A fully functional Next.js fleet dashboard with real-time WebSocket updates, a driver leaderboard, safety event log, and XAI explanation panel.

#### Step 6.1 — Fleet WebSocket Server

Create `apps/backend/app/api/v1/ws.py`:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
import asyncio
import json

router = APIRouter(tags=["websocket"])
connected_clients: dict[str, set[WebSocket]] = {}

@router.websocket("/api/v1/fleet/ws/{org_id}")
async def fleet_realtime_stream(websocket: WebSocket, org_id: str):
    """
    Real-time fleet updates via Redis pub-sub.
    Subscribes to all vehicle risk channels for this organization.
    Pushes updates to connected browser clients every 5 seconds or on change.
    """
    await websocket.accept()
    connected_clients.setdefault(org_id, set()).add(websocket)

    r = aioredis.from_url("redis://localhost:6379")
    pubsub = r.pubsub()
    await pubsub.psubscribe("risk:*")  # Subscribe to all vehicle channels

    try:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                risk_data = json.loads(message["data"])
                await websocket.send_json({
                    "type": "risk_update",
                    "data": risk_data
                })
    except WebSocketDisconnect:
        connected_clients[org_id].discard(websocket)
    finally:
        await pubsub.unsubscribe("risk:*")
        await r.close()
```

#### Step 6.2 — React Fleet Dashboard Component

Create `apps/frontend/src/hooks/useFleetWebSocket.ts`:

```typescript
import { useEffect, useRef } from "react";
import { useFleetStore } from "@/lib/store";

export function useFleetWebSocket(orgId: string) {
  const ws = useRef<WebSocket | null>(null);
  const { updateVehicleRisk, addAlert } = useFleetStore();

  useEffect(() => {
    ws.current = new WebSocket(`ws://localhost:8000/api/v1/fleet/ws/${orgId}`);

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === "risk_update") {
        updateVehicleRisk(message.data.vehicle_id, message.data);

        // Trigger alert for HIGH/CRITICAL
        if (["HIGH", "CRITICAL"].includes(message.data.risk_level)) {
          addAlert({
            vehicleId: message.data.vehicle_id,
            level: message.data.risk_level,
            reasons: message.data.reasons,
            timestamp: message.data.timestamp,
          });
        }
      }
    };

    ws.current.onerror = (e) => console.error("Fleet WS error:", e);
    ws.current.onclose = () => {
      // Reconnect after 3 seconds
      setTimeout(() => {
        ws.current = new WebSocket(`ws://localhost:8000/api/v1/fleet/ws/${orgId}`);
      }, 3000);
    };

    return () => ws.current?.close();
  }, [orgId]);
}
```

#### Step 6.3 — SHAP Explainer Service

Create `ml/xai/shap_explainer.py`:

```python
import shap
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import io
import base64

def explain_maintenance_prediction(model, feature_row: np.ndarray, feature_names: list[str]) -> dict:
    """
    Generate SHAP explanation for a maintenance prediction.
    Returns top contributing features + base64 waterfall plot.
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(feature_row)

    # Handle binary classification (SHAP returns values for both classes)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # Use positive class values

    # Top 3 feature contributions
    feature_impacts = sorted(
        zip(feature_names, shap_values[0] if shap_values.ndim > 1 else shap_values),
        key=lambda x: abs(x[1]),
        reverse=True
    )
    top_features = [{"feature": f, "impact": round(float(v), 4), "direction": "increases_risk" if v > 0 else "decreases_risk"} 
                    for f, v in feature_impacts[:3]]

    # Generate waterfall plot as base64
    plt.figure(figsize=(10, 4))
    shap.waterfall_plot(shap.Explanation(
        values=shap_values[0] if shap_values.ndim > 1 else shap_values,
        base_values=explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value,
        data=feature_row[0] if feature_row.ndim > 1 else feature_row,
        feature_names=feature_names
    ), show=False)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=120)
    plt.close()
    buf.seek(0)
    plot_b64 = base64.b64encode(buf.read()).decode()

    return {
        "top_features": top_features,
        "shap_plot_base64": plot_b64,
        "prediction_probability": float(model.predict_proba(feature_row.reshape(1, -1))[0][1])
    }
```

---

### Phase 7 — Integration Testing & Demo Preparation
**Timeline: Days 60–75**

**What you achieve:** A fully integrated, demo-ready platform with a recorded demo mode that works without a live car.

#### Step 7.1 — Backend Integration Tests

Create `apps/backend/tests/test_integration.py`:

```python
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()

@pytest.mark.asyncio
async def test_full_driver_analysis_pipeline():
    """Test that a frame can be sent and analyzed end-to-end."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with open("tests/fixtures/test_frame_alert.jpg", "rb") as f:
            response = await client.post(
                "/api/v1/driver/analysis",
                files={"file": ("frame.jpg", f, "image/jpeg")}
            )
    assert response.status_code == 200
    data = response.json()
    assert "alertness_score" in data
    assert data["alertness_score"] >= 0
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert "ear_value" in data

@pytest.mark.asyncio
async def test_risk_api_returns_valid_structure():
    """Test risk endpoint returns expected fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/risk/current/test_vehicle_001")
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert 0 <= data["risk_score"] <= 100

@pytest.mark.asyncio
async def test_assistant_chat_returns_response():
    """Test AI assistant returns a text response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/assistant/chat",
                                     json={"message": "What does the oil pressure warning mean?",
                                           "vehicle_id": "test_vehicle_001"})
    # SSE response — check headers
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
```

#### Step 7.2 — Demo Mode with Pre-recorded Data

Create `ml/demo/demo_runner.py`:

```python
"""
Demo mode: replays a pre-recorded driving video with injected synthetic telemetry.
This allows a full platform demonstration without a live camera or vehicle.
Use a dashcam video or download a driving clip from YouTube with yt-dlp.
"""
import asyncio
import cv2
import json
import httpx
from datetime import datetime, timedelta

DEMO_VIDEO_PATH = "ml/demo/assets/demo_drive.mp4"

async def run_full_demo():
    cap = cv2.VideoCapture(DEMO_VIDEO_PATH)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = 0

    print(f"Starting demo replay at {fps} FPS...")

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop video
                continue

            # Send frame every 3rd frame (10 FPS effective)
            if frame_count % 3 == 0:
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                files = {"file": ("frame.jpg", jpeg.tobytes(), "image/jpeg")}
                try:
                    response = await client.post("/api/v1/driver/analysis", files=files)
                    if response.status_code == 200:
                        result = response.json()
                        print(f"Frame {frame_count}: Risk={result['risk_level']}, "
                              f"Alertness={result['alertness_score']}, "
                              f"EAR={result.get('ear_value', 'N/A')}")
                except Exception as e:
                    print(f"Error processing frame {frame_count}: {e}")

            frame_count += 1
            await asyncio.sleep(1 / fps)

    cap.release()

if __name__ == "__main__":
    asyncio.run(run_full_demo())
```

---

## 9. Training Strategy — Kaggle & Colab Optimized

### 9.1 Training Priority Matrix

| Model | Platform | GPU | Time | Priority |
|-------|----------|-----|------|----------|
| YOLOv8n (Driver: DMD) | Kaggle | P100/T4 | 4–6 hours | **Week 1** |
| YOLOv8m (Road: BDD100K) | Kaggle | P100 | 8–12 hours | **Week 2** |
| YOLO-LSTM Pedestrian Localizer (Caltech) | Kaggle/Colab | T4 | 2–4 hours | **Week 2** |
| XGBoost (AI4I Maintenance) | Local/Colab | CPU | 5 minutes | **Week 2** |
| LSTM Autoencoder (Engine) | Colab | T4 | 30 minutes | **Week 3** |

### 9.2 Kaggle Workflow — Step by Step

**Setting up your Kaggle training environment:**

```
1. Go to kaggle.com → Account → Settings → Enable GPU access
2. Create a new notebook → Notebook settings → GPU T4 x2
3. Add datasets:
   - Click "+ Add Data" on the right panel
   - Search for "DMD Driver Monitoring" or upload your own
   - Search for "BDD100K" — use the version with YOLO format labels
4. Your dataset mounts at /kaggle/input/{dataset-name}/
5. Training outputs go to /kaggle/working/ (5 GB limit)
6. To persist models: output → Download files from the output panel
```

**Kaggle time management:**
- You get 30 GPU hours per week on the free tier
- YOLOv8n on DMD: ~4–6 hours → use 1 weekly session
- YOLOv8m on BDD100K: ~10 hours → use across 2 sessions (save checkpoint after each)
- Always enable "Save model every N epochs" to survive session expiry

**Resuming interrupted training:**

```python
# Resume from checkpoint if session was interrupted
model = YOLO("yolov8m.pt")
results = model.train(
    data="...",
    epochs=50,
    resume=True,  # Add this flag to resume from last checkpoint
)
```

### 9.3 Google Colab Workflow

**Setting up persistent Drive-backed training:**

```python
# Always put this at the top of every Colab notebook
from google.colab import drive
drive.mount('/content/drive')

DRIVE_BASE = '/content/drive/MyDrive/bmw-ai-platform'
DATASET_PATH = f'{DRIVE_BASE}/datasets'
MODEL_SAVE_PATH = f'{DRIVE_BASE}/models'
CHECKPOINT_PATH = f'{DRIVE_BASE}/checkpoints'

import os
for path in [DATASET_PATH, MODEL_SAVE_PATH, CHECKPOINT_PATH]:
    os.makedirs(path, exist_ok=True)

# Install requirements (Colab resets packages each session)
!pip install -q ultralytics langchain chromadb sentence-transformers ucimlrepo xgboost shap
```

**Colab GPU availability tips:**
- Connect at off-peak times (early morning or late night) for T4 access
- If you need consistent GPU, Colab Pro is ~$10/month for better availability
- For models that need < 30 minutes training (XGBoost, small LSTM), CPU is fine

### 9.4 Model Weight Management

After training, manage your models systematically:

```
bmw-ai-platform/
└── ml/
    └── models/
        ├── driver_monitor_v1.pt        ← Download from Kaggle
        ├── road_scene_v1.pt            ← Download from Kaggle  
        ├── best_pedestrian_yololstm.pt ← Download from Colab/Kaggle
        ├── maintenance_xgb_v1.json     ← Train locally (tiny file)
        ├── engine_lstm_v1.pt           ← Train on Colab
        └── shape_predictor_68_face_landmarks.dat  ← Download from dlib.net
```

Add `ml/models/*.pt` to `.gitignore` (too large for Git). Instead, document how to download them in the README and use MLflow as the model registry.

---

## 10. Database Schema

> 🆕 **NEW:** The `users` table below was added because the original schema had `organizations`, `vehicles`, and `drivers`, but no actual login/authentication entity or role model. This table is what backs Phase 8 (Authentication, RBAC & Multi-Tenancy) and Phase 9 (Personalized Dashboards). `drivers` is kept as-is for domain data (license number etc.); a driver who also logs in is linked via `drivers.user_id`.

```sql
-- 🆕 NEW ── Users (authentication + RBAC) ────────────────
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,       -- argon2/bcrypt
    role VARCHAR(20) NOT NULL DEFAULT 'driver', -- super_admin, org_admin, fleet_manager, driver, maintenance_tech
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    driver_id UUID REFERENCES drivers(id),      -- nullable, set when role='driver'
    mfa_secret VARCHAR(64),                     -- TOTP secret, nullable
    mfa_enabled BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_org ON users(org_id, role);

-- 🆕 NEW ── Refresh tokens (rotating, revocable sessions) ─
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 🆕 NEW ── Audit log (who did what, for compliance/EU AI Act traceability)
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    org_id UUID REFERENCES organizations(id),
    action VARCHAR(100) NOT NULL,   -- e.g. EVENT_ACKNOWLEDGED, ROLE_CHANGED, MODEL_PROMOTED
    target_type VARCHAR(50),        -- e.g. safety_events, users, maintenance_predictions
    target_id UUID,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_org ON audit_log(org_id, created_at DESC);

-- ── Organizations ──────────────────────────────────────
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Vehicles ──────────────────────────────────────────
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    vin VARCHAR(17) UNIQUE,
    model VARCHAR(100),
    year INTEGER,
    fuel_type VARCHAR(20),       -- PETROL, DIESEL, ELECTRIC, HYBRID
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Drivers ───────────────────────────────────────────
CREATE TABLE drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    license_number VARCHAR(50),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Vehicle Telemetry (TimescaleDB hypertable) ────────
CREATE TABLE vehicle_telemetry (
    time TIMESTAMPTZ NOT NULL,
    vehicle_id UUID NOT NULL REFERENCES vehicles(id),
    driver_id UUID REFERENCES drivers(id),
    speed_kmh FLOAT,
    rpm INTEGER,
    oil_temp_c FLOAT,
    coolant_temp_c FLOAT,
    battery_soc_pct FLOAT,
    battery_health_pct FLOAT,
    tire_pressure_fl FLOAT,
    tire_pressure_fr FLOAT,
    tire_pressure_rl FLOAT,
    tire_pressure_rr FLOAT,
    brake_pedal_pct FLOAT,
    steering_angle_deg FLOAT,
    longitude FLOAT,
    latitude FLOAT
);

SELECT create_hypertable('vehicle_telemetry', 'time');

-- Create 7-day retention policy (keep last 90 days at full res, compress older)
SELECT add_compression_policy('vehicle_telemetry', INTERVAL '7 days');

-- ── Driver Monitoring Sessions ─────────────────────────
CREATE TABLE driver_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(id),
    driver_id UUID NOT NULL REFERENCES drivers(id),
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    alertness_score_avg FLOAT,
    alertness_score_min FLOAT,
    drowsy_events INTEGER DEFAULT 0,
    yawn_events INTEGER DEFAULT 0,
    phone_events INTEGER DEFAULT 0,
    seatbelt_events INTEGER DEFAULT 0,
    headpose_events INTEGER DEFAULT 0,
    total_frames_analyzed INTEGER DEFAULT 0
);

-- ── Safety Events ──────────────────────────────────────
CREATE TABLE safety_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(id),
    driver_id UUID NOT NULL REFERENCES drivers(id),
    session_id UUID REFERENCES driver_sessions(id),
    event_type VARCHAR(50) NOT NULL,    -- NEAR_COLLISION, DRIVER_ASLEEP, PHONE_USAGE, etc.
    severity VARCHAR(20) NOT NULL,       -- LOW, MEDIUM, HIGH, CRITICAL
    timestamp TIMESTAMPTZ NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    telemetry_snapshot JSONB,           -- Speed, EAR, TTC, etc. at moment of event
    video_clip_url VARCHAR(500),        -- MinIO URL to 30-second video clip
    xai_explanation TEXT,               -- Natural language XAI output
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID REFERENCES drivers(id),
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_safety_events_vehicle ON safety_events(vehicle_id, timestamp DESC);
CREATE INDEX idx_safety_events_severity ON safety_events(severity, acknowledged);

-- ── Maintenance Predictions ────────────────────────────
CREATE TABLE maintenance_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(id),
    component VARCHAR(50) NOT NULL,      -- ENGINE, BRAKES, BATTERY, TIRES, OIL
    health_score FLOAT NOT NULL,         -- 0.0 (critical) to 1.0 (perfect)
    anomaly_score FLOAT,                 -- LSTM autoencoder reconstruction error
    predicted_replacement_date DATE,
    predicted_remaining_km INTEGER,
    confidence FLOAT,                    -- Model confidence 0–1
    shap_explanation JSONB,             -- Top contributing sensor features
    ml_model_version VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_maintenance_vehicle ON maintenance_predictions(vehicle_id, component);

-- ── Driver Behavior Scores (daily rollup) ─────────────
CREATE TABLE driver_scores (
    date DATE NOT NULL,
    driver_id UUID NOT NULL REFERENCES drivers(id),
    safety_score INTEGER NOT NULL,       -- 0 to 100
    harsh_braking_count INTEGER DEFAULT 0,
    rapid_acceleration_count INTEGER DEFAULT 0,
    speeding_events INTEGER DEFAULT 0,
    drowsiness_events INTEGER DEFAULT 0,
    phone_usage_events INTEGER DEFAULT 0,
    no_seatbelt_events INTEGER DEFAULT 0,
    total_distance_km FLOAT DEFAULT 0,
    total_drive_time_minutes INTEGER DEFAULT 0,
    PRIMARY KEY (date, driver_id)
);

-- ── AI Assistant Conversation History ─────────────────
CREATE TABLE assistant_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID REFERENCES vehicles(id),
    driver_id UUID REFERENCES drivers(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    messages JSONB DEFAULT '[]'::jsonb   -- [{role, content, timestamp}]
);
```

---

## 11. API Endpoints Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | JWT login with email + password |
| POST | `/api/v1/auth/register` | Create new user account |
| POST | `/api/v1/auth/refresh` | Refresh JWT access token |
| POST | `/api/v1/auth/logout` | 🆕 NEW — revoke refresh token |
| POST | `/api/v1/auth/verify-email` | 🆕 NEW — confirm email via token |
| POST | `/api/v1/auth/forgot-password` | 🆕 NEW — send password reset email |
| POST | `/api/v1/auth/reset-password` | 🆕 NEW — set new password from reset token |
| POST | `/api/v1/auth/mfa/enable` | 🆕 NEW — enable TOTP MFA |
| POST | `/api/v1/auth/mfa/verify` | 🆕 NEW — verify TOTP code at login |
| GET | `/api/v1/auth/me` | 🆕 NEW — current user profile + role |

### 🆕 NEW — User & Organization Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/orgs/{org_id}/users` | List users in an org (admin only) |
| POST | `/api/v1/orgs/{org_id}/users/invite` | Invite a new user by email |
| PATCH | `/api/v1/users/{user_id}/role` | Change a user's role (admin only) |
| DELETE | `/api/v1/users/{user_id}` | Deactivate a user account |
| GET | `/api/v1/orgs/{org_id}/audit-log` | Paginated audit trail for the org |

### 🆕 NEW — Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/notifications/webhooks` | Register a webhook URL for safety events |
| GET | `/api/v1/notifications/preferences` | Get current user's alert preferences |
| PATCH | `/api/v1/notifications/preferences` | Update email/SMS/push preferences |

### 🆕 NEW — Model & Data Governance

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/models/{name}/versions` | List MLflow model versions and stage |
| POST | `/api/v1/models/{name}/promote` | Promote a model version to production |
| POST | `/api/v1/events/{event_id}/feedback` | Mark a safety event as false positive (feeds retraining) |
| GET | `/api/v1/users/{user_id}/export` | GDPR-style personal data export |
| DELETE | `/api/v1/users/{user_id}/data` | GDPR-style right-to-erasure request |

### Driver Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/driver/analysis` | Analyze single JPEG frame — returns driver state JSON |
| WS | `/api/v1/driver/stream/{vehicle_id}/{session_id}` | Real-time stream — send JPEG bytes, receive analysis JSON |
| GET | `/api/v1/driver/sessions/{vehicle_id}` | List monitoring sessions for a vehicle |
| GET | `/api/v1/driver/sessions/{session_id}/detail` | Full session stats and event timeline |

### Road Understanding

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/road/status` | Cheap Modules 2B–2H readiness metadata; does not run inference |
| POST | `/api/v1/road/analysis?stream_id=...` | Multipart JPEG/PNG → Module 2G analysis; stream ID preserves tracking/temporal state |
| DELETE | `/api/v1/road/streams/{stream_id}` | Reset one retained REST stream session |
| WS | `/api/v1/road/stream/{vehicle_id}` | Send binary JPEG/PNG frames; receive typed Module 2H analysis messages |

### Risk Engine

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/risk/current/{vehicle_id}` | Current composite risk score and reasons |
| GET | `/api/v1/risk/history/{vehicle_id}` | Historical risk scores (time-series) |

### Predictive Maintenance

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/maintenance/{vehicle_id}` | All component predictions for a vehicle |
| GET | `/api/v1/maintenance/{vehicle_id}/{component}` | Specific component prediction + SHAP explanation |
| GET | `/api/v1/maintenance/{vehicle_id}/history` | Historical maintenance records |
| POST | `/api/v1/maintenance/{vehicle_id}/trigger` | Manually trigger new prediction batch |

### AI Assistant

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/assistant/chat` | Chat with AI assistant (SSE streaming response) |
| GET | `/api/v1/assistant/conversations/{vehicle_id}` | Conversation history |

### Fleet Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/fleet/vehicles` | All vehicles in organization |
| GET | `/api/v1/fleet/alerts` | Active unacknowledged alerts across fleet |
| POST | `/api/v1/fleet/alerts/{alert_id}/acknowledge` | Acknowledge a safety alert |
| GET | `/api/v1/fleet/overview` | Fleet summary stats (vehicle count, active alerts, avg risk) |
| WS | `/api/v1/fleet/ws/{org_id}` | Real-time fleet updates (risk changes, new alerts) |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/driver/{driver_id}/weekly` | Weekly driver behavior report |
| GET | `/api/v1/analytics/driver/{driver_id}/trends` | 30-day trend data for charts |
| GET | `/api/v1/analytics/fleet/incidents` | Fleet-wide incident trend data |
| GET | `/api/v1/analytics/fleet/leaderboard` | Driver safety score ranking |

### Safety Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/events/{vehicle_id}` | Paginated safety event log for a vehicle |
| GET | `/api/v1/events/{event_id}` | Single event detail with video URL and XAI |
| GET | `/api/v1/events/{vehicle_id}/export` | Export events as CSV |

### XAI

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/xai/explain` | Get XAI explanation for a detection event |
| GET | `/api/v1/xai/heatmap/{filename}` | Retrieve stored Grad-CAM heatmap image |

### Telemetry & Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/telemetry/{vehicle_id}` | Time-series telemetry (last 24h default) |
| GET | `/api/v1/telemetry/{vehicle_id}/live` | Latest telemetry snapshot |

---

## 12. Deployment Architecture

### Local Development (Single Command)

```bash
# Start all 11 services
docker compose -f infra/docker-compose.yml up -d

# Services available at:
# Frontend Dashboard    → http://localhost:3000
# Backend API          → http://localhost:8000
# API Swagger Docs     → http://localhost:8000/docs
# MLflow Tracking      → http://localhost:5000
# MinIO Admin          → http://localhost:9001
# Grafana Monitoring   → http://localhost:3001
# ChromaDB             → http://localhost:8001
```

### Production Cloud Architecture

```
Internet
    │
    ├── https://bmw-demo.vercel.app          ← Next.js on Vercel (CDN, free)
    │       ↓ API calls
    └── https://bmw-api.onrender.com         ← FastAPI on Render ($7/month)
            ├── Gunicorn + 2x Uvicorn workers
            ├── Celery worker process
            └── Celery beat scheduler
                    ↓
    ├── Render PostgreSQL (TimescaleDB)      ← Primary DB (free 1GB)
    ├── Upstash Redis                        ← pub-sub + cache (free tier)
    ├── Cloudflare R2                        ← Object storage (free 10GB)
    └── ChromaDB (bundled in Render)         ← Vector store
```

### Environment-Specific Configuration

```bash
# Production .env additions
ENVIRONMENT=production
ALLOWED_ORIGINS=["https://bmw-demo.vercel.app"]
DATABASE_URL=postgresql+asyncpg://user:pass@render-host:5432/bmwai_prod
REDIS_URL=rediss://upstash-host:6379  # Note: rediss:// for TLS
SENTRY_DSN=https://your-sentry-dsn  # Error tracking
```

### CI/CD Pipeline

```
Developer pushes to feature branch
    ↓
GitHub Actions CI: pytest + pnpm lint + pnpm build
    ↓ (on merge to main)
GitHub Actions Deploy:
    ├── Build Docker image → push to GitHub Container Registry
    ├── Trigger Render redeploy via webhook
    └── Trigger Vercel redeploy automatically (connected to GitHub)
```

---

## 13. Reference Repositories

| Repository | URL | How You Use It |
|-----------|-----|----------------|
| Ultralytics YOLOv8 | https://github.com/ultralytics/ultralytics | Core detection backbone — read the training docs thoroughly |
| Eclipse Kuksa Databroker | https://github.com/eclipse-kuksa/kuksa-databroker | Run via Docker, subscribe with kuksa-client |
| Eclipse Kuksa Canvas | https://github.com/eclipse-kuksa/kuksa-canvas | HMI vehicle display — add to your dashboard |
| Eclipse Velocitas SDK | https://github.com/eclipse-velocitas/vehicle-app-python-sdk | Vehicle App pattern for structured VSS subscription |
| DMD Dataset | https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset | Primary driver monitoring training data |
| BDD100K Toolkit | https://github.com/bdd100k/bdd100k | Dataset tools, YOLO format conversion scripts |
| Caltech Pedestrian YOLO | https://www.kaggle.com/datasets/abhinavsasikumar/caltech-pedestrian-yolo/data | Temporal pedestrian localization data |
| PyTorch Captum | https://github.com/pytorch/captum | Integrated Gradients XAI — study the tutorials |
| pytorch-grad-cam | https://github.com/jacobgil/pytorch-grad-cam | EigenCAM for YOLOv8 — follow the YOLO example |
| FastAPI Full-Stack Template | https://github.com/tiangolo/full-stack-fastapi-template | Starting scaffold for the backend |
| OpenAssistant OASST1 | https://huggingface.co/datasets/OpenAssistant/oasst1 | LLM fine-tuning data (Phase 2) |
| comma.ai openpilot | https://github.com/commaai/openpilot | Study their camera calibration and safety constraints for inspiration |
| ByteTrack (via supervision) | https://github.com/roboflow/supervision | Object tracking integration — used in road module |

---

## 14. Phase 8 — Authentication, RBAC & Multi-Tenancy 🆕 NEW

**Timeline: Days 63–70 | Foundation for all personalization work below**

This phase closes the biggest gap in the original build: there was no real `users` table, password handling, or role model — only `drivers` and `organizations`. Nothing in Section 15 (personalized dashboards) is possible without this phase.

**Scope (8A–8F):**

- **8A — Users table & password handling.** Implement the `users`, `refresh_tokens`, and `audit_log` tables from Section 10. Hash passwords with `argon2` (preferred) or `bcrypt`. Never store plaintext or reversible passwords.
- **8B — JWT issuance & rotation.** Short-lived access token (15 min), long-lived refresh token (7–30 days) stored **hashed** in `refresh_tokens`. Rotate the refresh token on every use; revoke on logout or password change.
- **8C — Role model.** Five roles: `super_admin`, `org_admin`, `fleet_manager`, `driver`, `maintenance_tech`. Enforce with a FastAPI dependency, e.g. `Depends(require_role("fleet_manager", "org_admin"))`, applied per-route — never trust a role claim without re-validating server-side on every request.
- **8D — Row-level scoping.** Every query that touches `vehicles`, `safety_events`, `driver_scores`, etc. must filter by `org_id` (and by `driver_id` when the caller's role is `driver`). This is what makes the same API endpoints return different, personalized data per user.
- **8E — Registration & onboarding flow.** Register → email verification → create/join an organization → (if fleet manager) register vehicles → (if driver) get linked to a vehicle. Land the new user on an empty-state dashboard, not a blank page.
- **8F — Optional MFA & OAuth.** TOTP-based MFA (`pyotp` + QR code) and/or Google OAuth login. Both are cheap to add once 8A–8D exist and meaningfully raise the perceived security maturity of the project.

**Key backend snippet — role-gated route:**

```python
# app/core/deps.py
from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user

def require_role(*allowed_roles: str):
    def checker(user = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user
    return checker

# app/api/v1/fleet.py
@router.get("/fleet/vehicles")
async def list_fleet_vehicles(
    user = Depends(require_role("fleet_manager", "org_admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Vehicle).where(Vehicle.org_id == user.org_id)
    )
    return result.scalars().all()
```

**Exit criteria:** a user can register, verify their email, log in, receive a role-scoped JWT, and every existing API endpoint from Section 11 returns only their org's (or their own) data.

---

## 15. Phase 9 — Personalized Role-Based Dashboards 🆕 NEW

**Timeline: Days 71–82 | Frontend-heavy, depends on Phase 8**

One Next.js app, role-aware routing — not three separate frontends.

**Scope (9A–9D):**

- **9A — Driver dashboard** (`app/(driver)/dashboard`): own safety score trend, own vehicle's live telemetry (WebSocket, scoped by `driver_id`), own safety event history, AI assistant chat scoped to their vehicle's manual.
- **9B — Fleet manager dashboard** (`app/(fleet)/dashboard`): existing Module 09 fleet view, now gated to `org_id`, plus a driver leaderboard and incident heatmap.
- **9C — Admin dashboard** (`app/(admin)/dashboard`): user invites and role management, audit log viewer, system health (Celery queue depth, model versions from MLflow via the new `/models` endpoints).
- **9D — Shared design system.** One component library, one theme, role-specific layouts composed from shared primitives (`<StatCard>`, `<TelemetryChart>`, `<EventList>`) so the three dashboards don't diverge into three codebases.

**Route-to-role mapping:**

```
middleware.ts
  → decode JWT role claim
  → role === 'driver'         → /driver/dashboard
  → role === 'fleet_manager'  → /fleet/dashboard
  → role in ('org_admin','super_admin') → /admin/dashboard
```

**Exit criteria:** three visually distinct, data-scoped dashboards live behind one login, sharing one component library and one set of backend routes.

---

## 16. Phase 10 — Production Hardening & Observability 🆕 NEW

**Timeline: Days 83–92**

**Scope (10A–10E):**

- **10A — Testing.** pytest coverage on auth and risk-scoring logic; Playwright/Cypress e2e covering register → login → role-scoped dashboard; k6/Locust load test on the WebSocket fan-out.
- **10B — Observability.** Wire up the `SENTRY_DSN` env var that already exists in Section 12 but was never connected. Structured JSON logging. Prometheus + Grafana panels for API latency, Celery queue depth, model inference time.
- **10C — Security.** Rate limit `/api/v1/auth/login` (e.g. `slowapi`, 5 attempts/minute/IP). Validate all uploaded frames/files for size and MIME type. Move secrets out of `.env` into a vault (Doppler, AWS Secrets Manager, or Render's secret files) for production.
- **10D — API hardening.** Pagination on every list endpoint, idempotency keys on POST routes that create resources, a consistent error envelope (`{"error": {"code", "message"}}`), API version discipline (`/api/v1/...` stays stable; breaking changes go to `/api/v2/...`).
- **10E — Audit logging.** Every role change, event acknowledgment, and model promotion writes a row to `audit_log` (Section 10) — this both satisfies the EU AI Act traceability requirement already referenced in Section 1 and is genuinely useful for debugging.

**Exit criteria:** Sentry captures a deliberately-triggered error end-to-end; `/auth/login` returns 429 after 5 failed attempts; `EXPLAIN ANALYZE` on the top 10 dashboard queries shows no sequential scans on tables >10k rows.

---

## 17. Phase 11 — ML/AI Maturity & Governance 🆕 NEW

**Timeline: Days 93–100**

**Scope (11A–11D):**

- **11A — Model registry discipline.** Actually use MLflow's `staging` → `production` stage transitions (already available in your stack, previously only used for experiment tracking) — gate promotion behind an eval-metric check via `POST /api/v1/models/{name}/promote`.
- **11B — Drift detection.** Compare live telemetry feature distributions against the training distribution (e.g. population stability index on speed, EAR, braking frequency); alert when drift crosses a threshold.
- **11C — Feedback loop.** Use the new `POST /api/v1/events/{event_id}/feedback` endpoint so drivers/managers can flag false positives; periodically export flagged events into a retraining dataset.
- **11D — LLM guardrails & RAG evaluation.** Input/output filtering on the AI Vehicle Assistant (refuse out-of-scope or unsafe advice); build a small RAGAS-based eval set to measure retrieval faithfulness instead of trusting the RAG pipeline blindly.

**Exit criteria:** a model version cannot reach `production` stage without passing an automated eval check; the assistant has a documented eval score, not just a vibe check.

---

## 18. Phase 12 — Notifications & Product Polish 🆕 NEW

**Timeline: Days 101–108**

**Scope (12A–12D):**

- **12A — Alerting.** Email (Resend) and optionally SMS (Twilio) for `CRITICAL` severity safety events, using the new `notifications/preferences` and `notifications/webhooks` endpoints.
- **12B — PWA support.** Installable driver dashboard for mobile, using Next.js PWA tooling.
- **12C — Accessibility & theming.** Keyboard navigation, ARIA labels, dark mode, WCAG-AA color contrast — ties directly into the EU AI Act framing already in Section 1.
- **12D — Reporting.** PDF weekly driver report (extends the existing CSV export endpoint) using the same data as `/analytics/driver/{id}/weekly`.

**Exit criteria:** a CRITICAL safety event triggers an email within seconds; the driver dashboard installs as a PWA on a phone; a Lighthouse accessibility audit scores 90+.

---

## 19. Advanced Industry-Level Features 🆕 NEW

These go beyond "complete product" into "distinctive, automotive-grade platform." Pick based on time budget — not all are required, but each is a strong differentiator for a BMW-facing portfolio.

### 19.1 Automotive compliance & cybersecurity
- **ISO 21434 TARA document** — a written threat & risk assessment for your own system (e.g. spoofed Kuksa signals, malicious CV pipeline input) stored in the repo.
- **UNECE R155/R156-style signed OTA model updates** — new model weights are cryptographically signed; the loader verifies the signature before use.
- **ISO 26262-inspired severity classification** for safety events, with documented fail-safe behavior when a sensor feed drops.

### 19.2 Edge AI & OTA deployment
- ONNX/TensorRT export + INT8 quantization for on-device inference (simulate a Jetson-class edge target).
- Edge/cloud split: lightweight on-device model, escalate to cloud LLM/XAI only above a risk threshold.
- OTA rollout dashboard: push a model version to a fleet %, monitor error rate, roll back on regression (canary-style).

### 19.3 Event-driven data backbone
- Kafka or Redpanda replacing direct Redis pub-sub for telemetry ingestion.
- Feature store (Feast) so training and real-time inference read the same computed features — eliminates training/serving skew.
- Event replay: re-run any historical drive through the risk engine for debugging or regression testing.

### 19.4 Advanced ML/AI
- Sensor fusion: camera + simulated radar/LiDAR (nuScenes/KITTI) combined via a Kalman filter.
- Multi-agent LangGraph: supervisor graph coordinating specialized maintenance/safety/route agents instead of one flat RAG chain.
- Federated learning simulation (FedAvg across a few simulated vehicle clients) for privacy-preserving driver-behavior training.
- Digital twin: live 2D/3D vehicle state view driven by telemetry, pairing with Eclipse Kuksa Canvas.

### 19.5 Infrastructure & DevOps
- Kubernetes (k3d/kind for local, Helm charts) instead of pure docker-compose.
- Terraform for cloud deployment instead of manual setup.
- Canary/blue-green deploys for backend and model releases.
- Chaos testing: deliberately kill Redis/Postgres mid-demo and confirm graceful degradation.

### 19.6 Business-layer / SaaS features
- Stripe test-mode billing with per-vehicle or per-seat tiers.
- Insurance telematics scoring: turn `driver_scores` into a usage-based-insurance premium calculator.
- Carbon/efficiency tracking for EVs: battery health + driving style → efficiency score.
- Webhook system so external systems can subscribe to safety events.
- API gateway with per-tenant rate limiting.
- GDPR-style data export/erasure (already added as endpoints in Section 11).

---

## 20. Phase 13 — Performance & Optimization Pass 🆕 NEW

**Timeline: Days 109–116 | Run this last, against real bottlenecks, not guesses**

**Scope by module:**

| Module | Optimization | Why |
|---|---|---|
| 01 — Driver Monitoring | Adaptive frame sampling (full inference every 3–5 frames, optical-flow interpolation between) | Cuts CV compute 60–70% |
| 01 — Driver Monitoring | ONNX/INT8 quantization of YOLOv8n and landmark models | 2–4x CPU inference speedup |
| 01 — Driver Monitoring | Gate MediaPipe/Dlib behind a cheap face-presence check | Avoids running the full 468-point mesh on empty frames |
| 02 — Road Understanding | ROI cropping + periodic full-frame re-segmentation | Avoids segmenting the full frame every call |
| 02 — Road Understanding | Run Module 01 and 02 as independent async workers | Removes unnecessary sequential blocking |
| 03 — Predictive Maintenance | Batch telemetry writes (1–5s buffer) instead of row-by-row inserts | Single biggest DB win available |
| 03 — Predictive Maintenance | TimescaleDB continuous aggregates for hourly/daily rollups | Avoids scanning raw rows on every dashboard load |
| 03 — Predictive Maintenance | LTTB downsampling before sending chart data to the frontend | Charts don't need millisecond resolution |
| 04 — Risk Engine | Redis cache (short TTL) for latest risk score per vehicle | Cuts repeated Postgres reads |
| 04 — Risk Engine | Throttle WebSocket fan-out to ~2–4 updates/sec | Matches human perception, cuts bandwidth at fleet scale |
| 04 — Risk Engine | Run hard-override rules (4B) before weighted scoring | Cheap checks gate expensive computation |
| 04 — Risk Engine | Partial index `WHERE acknowledged = FALSE` on `safety_events` | Matches the dashboard's actual query pattern |
| 05 — AI Assistant | Persist embeddings instead of re-embedding the knowledge base on every deploy | Removes redundant compute |
| 05 — AI Assistant | Semantic cache (embedding-similarity, not exact match) for common questions | Cuts Ollama load |
| 05 — AI Assistant | Small classifier model routes queries before invoking the full LLM | Avoids using the biggest model for routing |
| 06 — Fleet Dashboard | Virtualized lists (`react-window`) for 100+ vehicle views | Avoids rendering every row |
| 06 — Fleet Dashboard | `React.memo`/`useMemo` on chart components | One WebSocket tick shouldn't re-render every chart |
| 06 — Fleet Dashboard | WebSocket channel filtering by `org_id`/role (closes the gap the original spec flagged as "deferred until fleet auth lands" — now that Phase 8 exists, implement it) | Avoids broadcasting every event to every socket |
| 07 — Testing/Demo | Load test the WebSocket fan-out with k6/Locust | Finds the real bottleneck before optimizing blindly |
| 07 — Testing/Demo | Profile the CV pipeline with `py-spy`/`cProfile` | Confirms which stage is actually slow |

**Cross-cutting (apply once, benefits everything):**

- Gzip/brotli response compression on the API.
- HTTP caching headers on read-mostly endpoints (`/analytics/fleet/leaderboard`).
- Tuned async SQLAlchemy connection pool (`pool_size`, `max_overflow`).
- Read replica for analytics queries, separate from the primary write path.
- Celery queues split by task weight (`ml_tasks` vs `notifications`) so slow jobs don't block fast ones.
- `next/dynamic` route-based code splitting so the driver dashboard doesn't ship fleet-manager bundle code.
- `next/image` for video-clip thumbnails instead of full-resolution frames.
- CDN in front of MinIO/R2 for safety-event video clips.
- Horizontal autoscaling on inference workers specifically (the actual bottleneck), not the API server.

**Exit criteria:** p95 dashboard load under 300ms with 500 simulated concurrent connections; `EXPLAIN ANALYZE` on all dashboard queries shows index usage; CV pipeline throughput measured and documented, not assumed.

---

## Quick Start Checklist

```
Setup (Days 1–5)
□ Install Python 3.11+, Node.js 20, Docker Desktop
□ Set Docker Desktop memory to 8GB minimum
□ Clone repo: git clone https://github.com/YOUR_USERNAME/bmw-ai-platform
□ Copy .env.example to .env and fill in values
□ Run: docker compose -f infra/docker-compose.yml up -d
□ Verify all 11 services are running: docker compose ps
□ Run: alembic upgrade head (creates all tables)
□ Pull Ollama LLM: docker exec ollama ollama pull llama3.2:3b

Model Downloads (Days 3–4)
□ Download Dlib landmark predictor: wget dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
□ Extract to ml/models/

Kaggle Training Setup (Days 3–5, run while coding)
□ Create Kaggle account, enable GPU access (Account Settings)
□ Upload DMD RGB subset to Kaggle as private dataset
□ Upload BDD100K segmentation images and train-ID masks to Kaggle
□ Create Kaggle notebook for YOLOv8n driver training (notebooks/train_driver_yolo_kaggle.py)
□ Train DeepLabV3+ road segmentation (notebooks/train_road_seg.ipynb)
□ Download trained weights to ml/models/ after training completes

Knowledge Base (Day 5)
□ Place BMW owner manual PDF in data/
□ Download OBD-II codes database from github.com/myvin/obd2codes
□ Run: python ml/assistant/knowledge_base.py

Development
□ cd apps/backend && uvicorn app.main:app --reload --port 8000
□ cd apps/frontend && pnpm install && pnpm dev
□ Open http://localhost:3000 — you should see the dashboard
□ Open http://localhost:8000/docs — test API endpoints
□ Test driver monitoring: POST /api/v1/driver/analysis with a test JPEG

Demo Preparation
□ Download or record a driving video clip for demo mode
□ Place at ml/demo/assets/demo_drive.mp4
□ Run: python ml/demo/demo_runner.py (verify pipeline processes frames)
□ Write BMW-facing README with architecture diagram and demo GIF
□ Deploy to Render + Vercel for live demo link
```

---

*Built to demonstrate production-grade automotive AI engineering aligned with BMW Group Software's strategic direction: Software-Defined Vehicle (SDV), ADAS, Predictive Analytics, and Responsible AI under EU AI Act compliance.*

*All datasets used are freely available for academic and portfolio use. All training designed for zero-cost execution on Kaggle Free + Google Colab Free tiers.*

---

> 🆕 **Phases 0–7 above are the original build. Phases 8–13 (Sections 14–20) are the industry-level upgrade layer added in this revision — authentication/RBAC, personalized dashboards, production hardening, ML governance, notifications, advanced platform features, and a dedicated performance pass. Suggested build order: Phase 8 → 9 → 10 → 11 → 12 → 13, picking Section 19 items opportunistically based on time budget.**
