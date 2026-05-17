from unittest.mock import AsyncMock, patch

import pytest

from app.agents.orchestrator import run_turn


@pytest.mark.asyncio
async def test_run_turn_dispatches_create_event(db_session, test_user):
    """When LLM emits a create_event tool call, orchestrator persists the event."""
    fake_llm_response = {
        "tool_calls": [
            {
                "name": "schedule.create_event",
                "arguments": {
                    "title": "내일 3시 회의",
                    "start_at": "2026-05-16T15:00:00+09:00",
                },
            }
        ],
        "final_text": "내일 3시에 회의 잡았어요.",
    }

    with patch(
        "app.agents.orchestrator.call_llm",
        new=AsyncMock(return_value=fake_llm_response),
    ):
        result = await run_turn(
            db_session,
            user=test_user,
            session_id=None,
            user_message="내일 3시에 회의 잡아줘",
        )

    assert "회의 잡았어요" in result["assistant_message"]
    assert len(result["tool_calls"]) == 1
    # event actually persisted
    from sqlalchemy import select

    from app.db.models import Event

    rows = (await db_session.execute(select(Event))).scalars().all()
    assert len(rows) == 1
    assert rows[0].title == "내일 3시 회의"
