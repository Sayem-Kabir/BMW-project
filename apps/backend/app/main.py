from contextlib import asynccontextmanager
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
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis shutdown error: %s", exc)
    await engine.dispose()


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
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in ALL_ROUTERS:
    app.include_router(router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "phase": "1",
        "environment": getattr(settings, "environment", "development"),
    }


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
