"""Common interface and helpers for domain sub-agents.

Each domain (schedule / todo / ledger / finance / ideas / files) implements
DomainAgent. The orchestrator dispatches tool calls to `handle_tool`; the
per-domain chat endpoint (`POST /chat/{domain}`) invokes `run_turn`.
"""
import base64
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Attachment, User


class DomainAgent(Protocol):
    name: str
    tools: list[dict[str, Any]]
    model: str

    async def handle_tool(
        self,
        session: AsyncSession,
        *,
        user: User,
        intent: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a single tool dispatched by the orchestrator. No LLM call."""
        ...

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
        """Domain chat turn — own LLM call with own tools/system prompt.

        `attachments` carries already-persisted files (saved by FilesAgent
        before dispatch). v1: only files-aware agents (`files`) use them;
        others ignore.
        """
        ...


def build_user_message(
    text: str, attachments: list[Attachment] | None = None
) -> dict[str, Any]:
    """Compose the user role message, embedding image attachments as Claude
    vision content blocks. PDFs/text fall back to a text marker pending a
    dedicated extractor."""
    atts = attachments or []
    if not atts:
        return {"role": "user", "content": text}

    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for att in atts:
        if att.mime_type.startswith("image/"):
            raw = Path(att.path).read_bytes()
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": att.mime_type,
                        "data": base64.b64encode(raw).decode(),
                    },
                }
            )
        else:
            content.append(
                {
                    "type": "text",
                    "text": f"[attachment: {att.original_name} ({att.mime_type})]",
                }
            )
    return {"role": "user", "content": content}


async def call_llm(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    system: str,
    model: str,
) -> dict[str, Any]:
    """Thin wrapper around claude_agent_sdk for testability."""
    from claude_agent_sdk import ClaudeClient

    client = ClaudeClient()
    return await client.run(messages=messages, tools=tools, system=system, model=model)


class StubAgent:
    """Domain agent whose tool calls are recognized but not yet implemented.

    Used for ledger/finance/ideas/files in v1 — the orchestrator LLM sees the
    full tool schema, dispatches calls, and gets a `not implemented` response
    that it surfaces to the user. The direct domain chat returns a fixed
    Korean placeholder message without calling the LLM.
    """

    def __init__(self, name: str, tools: list[dict[str, Any]]):
        self.name = name
        self.tools = tools

    @property
    def model(self) -> str:
        from app.core.config import get_settings

        return get_settings().agent_models[self.name]

    async def handle_tool(
        self, session, *, user, intent: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "error": f"{self.name}.{intent} not implemented yet",
        }

    async def run_turn(
        self,
        session,
        *,
        user,
        session_id,
        user_message: str,
        recent_messages: list[dict[str, Any]],
        attachments: list[Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "assistant_message": f"{self.name} 도메인은 아직 구현되지 않았어요.",
            "tool_calls": [],
        }
