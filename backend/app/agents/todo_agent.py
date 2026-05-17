from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import call_llm
from app.core.config import get_settings
from app.db.models import Attachment, User
from app.services.todo import NotFoundError, TodoService
from app.services.todoist import TodoistAuthError, TodoistClient
from app.services.todoist_sync import (
    push_close_local_task,
    push_local_task,
    sync_user_todoist,
)


TODO_TOOLS: list[dict[str, Any]] = [
    {
        "name": "todo.add_task",
        "description": "Create a new task. priority is 1 (highest) to 5 (lowest), default 3.",
        "input_schema": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "notes": {"type": "string"},
                "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                "due_at": {"type": "string", "description": "ISO-8601 datetime with tz"},
            },
        },
    },
    {
        "name": "todo.list_tasks",
        "description": "List tasks for the user, optionally filtered by status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["open", "done", "deferred", "cancelled"]},
            },
        },
    },
    {
        "name": "todo.complete_task",
        "description": "Mark a task as done by id.",
        "input_schema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {"task_id": {"type": "string", "description": "Task UUID"}},
        },
    },
    {
        "name": "todo.set_priority",
        "description": "Change a task's priority (1 highest .. 5 lowest).",
        "input_schema": {
            "type": "object",
            "required": ["task_id", "priority"],
            "properties": {
                "task_id": {"type": "string"},
                "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            },
        },
    },
    {
        "name": "todo.sync_todoist",
        "description": "Pull tasks from Todoist + push pending local tasks. Returns sync counts.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


TODO_SYSTEM = """\
You are the todo sub-agent for home_agent. The user speaks Korean.
Scope: todo.* only. Priorities are 1 (highest) .. 5 (lowest). Respond
briefly in Korean after the tool call.
"""


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _serialize_task(t) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "title": t.title,
        "status": t.status,
        "priority": t.priority,
        "due_at": t.due_at.isoformat() if t.due_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        # Phase 5: surface sync state so user sees pending/failed pushes
        "source": getattr(t, "source", "local"),
        "sync_state": getattr(t, "sync_state", None),
    }


def _todoist_token(user: User) -> str | None:
    tokens = (user.external_tokens or {}).get("todoist") or {}
    return tokens.get("access_token")


class TodoAgent:
    name = "todo"
    tools = TODO_TOOLS

    @property
    def model(self) -> str:
        return get_settings().agent_models["todo"]

    async def handle_tool(
        self,
        session: AsyncSession,
        *,
        user: User,
        intent: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        svc = TodoService(session, user.id)

        if intent == "add_task":
            try:
                task = await svc.create_task(
                    title=params["title"],
                    notes=params.get("notes"),
                    priority=params.get("priority", 3),
                    due_at=_parse_iso(params["due_at"]) if params.get("due_at") else None,
                )
            except (KeyError, ValueError) as exc:
                return {"ok": False, "error": f"invalid params: {exc}"}
            # Phase 5 write-through: push to Todoist if user has token (best-effort).
            token = _todoist_token(user)
            if token:
                async with TodoistClient(token) as client:
                    await push_local_task(session, client, task=task)
            return {"ok": True, "task": _serialize_task(task)}

        if intent == "list_tasks":
            try:
                tasks = await svc.list_tasks(status=params.get("status"))
                return {"ok": True, "tasks": [_serialize_task(t) for t in tasks]}
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}

        if intent == "complete_task":
            try:
                task = await svc.get_task(UUID(params["task_id"]))
            except (KeyError, ValueError) as exc:
                return {"ok": False, "error": f"invalid params: {exc}"}
            except NotFoundError as exc:
                return {"ok": False, "error": str(exc)}
            # Phase 5: push close to Todoist for source='todoist' tasks
            token = _todoist_token(user)
            if task.source == "todoist" and token:
                async with TodoistClient(token) as client:
                    ok = await push_close_local_task(client, task=task)
                if not ok:
                    task.sync_state = "pending"
                    task.retry_count = (task.retry_count or 0) + 1
            updated = await svc.complete_task(task.id)
            return {"ok": True, "task": _serialize_task(updated)}

        if intent == "set_priority":
            try:
                task = await svc.get_task(UUID(params["task_id"]))
                new_priority = int(params["priority"])
            except (KeyError, ValueError) as exc:
                return {"ok": False, "error": f"invalid params: {exc}"}
            except NotFoundError as exc:
                return {"ok": False, "error": str(exc)}
            token = _todoist_token(user)
            if task.source == "todoist" and task.external_id and token:
                from app.services.todoist import map_priority_local_to_todoist
                async with TodoistClient(token) as client:
                    try:
                        await client.update_task(
                            task.external_id,
                            priority=map_priority_local_to_todoist(new_priority),
                        )
                    except Exception:
                        task.sync_state = "pending"
                        task.retry_count = (task.retry_count or 0) + 1
            updated = await svc.update_task(task.id, priority=new_priority)
            return {"ok": True, "task": _serialize_task(updated)}

        if intent == "sync_todoist":
            token = _todoist_token(user)
            if not token:
                return {
                    "ok": False,
                    "error": "Todoist 재인증 필요. /oauth/todoist/start 를 새 창에서 열어주세요.",
                }
            try:
                async with TodoistClient(token) as client:
                    result = await sync_user_todoist(session, user=user, client=client)
            except TodoistAuthError:
                user.external_tokens["todoist"] = None
                await session.commit()
                return {
                    "ok": False,
                    "error": "Todoist 토큰이 만료/취소되었습니다. /oauth/todoist/start 에서 재인증하세요.",
                }
            return {"ok": True, "result": result}

        return {"ok": False, "error": f"unknown intent: {intent}"}

    async def run_turn(
        self,
        session: AsyncSession,
        *,
        user: User,
        session_id: UUID | None,
        user_message: str,
        recent_messages: list[dict[str, Any]],
        attachments: list[Attachment] | None = None,
    ) -> dict[str, Any]:
        messages = [*recent_messages, {"role": "user", "content": user_message}]
        llm_resp = await call_llm(
            messages=messages, tools=self.tools, system=TODO_SYSTEM, model=self.model
        )

        tool_results = []
        for call in llm_resp.get("tool_calls", []):
            _, intent = call["name"].split(".", 1)
            res = await self.handle_tool(session, user=user, intent=intent, params=call["arguments"])
            tool_results.append({"name": call["name"], "result": res})

        return {
            "assistant_message": llm_resp.get("final_text", ""),
            "tool_calls": tool_results,
        }
