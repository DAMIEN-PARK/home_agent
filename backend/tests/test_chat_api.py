from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_post_chat_creates_event(app_client: AsyncClient, test_user):
    fake_response = {
        "tool_calls": [
            {
                "name": "schedule.create_event",
                "arguments": {
                    "title": "회의",
                    "start_at": "2026-05-19T15:00:00+09:00",
                },
            }
        ],
        "final_text": "회의 잡았어요.",
    }
    with patch(
        "app.agents.orchestrator.call_llm",
        new=AsyncMock(return_value=fake_response),
    ):
        resp = await app_client.post(
            "/chat",
            json={
                "message": "5월 19일 3시 회의 잡아줘",
                "user_id": str(test_user.id),
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "회의 잡았어요" in data["assistant_message"]
    assert len(data["tool_calls"]) == 1


@pytest.mark.asyncio
async def test_post_chat_unknown_user_404(app_client: AsyncClient):
    resp = await app_client.post(
        "/chat",
        json={
            "message": "hi",
            "user_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_response_contract(app_client: AsyncClient, test_user):
    """ChatResponse keys exactly {assistant_message, tool_calls}; drift detection.

    Baseline at plan-write: schemas/chat.py:18-20 has exactly 2 fields.
    Any future field addition forces test update — intended drift detection.
    """
    fake_llm = {
        "tool_calls": [{"name": "noop.test", "arguments": {"k": "v"}}],
        "final_text": "ok",
    }
    with patch(
        "app.agents.orchestrator.call_llm",
        new=AsyncMock(return_value=fake_llm),
    ):
        resp = await app_client.post(
            "/chat",
            json={"message": "hi", "user_id": str(test_user.id)},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"assistant_message", "tool_calls"}
    assert isinstance(data["assistant_message"], str)
    assert isinstance(data["tool_calls"], list)
    for tc in data["tool_calls"]:
        assert set(tc.keys()) == {"name", "result"}
