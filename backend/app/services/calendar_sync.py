from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services.schedule_service import upsert_google_event


class _CalendarClient(Protocol):
    async def list_events(
        self, *, calendar_id: str, time_min: datetime, time_max: datetime
    ) -> list[dict]: ...


async def sync_user_google_calendar(
    session: AsyncSession,
    *,
    user: User,
    client: _CalendarClient,
    calendar_id: str = "primary",
    window_days_back: int = 1,
    window_days_forward: int = 90,
) -> int:
    """Pull events from Google Calendar and upsert into schedule.events.
    Returns number of events synced."""
    now = datetime.now(timezone.utc)
    time_min = now - timedelta(days=window_days_back)
    time_max = now + timedelta(days=window_days_forward)

    raw_events = await client.list_events(
        calendar_id=calendar_id, time_min=time_min, time_max=time_max
    )

    for evt in raw_events:
        await upsert_google_event(
            session,
            user_id=user.id,
            external_id=evt["id"],
            title=evt["summary"],
            start_at=evt["start_at"],
            end_at=evt.get("end_at"),
            description=evt.get("description"),
            synced_at=now,
        )

    return len(raw_events)
