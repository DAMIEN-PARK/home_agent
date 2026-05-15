from datetime import datetime, timedelta, timezone

import pytest

from app.services.schedule_service import create_local_event, list_events


@pytest.mark.asyncio
async def test_create_local_event(db_session, test_user):
    now = datetime.now(timezone.utc)
    event = await create_local_event(
        db_session,
        user_id=test_user.id,
        title="회의",
        start_at=now,
        end_at=now + timedelta(hours=1),
    )
    assert event.title == "회의"
    assert event.source == "local"
    assert event.external_id is None


@pytest.mark.asyncio
async def test_list_events_filters_by_time_range(db_session, test_user):
    now = datetime.now(timezone.utc)
    await create_local_event(db_session, user_id=test_user.id, title="in", start_at=now)
    await create_local_event(
        db_session,
        user_id=test_user.id,
        title="out",
        start_at=now + timedelta(days=30),
    )
    events = await list_events(
        db_session,
        user_id=test_user.id,
        from_=now - timedelta(hours=1),
        to=now + timedelta(days=1),
    )
    titles = [e.title for e in events]
    assert "in" in titles
    assert "out" not in titles
