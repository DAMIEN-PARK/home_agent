from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event


async def create_local_event(
    session: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    start_at: datetime,
    end_at: datetime | None = None,
    description: str | None = None,
) -> Event:
    event = Event(
        user_id=user_id,
        source="local",
        title=title,
        start_at=start_at,
        end_at=end_at,
        description=description,
    )
    session.add(event)
    await session.flush()
    await session.commit()
    return event


async def list_events(
    session: AsyncSession,
    *,
    user_id: UUID,
    from_: datetime,
    to: datetime,
) -> Sequence[Event]:
    stmt = (
        select(Event)
        .where(Event.user_id == user_id, Event.start_at >= from_, Event.start_at < to)
        .order_by(Event.start_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def upsert_google_event(
    session: AsyncSession,
    *,
    user_id: UUID,
    external_id: str,
    title: str,
    start_at: datetime,
    end_at: datetime | None,
    description: str | None,
    synced_at: datetime,
) -> Event:
    stmt = select(Event).where(Event.source == "google", Event.external_id == external_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.title = title
        existing.start_at = start_at
        existing.end_at = end_at
        existing.description = description
        existing.synced_at = synced_at
        await session.commit()
        return existing

    event = Event(
        user_id=user_id,
        source="google",
        external_id=external_id,
        title=title,
        start_at=start_at,
        end_at=end_at,
        description=description,
        synced_at=synced_at,
    )
    session.add(event)
    await session.commit()
    return event
