from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import ALL_ROUTERS
from app.core.config import settings
from app.core.database import Base, engine
from app.core.redis import close_redis

# Import models so Base.metadata is populated for create_all
import app.models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BMW AI Platform...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")
    except Exception as exc:  # noqa: BLE001 — allow boot without DB for local/CI smoke tests
        logger.warning("Database unavailable at startup (%s). Continuing without create_all.", exc)
    yield
    logger.info("Shutting down...")
    try:
        await close_redis()
    except asyncio.CancelledError:
        logger.info("Shutdown interrupted while closing Redis")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis shutdown error: %s", exc)
    try:
        await engine.dispose()
    except asyncio.CancelledError:
        logger.info("Shutdown interrupted while closing database pool")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database shutdown error: %s", exc)


app = FastAPI(
    title="BMW AI Automotive Intelligence Platform",
    description="Production-grade automotive AI: ADAS, SDV, Predictive Maintenance, XAI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in ALL_ROUTERS:
    app.include_router(router)


@app.get("/health")
async def health_check():
    payload = {
        "status": "healthy",
        "version": "1.0.0",
        "phase": "1",
        "environment": getattr(settings, "environment", "development"),
    }
    try:
        # Optional — keep /health cheap if ML path is unavailable in CI
        import sys
        from pathlib import Path

        repo = Path(__file__).resolve().parents[3]
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
        from ml.common.gpu_detector import get_inference_device

        payload["inference_device"] = get_inference_device()
    except Exception:  # noqa: BLE001
        payload["inference_device"] = "unknown"
    try:
        from app.core import redis as redis_ops

        payload["redis"] = "ok" if await redis_ops.ping_redis() else "unavailable"
    except Exception:  # noqa: BLE001
        payload["redis"] = "unavailable"
    return payload


@app.get("/")
async def root():
    return {
        "message": "BMW AI Automotive Intelligence Platform",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
        "phase": "1 — driver monitoring",
    }


logger.info("FastAPI application initialized")
