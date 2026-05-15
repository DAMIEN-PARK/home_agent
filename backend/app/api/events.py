from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.schedule_service import list_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def get_events(
    user_id: UUID = Query(...),
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    events = await list_events(session, user_id=user_id, from_=from_, to=to)
    return {
        "events": [
            {
                "id": str(e.id),
                "title": e.title,
                "source": e.source,
                "start_at": e.start_at.isoformat(),
                "end_at": e.end_at.isoformat() if e.end_at else None,
                "description": e.description,
            }
            for e in events
        ]
    }
