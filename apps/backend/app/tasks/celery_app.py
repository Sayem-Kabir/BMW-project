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
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        # Placeholder schedules — real jobs land in later phases
        "hourly-driver-scoring": {
            "task": "app.tasks.scoring.update_driver_scores",
            "schedule": 3600.0,
        },
    },
)
