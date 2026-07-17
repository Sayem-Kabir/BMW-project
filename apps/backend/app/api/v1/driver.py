from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.schemas.common import DriverAnalysisResponse, DriverSessionResponse, HeadPose

router = APIRouter(prefix="/api/v1/driver", tags=["Driver Monitoring"])


@router.post("/analysis", response_model=DriverAnalysisResponse)
async def analyze_frame():
    """Analyze a single JPEG frame. Full CV pipeline lands in Phase 1."""
    return DriverAnalysisResponse(
        alertness_score=100,
        risk_level="LOW",
        ear_value=0.30,
        mar_value=0.20,
        yawn_count=0,
        head_pose=HeadPose(),
        phone_detected=False,
        seatbelt_worn=True,
        consecutive_drowsy_frames=0,
    )


@router.get("/sessions/{vehicle_id}")
async def list_sessions(vehicle_id: UUID):
    return {"vehicle_id": str(vehicle_id), "sessions": [], "phase": "scaffold"}


@router.get("/sessions/{session_id}/detail")
async def session_detail(session_id: UUID):
    return {
        "session_id": str(session_id),
        "detail": None,
        "message": "No sessions yet — driver monitoring arrives in Phase 1",
        "phase": "scaffold",
    }


@router.websocket("/stream/{vehicle_id}/{session_id}")
async def driver_stream(websocket: WebSocket, vehicle_id: UUID, session_id: UUID):
    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "type": "ready",
                "vehicle_id": str(vehicle_id),
                "session_id": str(session_id),
                "message": "WebSocket scaffold ready. Frame analysis ships in Phase 1.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        while True:
            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                break
            await websocket.send_json(
                {
                    "type": "analysis",
                    "payload": DriverAnalysisResponse(
                        alertness_score=100,
                        risk_level="LOW",
                        ear_value=0.30,
                        mar_value=0.20,
                        head_pose=HeadPose(),
                    ).model_dump(),
                }
            )
    except WebSocketDisconnect:
        return
