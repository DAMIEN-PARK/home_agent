"""files domain agent — stores uploads to disk + metadata rows.

v1 scope: storage and metadata only. OCR / auto-tagging / semantic search are
delegated to the *consuming* domain agent (which can use Claude vision on the
raw bytes) — see docs/superpowers/specs/2026-05-17-domain-chat-attachments.md.
"""
from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Attachment, User


FILES_TOOLS: list[dict[str, Any]] = [
    {
        "name": "files.list_recent",
        "description": "List the user's recently uploaded files.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
        },
    },
    {
        "name": "files.search_files",
        "description": "Natural-language search across files and photos.",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "type": {"type": "string", "enum": ["photo", "document", "pdf"]},
            },
        },
    },
]


def _ext_for(mime: str, original_name: str) -> str:
    """Choose an on-disk extension. Prefer mime-derived; fall back to filename."""
    guessed = mimetypes.guess_extension(mime) or ""
    if guessed:
        return guessed.lstrip(".")
    suffix = Path(original_name).suffix.lstrip(".")
    return suffix or "bin"


def _serialize(att: Attachment) -> dict[str, Any]:
    return {
        "id": str(att.id),
        "original_name": att.original_name,
        "mime_type": att.mime_type,
        "size_bytes": att.size_bytes,
        "sha256": att.sha256,
    }


class FilesAgent:
    name = "files"
    tools = FILES_TOOLS

    @property
    def model(self) -> str:
        return get_settings().agent_models["files"]

    async def save_attachment(
        self,
        session: AsyncSession,
        *,
        user: User,
        raw: bytes,
        original_name: str,
        mime: str,
        session_id: UUID | None = None,
    ) -> Attachment:
        """Persist `raw` to disk (dedup by sha256) and insert a metadata row."""
        sha = hashlib.sha256(raw).hexdigest()
        ext = _ext_for(mime, original_name)
        root = get_settings().files_root
        subdir = root / sha[:2]
        subdir.mkdir(parents=True, exist_ok=True)
        path = subdir / f"{sha}.{ext}"
        if not path.exists():
            path.write_bytes(raw)

        att = Attachment(
            user_id=user.id,
            session_id=session_id,
            path=str(path),
            sha256=sha,
            original_name=original_name,
            mime_type=mime,
            size_bytes=len(raw),
        )
        session.add(att)
        await session.flush()
        return att

    async def get_attachment_bytes(
        self, session: AsyncSession, *, user: User, attachment_id: UUID
    ) -> tuple[bytes, str]:
        att = await session.get(Attachment, attachment_id)
        if att is None or att.user_id != user.id:
            raise LookupError(f"attachment {attachment_id} not found")
        return Path(att.path).read_bytes(), att.mime_type

    async def handle_tool(
        self,
        session: AsyncSession,
        *,
        user: User,
        intent: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if intent == "list_recent":
            limit = int(params.get("limit") or 20)
            stmt = (
                select(Attachment)
                .where(Attachment.user_id == user.id)
                .order_by(Attachment.created_at.desc())
                .limit(limit)
            )
            rows = list((await session.scalars(stmt)).all())
            return {"ok": True, "files": [_serialize(a) for a in rows]}

        if intent == "search_files":
            # v1: semantic search not implemented; defer to a later spec.
            return {"ok": False, "error": "files.search_files not implemented yet"}

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
        n = len(attachments or [])
        if n == 0:
            text = "파일을 첨부하면 등록해 드려요."
        elif n == 1:
            a = (attachments or [])[0]
            text = f"`{a.original_name}` 1개 파일을 등록했어요."
        else:
            text = f"{n}개 파일을 등록했어요."
        return {"assistant_message": text, "tool_calls": []}
