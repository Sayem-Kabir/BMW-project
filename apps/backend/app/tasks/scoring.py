from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.scoring.update_driver_scores")
def update_driver_scores() -> dict:
    """Periodic driver safety score rollup (implemented in Phase 4/6)."""
    return {"status": "skipped", "phase": "scaffold", "message": "Scoring not implemented yet"}
