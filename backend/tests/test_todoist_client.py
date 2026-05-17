import pytest
from pytest_httpx import HTTPXMock

from app.services.todoist import TodoistAuthError, TodoistClient


@pytest.mark.asyncio
async def test_list_tasks_parses_payload(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.todoist.com/rest/v2/tasks",
        json=[
            {
                "id": "todoist_001",
                "content": "장보기",
                "priority": 2,
                "is_completed": False,
                "description": None,
            }
        ],
    )

    async with TodoistClient(access_token="fake") as client:
        tasks = await client.list_tasks()

    assert len(tasks) == 1
    assert tasks[0]["id"] == "todoist_001"
    assert tasks[0]["content"] == "장보기"


@pytest.mark.asyncio
async def test_list_tasks_raises_on_401(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.todoist.com/rest/v2/tasks",
        status_code=401,
    )

    async with TodoistClient(access_token="bad") as client:
        with pytest.raises(TodoistAuthError):
            await client.list_tasks()


@pytest.mark.asyncio
async def test_aenter_aexit_closes_http(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.todoist.com/rest/v2/tasks", json=[]
    )

    async with TodoistClient(access_token="fake") as client:
        await client.list_tasks()
        http = client._http
    # After exit, httpx client owned by TodoistClient must be closed.
    assert http.is_closed


@pytest.mark.asyncio
async def test_backoff_on_429(httpx_mock: HTTPXMock, monkeypatch):
    # Suppress real sleep to keep test fast.
    import app.services.todoist as todoist_module
    sleeps: list[float] = []

    async def fake_sleep(d):
        sleeps.append(d)

    monkeypatch.setattr(todoist_module.asyncio, "sleep", fake_sleep)

    httpx_mock.add_response(
        url="https://api.todoist.com/rest/v2/tasks", status_code=429
    )
    httpx_mock.add_response(
        url="https://api.todoist.com/rest/v2/tasks", status_code=429
    )
    httpx_mock.add_response(
        url="https://api.todoist.com/rest/v2/tasks", json=[]
    )

    async with TodoistClient(access_token="fake") as client:
        tasks = await client.list_tasks()

    assert tasks == []
    assert sleeps == [1, 2]  # exponential backoff
