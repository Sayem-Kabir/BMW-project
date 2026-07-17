from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.event import SafetyEvent
from app.schemas.common import SafetyEventResponse

router = APIRouter(prefix="/api/v1/events", tags=["Safety Events"])


@router.get("/{vehicle_id}", response_model=list[SafetyEventResponse])
async def list_events(vehicle_id: UUID, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(SafetyEvent)
        .where(SafetyEvent.vehicle_id == vehicle_id)
        .order_by(SafetyEvent.timestamp.desc())
        .limit(100)
    )
    return list(result.scalars().all())


@router.get("/detail/{event_id}", response_model=SafetyEventResponse | None)
async def event_detail(event_id: UUID, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(SafetyEvent).where(SafetyEvent.id == event_id))
    return result.scalar_one_or_none()


@router.get("/{vehicle_id}/export")
async def export_events(vehicle_id: UUID, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(SafetyEvent).where(SafetyEvent.vehicle_id == vehicle_id)
    )
    events = result.scalars().all()
    lines = ["event_id,event_type,severity,timestamp"]
    for e in events:
        lines.append(f"{e.id},{e.event_type},{e.severity},{e.timestamp.isoformat()}")
    return PlainTextResponse("\n".join(lines), media_type="text/csv")
