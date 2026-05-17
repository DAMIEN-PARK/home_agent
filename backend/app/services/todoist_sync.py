"""Todoist sync orchestration: pull + upsert + tombstone + push.

Mirrors calendar_sync.py pattern (one-way pull) but adds push-from-local
for write-through asymmetric sync (Phase 5 v3 Option C-lite).

Commit semantics (Phase 5 ADR):
- sync_user_todoist, upsert_todoist_task, tombstone_missing_todoist_tasks:
  service-commit (schedule_service precedent)
- push_local_task: flush only (chat turn commit과 통합 — TodoAgent caller path)
"""
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.models.todo import Task
from app.services.todoist import (
    TodoistClient,
    map_priority_local_to_todoist,
    map_priority_todoist_to_local,
)


MAX_RETRY = 5


class _TodoistClientLike(Protocol):
    async def list_tasks(self, *, project_id: str | None = None) -> list[dict[str, Any]]: ...
    async def post_task(self, **kwargs: Any) -> dict[str, Any]: ...
    async def close_task(self, task_id: str) -> None: ...
    async def list_projects(self) -> list[dict[str, Any]]: ...


def _fetch_todoist_token(user: User) -> str | None:
    tokens = (user.external_tokens or {}).get("todoist") or {}
    return tokens.get("access_token")


async def _fetch_default_project_id(client: _TodoistClientLike) -> str | None:
    """Inbox (or first project) — used as push fallback when local project_id is invalid/archived."""
    projects = await client.list_projects()
    for p in projects:
        if p.get("is_inbox_project"):
            return p["id"]
    return projects[0]["id"] if projects else None


async def upsert_todoist_task(
    session: AsyncSession,
    *,
    user_id: UUID,
    external_id: str,
    title: str,
    priority: int,
    completed: bool,
    notes: str | None,
    synced_at: datetime,
) -> Task:
    """Insert or update a source='todoist' task. Service commits."""
    stmt = select(Task).where(
        Task.source == "todoist",
        Task.external_id == external_id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        existing.title = title
        existing.priority = priority
        existing.notes = notes
        # Sync overrides status open/done; preserves deferred tombstones (handled separately)
        if existing.status != "deferred":
            new_status = "done" if completed else "open"
            existing.status = new_status
            existing.completed_at = synced_at if completed else None
        existing.synced_at = synced_at
        await session.commit()
        return existing

    task = Task(
        user_id=user_id,
        title=title,
        priority=priority,
        notes=notes,
        status="done" if completed else "open",
        completed_at=synced_at if completed else None,
        source="todoist",
        external_id=external_id,
        synced_at=synced_at,
    )
    session.add(task)
    await session.commit()
    return task


async def tombstone_missing_todoist_tasks(
    session: AsyncSession,
    *,
    user_id: UUID,
    server_external_ids: set[str],
    synced_at: datetime,
) -> int:
    """Mark source='todoist' tasks missing from server as status='deferred' (soft-delete).

    Tombstones are immutable — only status + synced_at touched (Phase 5 v3 §1 Principle 4).
    Service commits. Returns count tombstoned.
    """
    stmt = select(Task).where(
        Task.user_id == user_id,
        Task.source == "todoist",
        Task.status != "deferred",
    )
    rows = (await session.execute(stmt)).scalars().all()
    n = 0
    for t in rows:
        if t.external_id not in server_external_ids:
            t.status = "deferred"
            t.synced_at = synced_at
            n += 1
    if n:
        await session.commit()
    return n


async def push_local_task(
    session: AsyncSession,
    client: _TodoistClientLike,
    *,
    task: Task,
) -> str | None:
    """Push a local task to Todoist. Returns external_id on success.

    On failure: increments retry_count, sets sync_state='pending' (or 'failed' if retry_count >= MAX_RETRY).
    Flush only (caller commits).
    """
    try:
        resp = await client.post_task(
            content=task.title,
            description=task.notes,
            priority=map_priority_local_to_todoist(task.priority),
        )
        task.external_id = resp["id"]
        task.sync_state = None
        task.retry_count = 0
        task.synced_at = datetime.now(timezone.utc)
        await session.flush()
        return resp["id"]
    except Exception:
        task.retry_count = (task.retry_count or 0) + 1
        task.sync_state = "failed" if task.retry_count >= MAX_RETRY else "pending"
        await session.flush()
        return None


async def push_close_local_task(
    client: _TodoistClientLike,
    *,
    task: Task,
) -> bool:
    """Close a Todoist task corresponding to a local source='todoist' task.

    Returns True on success, False on failure (caller sets sync_state).
    No session arg — only external API call, caller handles DB state.
    """
    if not task.external_id:
        return False
    try:
        await client.close_task(task.external_id)
        return True
    except Exception:
        return False


async def sync_user_todoist(
    session: AsyncSession,
    *,
    user: User,
    client: _TodoistClientLike,
) -> dict[str, Any]:
    """Pull Todoist tasks → upsert local + tombstone missing. Retry pending pushes.

    Service-commits internally. Returns {synced, pushed, tombstoned, errors, pending_task_ids}.
    """
    now = datetime.now(timezone.utc)

    # 1. Pull from Todoist
    raw_tasks = await client.list_tasks()
    server_external_ids: set[str] = set()
    for raw in raw_tasks:
        ext_id = raw["id"]
        server_external_ids.add(ext_id)
        await upsert_todoist_task(
            session,
            user_id=user.id,
            external_id=ext_id,
            title=raw["content"],
            priority=map_priority_todoist_to_local(raw.get("priority", 1)),
            completed=bool(raw.get("is_completed")),
            notes=raw.get("description") or None,
            synced_at=now,
        )

    synced = len(raw_tasks)
    tombstoned = await tombstone_missing_todoist_tasks(
        session,
        user_id=user.id,
        server_external_ids=server_external_ids,
        synced_at=now,
    )

    # 2. Retry pending push tasks
    pending_stmt = select(Task).where(
        Task.user_id == user.id,
        Task.sync_state == "pending",
    )
    pending = (await session.execute(pending_stmt)).scalars().all()
    pushed = 0
    errors = 0
    for t in pending:
        ext_id = await push_local_task(session, client, task=t)
        if ext_id:
            pushed += 1
        else:
            errors += 1
    if pending:
        await session.commit()

    # 3. Surface remaining pending task ids
    still_pending_stmt = select(Task.id).where(
        Task.user_id == user.id,
        Task.sync_state.in_(["pending", "failed"]),
    )
    pending_task_ids = [str(row) for row in (await session.execute(still_pending_stmt)).scalars().all()]

    return {
        "synced": synced,
        "pushed": pushed,
        "tombstoned": tombstoned,
        "errors": errors,
        "pending_task_ids": pending_task_ids,
    }
