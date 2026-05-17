from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import call_llm
from app.agents.registry import REGISTRY
from app.core.config import get_settings
from app.db.models import Message, Session, User


ORCHESTRATOR_SYSTEM = """\
You are home_agent's orchestrator, a personal assistant. The user speaks Korean.
You have tools across six domains: schedule, todo, ledger, finance, ideas, files.
Call the appropriate <domain>.<intent> tool; multiple in one turn if needed.
When relative times are given ("내일 3시"), resolve against today's date (KST).
Respond briefly in Korean after tool calls. If a tool returns
{ok: false, error: "... not implemented yet"}, tell the user that domain is not
wired up yet and suggest what they can do instead.
"""


async def _load_domain_recent_turns(
    db: AsyncSession,
    *,
    user: User,
    device_id: UUID | None,
    per_domain_turns: int = 3,
) -> list[dict[str, Any]]:
    """For each non-orchestrator domain, fetch the active session for this
    (user, device) and prepend its last N user/assistant pairs to the
    orchestrator's context. Returns system-role messages, one per domain.
    """
    if device_id is None:
        return []

    out: list[dict[str, Any]] = []
    for domain in REGISTRY:
        sess_stmt = (
            select(Session)
            .where(
                Session.user_id == user.id,
                Session.device_id == device_id,
                Session.scope == domain,
                Session.ended_at.is_(None),
            )
            .order_by(Session.created_at.desc())
            .limit(1)
        )
        sess = (await db.scalars(sess_stmt)).first()
        if sess is None:
            continue

        msg_stmt = (
            select(Message)
            .where(
                Message.session_id == sess.id,
                Message.role.in_(["user", "assistant"]),
            )
            .order_by(Message.created_at.desc())
            .limit(per_domain_turns * 2)
        )
        msgs = list((await db.scalars(msg_stmt)).all())
        msgs.reverse()
        if not msgs:
            continue

        preview = "\n".join(f"[{m.role}] {m.content}" for m in msgs)
        out.append(
            {
                "role": "system",
                "content": f"Recent {domain} domain chat for this device:\n{preview}",
            }
        )
    return out


async def run_turn(
    db: AsyncSession,
    *,
    user: User,
    session_id: UUID | None,
    user_message: str,
    device_id: UUID | None = None,
    device_name: str | None = None,
) -> dict[str, Any]:
    all_tools = [t for agent in REGISTRY.values() for t in agent.tools]
    cross_ctx = await _load_domain_recent_turns(db, user=user, device_id=device_id)
    messages = [*cross_ctx, {"role": "user", "content": user_message}]
    model = get_settings().agent_models["orchestrator"]

    llm_resp = await call_llm(
        messages=messages, tools=all_tools, system=ORCHESTRATOR_SYSTEM, model=model
    )

    tool_results: list[dict[str, Any]] = []
    for call in llm_resp.get("tool_calls", []):
        name = call["name"]
        if "." not in name:
            tool_results.append(
                {"name": name, "result": {"ok": False, "error": "malformed tool name"}}
            )
            continue
        domain, intent = name.split(".", 1)
        agent = REGISTRY.get(domain)
        if agent is None:
            tool_results.append(
                {"name": name, "result": {"ok": False, "error": f"unknown domain: {domain}"}}
            )
            continue
        res = await agent.handle_tool(
            db, user=user, intent=intent, params=call["arguments"]
        )
        tool_results.append({"name": name, "result": res})

    return {
        "assistant_message": llm_resp.get("final_text", ""),
        "tool_calls": tool_results,
    }
