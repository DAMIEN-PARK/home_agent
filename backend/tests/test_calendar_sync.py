from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.calendar_sync import sync_user_google_calendar
from app.services.schedule_service import list_events


@pytest.mark.asyncio
async def test_sync_upserts_google_events(db_session, test_user):
    fake_client = AsyncMock()
    fake_client.list_events.return_value = [
        {
            "id": "g_evt_1",
            "summary": "Standup",
            "start_at": datetime(2026, 5, 20, 1, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 5, 20, 1, 30, tzinfo=timezone.utc),
            "description": None,
        }
    ]

    await sync_user_google_calendar(
        db_session,
        user=test_user,
        client=fake_client,
        calendar_id="primary",
        window_days_back=1,
        window_days_forward=30,
    )

    events = await list_events(
        db_session,
        user_id=test_user.id,
        from_=datetime(2026, 5, 1, tzinfo=timezone.utc),
        to=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert len(events) == 1
    assert events[0].external_id == "g_evt_1"
    assert events[0].source == "google"


@pytest.mark.asyncio
async def test_sync_is_idempotent(db_session, test_user):
    fake_client = AsyncMock()
    fake_client.list_events.return_value = [
        {
            "id": "g_evt_1",
            "summary": "Standup v1",
            "start_at": datetime(2026, 5, 20, 1, 0, tzinfo=timezone.utc),
            "end_at": None,
            "description": None,
        }
    ]
    await sync_user_google_calendar(
        db_session, user=test_user, client=fake_client, calendar_id="primary"
    )

    fake_client.list_events.return_value = [
        {
            "id": "g_evt_1",
            "summary": "Standup v2",  # title changed
            "start_at": datetime(2026, 5, 20, 1, 0, tzinfo=timezone.utc),
            "end_at": None,
            "description": None,
        }
    ]
    await sync_user_google_calendar(
        db_session, user=test_user, client=fake_client, calendar_id="primary"
    )

    events = await list_events(
        db_session,
        user_id=test_user.id,
        from_=datetime(2026, 5, 1, tzinfo=timezone.utc),
        to=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert len(events) == 1
    assert events[0].title == "Standup v2"
