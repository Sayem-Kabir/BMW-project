# Architecture Overview

The BMW AI Platform follows a layered architecture:

1. **Input** — Camera feeds, Eclipse Kuksa VSS signals, OBD-II
2. **CV workers** — YOLOv8, MediaPipe, Dlib (Phases 1–2)
3. **Risk engine** — Weighted scoring + Redis pub-sub (Phase 4)
4. **FastAPI** — REST + WebSocket + SSE
5. **Data** — PostgreSQL/TimescaleDB, Redis, ChromaDB, MinIO
6. **Dashboard** — Next.js 14 (Phase 6)
7. **AI assistant** — LangGraph + RAG + Ollama (Phase 5)
8. **XAI** — Grad-CAM + SHAP (Phase 6)

See `BMW_AI_Platform_Complete_Spec.md` for the full design.
