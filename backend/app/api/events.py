from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.events import EventsResponse
from app.db.session import get_session
from app.services.schedule_service import list_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventsResponse)
async def get_events(
    user_id: UUID = Query(...),
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    session: AsyncSession = Depends(get_session),
) -> EventsResponse:
    events = await list_events(session, user_id=user_id, from_=from_, to=to)
    return EventsResponse(events=events)
