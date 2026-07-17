from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.events.post_process_event")
def post_process_event(event_id: str) -> dict:
    """Background processing for safety events (Phase 4)."""
    return {
        "status": "skipped",
        "event_id": event_id,
        "phase": "scaffold",
    }
