import pytest

from app.agents.schedule_agent import handle_intent


@pytest.mark.asyncio
async def test_handle_create_event(db_session, test_user):
    result = await handle_intent(
        db_session,
        user=test_user,
        intent="create_event",
        params={
            "title": "회의",
            "start_at": "2026-05-19T15:00:00+09:00",
            "end_at": "2026-05-19T16:00:00+09:00",
        },
    )
    assert result["ok"] is True
    assert result["event"]["title"] == "회의"


@pytest.mark.asyncio
async def test_handle_list_events(db_session, test_user):
    await handle_intent(
        db_session,
        user=test_user,
        intent="create_event",
        params={"title": "x", "start_at": "2026-05-20T10:00:00+09:00"},
    )
    result = await handle_intent(
        db_session,
        user=test_user,
        intent="list_events",
        params={"from": "2026-05-01T00:00:00Z", "to": "2026-06-01T00:00:00Z"},
    )
    assert result["ok"] is True
    assert len(result["events"]) == 1


@pytest.mark.asyncio
async def test_handle_unknown_intent_returns_error(db_session, test_user):
    result = await handle_intent(db_session, user=test_user, intent="???", params={})
    assert result["ok"] is False
