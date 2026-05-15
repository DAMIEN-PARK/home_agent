from datetime import datetime, timezone

import pytest
from pytest_httpx import HTTPXMock

from app.services.google_calendar import GoogleCalendarClient


@pytest.mark.asyncio
async def test_list_events_parses_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url__regex=r"https://www\.googleapis\.com/calendar/v3/calendars/.*",
        json={
            "items": [
                {
                    "id": "evt_001",
                    "summary": "Standup",
                    "start": {"dateTime": "2026-05-19T10:00:00+09:00"},
                    "end": {"dateTime": "2026-05-19T10:30:00+09:00"},
                    "description": "daily standup",
                }
            ]
        },
    )

    client = GoogleCalendarClient(access_token="fake")
    events = await client.list_events(
        calendar_id="primary",
        time_min=datetime(2026, 5, 1, tzinfo=timezone.utc),
        time_max=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    assert len(events) == 1
    assert events[0]["id"] == "evt_001"
    assert events[0]["start_at"].isoformat() == "2026-05-19T01:00:00+00:00"
