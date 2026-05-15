from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schedule_agent import handle_intent as schedule_handle
from app.db.models import User


SCHEDULE_TOOLS = [
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


SYSTEM_PROMPT = """\
You are home_agent, a personal assistant orchestrator. The user speaks Korean.
Today's date is provided by the tool runtime. When the user asks about scheduling,
creating, or listing events, call the appropriate schedule.* tool. When relative
times are given ("내일 3시"), resolve them against today's date in the user's
timezone (KST, Asia/Seoul). Respond briefly in Korean after the tool call.
"""


async def _call_llm(messages: list[dict], tools: list[dict]) -> dict[str, Any]:
    """Real implementation uses claude_agent_sdk. Mocked in tests."""
    from claude_agent_sdk import ClaudeClient  # lazy import to keep tests fast

    client = ClaudeClient()
    return await client.run(messages=messages, tools=tools, system=SYSTEM_PROMPT)


async def run_turn(
    session: AsyncSession,
    *,
    user: User,
    session_id: UUID | None,
    user_message: str,
) -> dict[str, Any]:
    """Single conversational turn: LLM decides which tools to call, we dispatch."""
    messages = [{"role": "user", "content": user_message}]
    llm_resp = await _call_llm(messages, SCHEDULE_TOOLS)

    tool_results = []
    for call in llm_resp.get("tool_calls", []):
        name = call["name"]
        args = call["arguments"]
        if name == "schedule.create_event":
            res = await schedule_handle(session, user=user, intent="create_event", params=args)
        elif name == "schedule.list_events":
            res = await schedule_handle(session, user=user, intent="list_events", params=args)
        else:
            res = {"ok": False, "error": f"unknown tool {name}"}
        tool_results.append({"name": name, "result": res})

    return {
        "assistant_message": llm_resp.get("final_text", ""),
        "tool_calls": tool_results,
    }
