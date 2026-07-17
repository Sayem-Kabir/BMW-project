from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.maintenance.run_batch_predictions")
def run_batch_predictions(vehicle_id: str | None = None) -> dict:
    """Batch maintenance predictions (Phase 3)."""
    return {
        "status": "skipped",
        "vehicle_id": vehicle_id,
        "phase": "scaffold",
    }
