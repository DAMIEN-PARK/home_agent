from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.agents.todo_agent import TodoAgent
from app.db.models.todo import Task


@pytest.mark.asyncio
async def test_add_task_pushes_to_todoist(db_session, test_user):
    """When user has Todoist token, add_task pushes to Todoist + records external_id."""
    test_user.external_tokens = {
        "todoist": {
            "access_token": "fake_token",
            "refresh_token": None,
            "scope": "data:read_write",
        }
    }
    await db_session.commit()

    fake_post_response = {"id": "todoist_new_001", "content": "장보기"}
    with patch("app.agents.todo_agent.TodoistClient") as MockClient:
        instance = AsyncMock()
        instance.post_task.return_value = fake_post_response
        MockClient.return_value.__aenter__.return_value = instance

        agent = TodoAgent()
        result = await agent.handle_tool(
            db_session,
            user=test_user,
            intent="add_task",
            params={"title": "장보기"},
        )

    assert result["ok"] is True
    task_id = result["task"]["id"]
    await db_session.commit()
    row = (
        await db_session.execute(select(Task).where(Task.title == "장보기"))
    ).scalar_one()
    assert str(row.id) == task_id
    assert row.external_id == "todoist_new_001"
    assert row.sync_state is None


@pytest.mark.asyncio
async def test_complete_task_on_todoist_source_closes_remote(db_session, test_user):
    """complete_task on source='todoist' task triggers Todoist close API + local update."""
    test_user.external_tokens = {
        "todoist": {
            "access_token": "fake_token",
            "refresh_token": None,
            "scope": "data:read_write",
        }
    }
    task = Task(
        user_id=test_user.id,
        title="외부 task",
        status="open",
        priority=3,
        source="todoist",
        external_id="todoist_existing_001",
    )
    db_session.add(task)
    await db_session.commit()

    with patch("app.agents.todo_agent.TodoistClient") as MockClient:
        instance = AsyncMock()
        instance.close_task.return_value = None
        MockClient.return_value.__aenter__.return_value = instance

        agent = TodoAgent()
        result = await agent.handle_tool(
            db_session,
            user=test_user,
            intent="complete_task",
            params={"task_id": str(task.id)},
        )

        instance.close_task.assert_called_once_with("todoist_existing_001")

    assert result["ok"] is True
    assert result["task"]["status"] == "done"


@pytest.mark.asyncio
async def test_sync_tool_invokes_endpoint(db_session, test_user):
    """sync_todoist intent triggers sync_user_todoist with TodoistClient."""
    test_user.external_tokens = {
        "todoist": {
            "access_token": "fake_token",
            "refresh_token": None,
            "scope": "data:read_write",
        }
    }
    await db_session.commit()

    with patch("app.agents.todo_agent.TodoistClient") as MockClient, patch(
        "app.agents.todo_agent.sync_user_todoist"
    ) as mock_sync:
        instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = instance
        mock_sync.return_value = {
            "synced": 0,
            "pushed": 0,
            "tombstoned": 0,
            "errors": 0,
            "pending_task_ids": [],
        }

        agent = TodoAgent()
        result = await agent.handle_tool(
            db_session,
            user=test_user,
            intent="sync_todoist",
            params={},
        )

    assert result["ok"] is True
    assert "result" in result
    mock_sync.assert_called_once()
