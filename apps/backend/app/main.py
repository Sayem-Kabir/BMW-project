"""BMW AI Platform FastAPI entrypoint."""

from __future__ import annotations

# Ensure monorepo roots are importable when started via `uvicorn` from apps/backend
import sys
from pathlib import Path

_main = Path(__file__).resolve()
_BACKEND_ROOT = _main.parents[1]
_REPO_ROOT = _BACKEND_ROOT
for _idx in (3, 2):
    try:
        _candidate = _main.parents[_idx]
    except IndexError:
        continue
    if (_candidate / "apps").is_dir() and (_candidate / "ml").is_dir():
        _REPO_ROOT = _candidate
        break
for _p in (_REPO_ROOT, _BACKEND_ROOT):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import ALL_ROUTERS
from app.core.config import settings
from app.core.database import Base, engine
from app.core.errors import install_error_handlers
from app.core.logging_config import configure_logging
from app.core.redis import close_redis

# Import models so Base.metadata is populated for create_all
import app.models  # noqa: F401

configure_logging(
    json_logs=bool(settings.log_json)
    or settings.environment.lower() in {"production", "prod", "staging"},
    level="INFO",
)
logger = logging.getLogger(__name__)


def _init_sentry() -> None:
    dsn = (settings.sentry_dsn or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=settings.environment,
            traces_sample_rate=0.1 if settings.environment.lower() in {"production", "prod"} else 0.0,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
        )
        logger.info("Sentry initialized")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sentry init failed: %s", exc)


def _cors_origins() -> list[str]:
    defaults = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
    ]
    extra = [item.strip() for item in (settings.cors_origins or "").split(",") if item.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for origin in defaults + extra:
        if origin not in seen:
            seen.add(origin)
            out.append(origin)
    return out


def _warn_insecure_production_settings() -> None:
    env = settings.environment.lower()
    if env not in {"production", "prod", "staging"}:
        return
    weak = "change-this-to-a-real-random-string-in-production"
    if not settings.secret_key or settings.secret_key == weak or len(settings.secret_key) < 24:
        logger.warning(
            "INSECURE SECRET_KEY in %s — set a long random SECRET_KEY before public deploy",
            settings.environment,
        )
    if not (settings.cors_origins or "").strip():
        logger.warning(
            "CORS_ORIGINS is empty in %s — set your Vercel origin for browser access",
            settings.environment,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BMW AI Platform...")
    _warn_insecure_production_settings()
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


_init_sentry()

app = FastAPI(
    title="BMW AI Automotive Intelligence Platform",
    description="Production-grade automotive AI: ADAS, SDV, Predictive Maintenance, XAI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Spec Phase 13 — Gzip + Brotli response compression
app.add_middleware(GZipMiddleware, minimum_size=500)
try:
    from starlette.middleware.brotli import BrotliMiddleware

    app.add_middleware(BrotliMiddleware, minimum_size=500, quality=4)
except Exception:  # noqa: BLE001
    logger.info("Brotli middleware unavailable — gzip only")

install_error_handlers(app)

# Module 8F / Phase 10B — Prometheus metrics at /metrics
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/metrics", "/health", "/ready"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
except Exception as exc:  # noqa: BLE001
    logger.warning("Prometheus instrumentator unavailable: %s", exc)

for router in ALL_ROUTERS:
    app.include_router(router)


@app.get("/health")
async def health_check():
    payload = {
        "status": "healthy",
        "version": "1.0.0",
        "phase": "13",
        "environment": getattr(settings, "environment", "development"),
    }
    try:
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
    try:
        from app.core.metrics_custom import refresh_celery_queue_depth

        payload["celery_queues"] = await refresh_celery_queue_depth()
    except Exception:  # noqa: BLE001
        payload["celery_queues"] = {}
    payload["sentry"] = "configured" if (settings.sentry_dsn or "").strip() else "disabled"
    return payload


@app.get("/ready")
async def readiness_check():
    """Render-style readiness probe — DB must accept a trivial query."""
    db_ok = False
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Readiness DB check failed: %s", exc)
    payload = {
        "status": "ready" if db_ok else "not_ready",
        "database": "ok" if db_ok else "unavailable",
        "environment": settings.environment,
        "phase": "10",
    }
    if not db_ok:
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get("/api/v1/debug/sentry-test")
async def sentry_test():
    """Deliberate error for Phase 10 exit criteria (Sentry capture). Disabled without DSN."""
    if not (settings.sentry_dsn or "").strip():
        return {"ok": False, "reason": "SENTRY_DSN not set"}
    raise RuntimeError("Phase 10 deliberate Sentry test error")


@app.get("/")
async def root():
    return {
        "message": "BMW AI Automotive Intelligence Platform",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "api": "/api/v1",
        "demo": "/api/v1/demo/status",
        "phase": "10",
        "metrics": "/metrics",
    }


logger.info("FastAPI application initialized")
