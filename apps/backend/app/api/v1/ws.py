from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])


@router.websocket("/api/v1/fleet/ws/{org_id}")
async def fleet_ws(websocket: WebSocket, org_id: UUID):
    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "org_id": str(org_id),
                "message": "Fleet WebSocket scaffold ready. Live risk pub-sub ships in Phase 4/6.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        while True:
            msg = await websocket.receive_text()
            await websocket.send_json(
                {
                    "type": "pong",
                    "echo": msg,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
    except WebSocketDisconnect:
        return
