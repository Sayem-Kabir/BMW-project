from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "bmw_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.scoring",
        "app.tasks.events",
        "app.tasks.maintenance",
        "app.tasks.risk",
        "app.tasks.notifications",
    ],
)

# Spec Phase 13 — split heavy ML work from fast notification delivery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_default_queue="default",
    task_routes={
        "app.tasks.maintenance.*": {"queue": "ml_tasks"},
        "app.tasks.risk.*": {"queue": "ml_tasks"},
        "app.tasks.scoring.*": {"queue": "ml_tasks"},
        "app.tasks.events.detect_and_persist_events": {"queue": "ml_tasks"},
        "app.tasks.events.process_safety_tick": {"queue": "ml_tasks"},
        "app.tasks.notifications.*": {"queue": "notifications"},
        "app.tasks.events.post_process_event": {"queue": "notifications"},
    },
    beat_schedule={
        "hourly-driver-scoring": {
            "task": "app.tasks.scoring.update_driver_scores",
            "schedule": 3600.0,
            "options": {"queue": "ml_tasks"},
        },
    },
)
