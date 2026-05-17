"""Todoist REST API v2 client.

Mirrors GoogleCalendarClient pattern but adds:
- TodoistAuthError (401) — caller clears token + surface re-auth
- async context manager (httpx lifecycle)
- exponential backoff on 429 (rate-limit: 450 req / 15min)
"""
import asyncio
from typing import Any

import httpx


TODOIST_API_BASE = "https://api.todoist.com/rest/v2"


class TodoistAuthError(Exception):
    """Raised when Todoist API returns 401. Caller clears stored token."""


class TodoistClient:
    """Stateless wrapper over Todoist REST v2. Use as async context manager.

    Example:
        async with TodoistClient(access_token) as client:
            tasks = await client.list_tasks()
    """

    def __init__(self, access_token: str, *, http: httpx.AsyncClient | None = None):
        self.access_token = access_token
        self._http = http or httpx.AsyncClient(timeout=15)
        self._owns_http = http is None

    async def __aenter__(self) -> "TodoistClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._owns_http:
            await self._http.aclose()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        url = f"{TODOIST_API_BASE}{path}"
        for attempt in range(3):
            resp = await self._http.request(method, url, headers=self._headers(), **kwargs)
            if resp.status_code == 401:
                raise TodoistAuthError("Todoist token rejected (401)")
            if resp.status_code == 429:
                # exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(1 << attempt)
                continue
            resp.raise_for_status()
            return resp
        # exhausted retries on 429
        resp.raise_for_status()
        return resp

    async def list_tasks(self, *, project_id: str | None = None) -> list[dict[str, Any]]:
        params = {"project_id": project_id} if project_id else {}
        resp = await self._request("GET", "/tasks", params=params)
        return resp.json()

    async def post_task(
        self,
        *,
        content: str,
        project_id: str | None = None,
        description: str | None = None,
        due_string: str | None = None,
        priority: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"content": content}
        if project_id:
            payload["project_id"] = project_id
        if description:
            payload["description"] = description
        if due_string:
            payload["due_string"] = due_string
        if priority is not None:
            # Todoist priority: 1 (normal) .. 4 (urgent); reverse of home_agent
            payload["priority"] = priority
        resp = await self._request("POST", "/tasks", json=payload)
        return resp.json()

    async def update_task(
        self,
        task_id: str,
        *,
        content: str | None = None,
        priority: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if content is not None:
            payload["content"] = content
        if priority is not None:
            payload["priority"] = priority
        resp = await self._request("POST", f"/tasks/{task_id}", json=payload)
        return resp.json()

    async def close_task(self, task_id: str) -> None:
        await self._request("POST", f"/tasks/{task_id}/close")

    async def list_projects(self) -> list[dict[str, Any]]:
        resp = await self._request("GET", "/projects")
        return resp.json()


def map_priority_local_to_todoist(local: int) -> int:
    """home_agent 1 (highest) .. 5 (lowest) -> Todoist 4 (urgent) .. 1 (normal).
    5 is lossy-mapped to Todoist 1 (no equivalent).
    """
    table = {1: 4, 2: 3, 3: 2, 4: 1, 5: 1}
    return table.get(local, 2)


def map_priority_todoist_to_local(remote: int) -> int:
    """Todoist 4 (urgent) .. 1 (normal) -> home_agent 1 .. 4. No 5-equivalent."""
    table = {4: 1, 3: 2, 2: 3, 1: 4}
    return table.get(remote, 3)
