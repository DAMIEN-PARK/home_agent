from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.db.models.todo import Task
from app.services.todoist_sync import push_local_task, sync_user_todoist


@pytest.mark.asyncio
async def test_sync_upserts_new_tasks(db_session, test_user):
    fake_client = AsyncMock()
    fake_client.list_tasks.return_value = [
        {
            "id": "todoist_001",
            "content": "장보기",
            "priority": 2,
            "is_completed": False,
            "description": None,
        }
    ]

    result = await sync_user_todoist(db_session, user=test_user, client=fake_client)

    assert result["synced"] == 1
    assert result["tombstoned"] == 0
    rows = (
        await db_session.execute(
            select(Task).where(Task.user_id == test_user.id, Task.source == "todoist")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].external_id == "todoist_001"
    assert rows[0].title == "장보기"


@pytest.mark.asyncio
async def test_sync_updates_existing_tasks(db_session, test_user):
    fake_client = AsyncMock()
    fake_client.list_tasks.return_value = [
        {
            "id": "todoist_001",
            "content": "장보기 v1",
            "priority": 1,
            "is_completed": False,
            "description": None,
        }
    ]
    await sync_user_todoist(db_session, user=test_user, client=fake_client)

    fake_client.list_tasks.return_value = [
        {
            "id": "todoist_001",
            "content": "장보기 v2",  # title changed
            "priority": 1,
            "is_completed": False,
            "description": None,
        }
    ]
    await sync_user_todoist(db_session, user=test_user, client=fake_client)

    rows = (
        await db_session.execute(
            select(Task).where(Task.user_id == test_user.id, Task.source == "todoist")
        )
    ).scalars().all()
    assert len(rows) == 1  # no duplicate
    assert rows[0].title == "장보기 v2"


@pytest.mark.asyncio
async def test_sync_tombstones_deleted_tasks(db_session, test_user):
    fake_client = AsyncMock()
    # Initial sync with 1 task
    fake_client.list_tasks.return_value = [
        {
            "id": "todoist_001",
            "content": "장보기",
            "priority": 1,
            "is_completed": False,
            "description": None,
        }
    ]
    await sync_user_todoist(db_session, user=test_user, client=fake_client)

    # Server now empty → task should be tombstoned
    fake_client.list_tasks.return_value = []
    result = await sync_user_todoist(db_session, user=test_user, client=fake_client)

    assert result["tombstoned"] == 1
    row = (
        await db_session.execute(
            select(Task).where(Task.external_id == "todoist_001")
        )
    ).scalar_one()
    assert row.status == "deferred"
    assert row.title == "장보기"  # title immutable on tombstone


@pytest.mark.asyncio
async def test_sync_does_not_touch_local_tasks(db_session, test_user):
    """source='local' tasks unaffected by sync (tombstone scope = source='todoist' only)."""
    local_task = Task(
        user_id=test_user.id,
        title="local-only task",
        status="open",
        priority=3,
        source="local",
    )
    db_session.add(local_task)
    await db_session.commit()

    fake_client = AsyncMock()
    fake_client.list_tasks.return_value = []
    await sync_user_todoist(db_session, user=test_user, client=fake_client)

    await db_session.refresh(local_task)
    assert local_task.status == "open"  # not tombstoned


@pytest.mark.asyncio
async def test_push_failure_sets_sync_state_pending(db_session, test_user):
    task = Task(
        user_id=test_user.id,
        title="장보기",
        status="open",
        priority=3,
        source="local",
    )
    db_session.add(task)
    await db_session.commit()

    fake_client = AsyncMock()
    fake_client.post_task.side_effect = RuntimeError("network down")

    ext_id = await push_local_task(db_session, fake_client, task=task)
    await db_session.commit()

    assert ext_id is None
    await db_session.refresh(task)
    assert task.sync_state == "pending"
    assert task.retry_count == 1
    assert task.external_id is None
