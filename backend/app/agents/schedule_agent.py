from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import call_llm
from app.core.config import get_settings
from app.db.models import Attachment, User
from app.services.schedule_service import create_local_event, list_events


SCHEDULE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "schedule.create_event",
        "description": "Create a calendar event in the user's local calendar (not Google).",
        "input_schema": {
            "type": "object",
            "required": ["title", "start_at"],
            "properties": {
                "title": {"type": "string"},
                "start_at": {"type": "string", "description": "ISO-8601 datetime with tz"},
                "end_at": {"type": "string"},
                "description": {"type": "string"},
            },
        },
    },
    {
        "name": "schedule.list_events",
        "description": "List events between two datetimes (includes Google-synced and local).",
        "input_schema": {
            "type": "object",
            "required": ["from", "to"],
            "properties": {
                "from": {"type": "string"},
                "to": {"type": "string"},
            },
        },
    },
]


SCHEDULE_SYSTEM = """\
You are the schedule sub-agent for home_agent. The user speaks Korean.
Scope: schedule.* only. Resolve relative times against today's date in KST.
Respond briefly in Korean after the tool call.
"""


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _serialize_event(e) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "title": e.title,
        "source": e.source,
        "external_id": e.external_id,
        "start_at": e.start_at.isoformat(),
        "end_at": e.end_at.isoformat() if e.end_at else None,
        "description": e.description,
    }


class ScheduleAgent:
    name = "schedule"
    tools = SCHEDULE_TOOLS

    @property
    def model(self) -> str:
        return get_settings().agent_models["schedule"]

    async def handle_tool(
        self,
        session: AsyncSession,
        *,
        user: User,
        intent: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if intent == "create_event":
            try:
                event = await create_local_event(
                    session,
                    user_id=user.id,
                    title=params["title"],
                    start_at=_parse_iso(params["start_at"]),
                    end_at=_parse_iso(params["end_at"]) if params.get("end_at") else None,
                    description=params.get("description"),
                )
                return {"ok": True, "event": _serialize_event(event)}
            except (KeyError, ValueError) as exc:
                return {"ok": False, "error": f"invalid params: {exc}"}

        if intent == "list_events":
            try:
                events = await list_events(
                    session,
                    user_id=user.id,
                    from_=_parse_iso(params["from"]),
                    to=_parse_iso(params["to"]),
                )
                return {"ok": True, "events": [_serialize_event(e) for e in events]}
            except (KeyError, ValueError) as exc:
                return {"ok": False, "error": f"invalid params: {exc}"}

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
            messages=messages, tools=self.tools, system=SCHEDULE_SYSTEM, model=self.model
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


# Backwards-compatible thin wrapper so `from app.agents.schedule_agent import handle_intent`
# in orchestrator.py keeps working until Step 7 rewrites it.
async def handle_intent(
    session: AsyncSession,
    *,
    user: User,
    intent: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    return await ScheduleAgent().handle_tool(session, user=user, intent=intent, params=params)
