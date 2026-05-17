import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.files_agent import FilesAgent
from app.agents.orchestrator import run_turn as orchestrator_run_turn
from app.agents.registry import REGISTRY
from app.db.models import Attachment, Message, Session, User


# FilesAgent is stateless (only name/tools/model property); single module-level
# instance avoids reallocating per request.
_files = FilesAgent()


class UnknownDomainError(LookupError):
    """Raised when chat/{domain} hits an unregistered domain. Router translates to HTTP 404."""


class ChatService:
    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user

    # ---- Session lifecycle ------------------------------------------------

    async def get_or_create_scoped_session(
        self,
        *,
        scope: str,
        device_id: UUID | None,
        device_name: str | None,
    ) -> Session:
        stmt = (
            select(Session)
            .where(
                Session.user_id == self.user.id,
                Session.device_id == device_id,
                Session.scope == scope,
                Session.ended_at.is_(None),
            )
            .order_by(Session.created_at.desc())
            .limit(1)
        )
        sess = (await self.session.scalars(stmt)).first()
        if sess is not None:
            if device_name and sess.device_name != device_name:
                sess.device_name = device_name
            return sess
        sess = Session(
            user_id=self.user.id,
            scope=scope,
            device_id=device_id,
            device_name=device_name,
        )
        self.session.add(sess)
        await self.session.flush()
        return sess

    # ---- Attachments ------------------------------------------------------

    async def save_attachments(
        self,
        *,
        session_id: UUID,
        raw_files: list[tuple[bytes, str, str]],
    ) -> list[Attachment]:
        out: list[Attachment] = []
        for raw, name, mime in raw_files:
            att = await _files.save_attachment(
                self.session,
                user=self.user,
                raw=raw,
                original_name=name,
                mime=mime,
                session_id=session_id,
            )
            out.append(att)
        return out

    # ---- Context loading --------------------------------------------------

    async def load_recent(
        self,
        *,
        session_id: UUID,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(Message)
            .where(
                Message.session_id == session_id,
                Message.role.in_(["user", "assistant"]),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = list((await self.session.scalars(stmt)).all())
        rows.reverse()
        return [{"role": m.role, "content": m.content} for m in rows]

    # ---- Turn persistence -------------------------------------------------

    async def persist_turn(
        self,
        *,
        session: Session,
        user_message: str,
        attachments: list[Attachment],
        result: dict[str, Any],
    ) -> None:
        extra = {"attachment_ids": [str(a.id) for a in attachments]} if attachments else None
        self.session.add(Message(session_id=session.id, role="user", content=user_message, extra=extra))
        self.session.add(
            Message(
                session_id=session.id,
                role="assistant",
                content=result.get("assistant_message", ""),
            )
        )
        for tc in result.get("tool_calls", []):
            self.session.add(
                Message(
                    session_id=session.id,
                    role="tool",
                    content=json.dumps(tc, ensure_ascii=False),
                    extra=tc,
                )
            )

    # ---- Public entry points ---------------------------------------------

    async def run_orchestrator(
        self,
        *,
        message: str,
        device_id: UUID | None,
        device_name: str | None,
        raw_files: list[tuple[bytes, str, str]],
    ) -> dict[str, Any]:
        sess = await self.get_or_create_scoped_session(
            scope="orchestrator", device_id=device_id, device_name=device_name
        )
        attachments = await self.save_attachments(
            session_id=sess.id, raw_files=raw_files
        )
        result = await orchestrator_run_turn(
            self.session,
            user=self.user,
            session_id=sess.id,
            user_message=message,
            device_id=device_id,
            device_name=device_name,
        )
        await self.persist_turn(
            session=sess,
            user_message=message,
            attachments=attachments,
            result=result,
        )
        return result

    async def run_domain(
        self,
        domain: str,
        *,
        message: str,
        device_id: UUID | None,
        device_name: str | None,
        raw_files: list[tuple[bytes, str, str]],
    ) -> dict[str, Any]:
        if domain not in REGISTRY:
            raise UnknownDomainError(domain)
        sess = await self.get_or_create_scoped_session(
            scope=domain, device_id=device_id, device_name=device_name
        )
        attachments = await self.save_attachments(
            session_id=sess.id, raw_files=raw_files
        )
        recent = await self.load_recent(session_id=sess.id)
        agent = REGISTRY[domain]
        result = await agent.run_turn(
            self.session,
            user=self.user,
            session_id=sess.id,
            user_message=message,
            recent_messages=recent,
            attachments=attachments,
        )
        await self.persist_turn(
            session=sess,
            user_message=message,
            attachments=attachments,
            result=result,
        )
        return result
