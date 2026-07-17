from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter

from app.schemas.common import RiskScoreResponse

router = APIRouter(prefix="/api/v1/risk", tags=["Risk Engine"])


@router.get("/current/{vehicle_id}", response_model=RiskScoreResponse)
async def current_risk(vehicle_id: UUID):
    return RiskScoreResponse(
        vehicle_id=vehicle_id,
        score=0,
        level="LOW",
        factors=[],
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/history/{vehicle_id}")
async def risk_history(vehicle_id: UUID):
    return {
        "vehicle_id": str(vehicle_id),
        "history": [],
        "phase": "scaffold",
        "message": "Risk engine aggregation ships in Phase 4",
    }
