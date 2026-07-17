from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.common import ChatRequest

router = APIRouter(prefix="/api/v1/assistant", tags=["AI Assistant"])


@router.post("/chat")
async def chat(body: ChatRequest):
    """SSE streaming scaffold — LangGraph agent lands in Phase 5."""

    async def event_stream():
        reply = (
            f"Phase 0 scaffold: received '{body.message}'. "
            "Full RAG + live Kuksa context arrives in Phase 5."
        )
        yield f"data: {reply}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations/{vehicle_id}")
async def conversations(vehicle_id: UUID):
    return {"vehicle_id": str(vehicle_id), "conversations": [], "phase": "scaffold"}
