from uuid import UUID

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/maintenance", tags=["Predictive Maintenance"])


@router.get("/{vehicle_id}/history")
async def maintenance_history(vehicle_id: UUID):
    return {"vehicle_id": str(vehicle_id), "history": [], "phase": "scaffold"}


@router.post("/{vehicle_id}/trigger")
async def trigger_prediction(vehicle_id: UUID):
    return {
        "vehicle_id": str(vehicle_id),
        "status": "queued",
        "message": "Celery maintenance task scaffold — real models in Phase 3",
    }


@router.get("/{vehicle_id}")
async def list_predictions(vehicle_id: UUID):
    return {
        "vehicle_id": str(vehicle_id),
        "predictions": [],
        "phase": "scaffold",
        "message": "Maintenance models ship in Phase 3",
    }


@router.get("/{vehicle_id}/{component}")
async def component_prediction(vehicle_id: UUID, component: str):
    return {
        "vehicle_id": str(vehicle_id),
        "component": component.upper(),
        "health_score": 1.0,
        "phase": "scaffold",
    }
