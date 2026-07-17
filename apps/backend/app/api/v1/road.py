from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.common import RoadAnalysisResponse

router = APIRouter(prefix="/api/v1/road", tags=["Road Understanding"])


@router.post("/analysis", response_model=RoadAnalysisResponse)
async def analyze_road_frame():
    return RoadAnalysisResponse(
        objects=[],
        frame_id=0,
        timestamp=datetime.now(timezone.utc),
    )


@router.websocket("/stream/{vehicle_id}")
async def road_stream(websocket: WebSocket, vehicle_id: UUID):
    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "type": "ready",
                "vehicle_id": str(vehicle_id),
                "message": "Road stream scaffold ready. YOLO pipeline ships in Phase 2.",
            }
        )
        while True:
            await websocket.receive()
            await websocket.send_json(
                RoadAnalysisResponse(
                    objects=[],
                    frame_id=0,
                    timestamp=datetime.now(timezone.utc),
                ).model_dump(by_alias=True)
            )
    except WebSocketDisconnect:
        return
