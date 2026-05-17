import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.files_agent import FilesAgent
from app.agents.orchestrator import run_turn as orchestrator_run_turn
from app.agents.registry import REGISTRY
from app.api.schemas.chat import ChatResponse
from app.db.models import Attachment, Message, Session, User
from app.db.session import get_session

router = APIRouter(prefix="/chat", tags=["chat"])

_files = FilesAgent()


class _ParsedInput:
    __slots__ = ("message", "user_id", "session_id", "device_id", "device_name", "raw_files")

    def __init__(
        self,
        *,
        message: str,
        user_id: UUID,
        session_id: UUID | None,
        device_id: UUID | None,
        device_name: str | None,
        raw_files: list[tuple[bytes, str, str]],
    ):
        self.message = message
        self.user_id = user_id
        self.session_id = session_id
        self.device_id = device_id
        self.device_name = device_name
        self.raw_files = raw_files


def _header_uuid(request: Request, name: str) -> UUID | None:
    raw = request.headers.get(name)
    return UUID(raw) if raw else None


async def _parse_input(request: Request) -> _ParsedInput:
    ct = request.headers.get("content-type", "")
    device_id = _header_uuid(request, "X-Device-Id")
    device_name = request.headers.get("X-Device-Name")

    if ct.startswith("multipart/"):
        form = await request.form()
        message = str(form.get("message", ""))
        user_id_raw = form.get("user_id")
        session_id_raw = form.get("session_id")
        files_field = form.getlist("attachments") if "attachments" in form else []
        raw_files: list[tuple[bytes, str, str]] = []
        for f in files_field:
            # UploadFile-like duck typing: filename + content_type + read()
            data = await f.read()
            raw_files.append((data, f.filename or "upload.bin", f.content_type or "application/octet-stream"))
        if user_id_raw is None:
            raise HTTPException(422, "user_id is required")
        return _ParsedInput(
            message=message,
            user_id=UUID(str(user_id_raw)),
            session_id=UUID(str(session_id_raw)) if session_id_raw else None,
            device_id=device_id,
            device_name=device_name,
            raw_files=raw_files,
        )

    body = await request.json()
    return _ParsedInput(
        message=body["message"],
        user_id=UUID(body["user_id"]),
        session_id=UUID(body["session_id"]) if body.get("session_id") else None,
        device_id=device_id,
        device_name=device_name,
        raw_files=[],
    )


async def _get_or_create_scoped_session(
    db: AsyncSession,
    *,
    user: User,
    scope: str,
    device_id: UUID | None,
    device_name: str | None,
) -> Session:
    stmt = (
        select(Session)
        .where(
            Session.user_id == user.id,
            Session.device_id == device_id,
            Session.scope == scope,
            Session.ended_at.is_(None),
        )
        .order_by(Session.created_at.desc())
        .limit(1)
    )
    sess = (await db.scalars(stmt)).first()
    if sess is not None:
        if device_name and sess.device_name != device_name:
            sess.device_name = device_name
        return sess
    sess = Session(
        user_id=user.id,
        scope=scope,
        device_id=device_id,
        device_name=device_name,
    )
    db.add(sess)
    await db.flush()
    return sess


async def _load_recent_messages(
    db: AsyncSession, *, session_id: UUID, limit: int = 10
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
    rows = list((await db.scalars(stmt)).all())
    rows.reverse()
    return [{"role": m.role, "content": m.content} for m in rows]


async def _save_attachments(
    db: AsyncSession,
    *,
    user: User,
    session_id: UUID,
    raw_files: list[tuple[bytes, str, str]],
) -> list[Attachment]:
    out: list[Attachment] = []
    for raw, name, mime in raw_files:
        att = await _files.save_attachment(
            db,
            user=user,
            raw=raw,
            original_name=name,
            mime=mime,
            session_id=session_id,
        )
        out.append(att)
    return out


async def _persist_turn(
    db: AsyncSession,
    *,
    session: Session,
    user_message: str,
    attachments: list[Attachment],
    result: dict[str, Any],
) -> None:
    extra = {"attachment_ids": [str(a.id) for a in attachments]} if attachments else None
    db.add(Message(session_id=session.id, role="user", content=user_message, extra=extra))
    db.add(
        Message(
            session_id=session.id,
            role="assistant",
            content=result.get("assistant_message", ""),
        )
    )
    for tc in result.get("tool_calls", []):
        db.add(
            Message(
                session_id=session.id,
                role="tool",
                content=json.dumps(tc, ensure_ascii=False),
                extra=tc,
            )
        )


@router.post("", response_model=ChatResponse)
async def post_chat(
    request: Request, db: AsyncSession = Depends(get_session)
) -> ChatResponse:
    parsed = await _parse_input(request)

    user = await db.get(User, parsed.user_id)
    if user is None:
        raise HTTPException(404, "user not found")

    sess = await _get_or_create_scoped_session(
        db,
        user=user,
        scope="orchestrator",
        device_id=parsed.device_id,
        device_name=parsed.device_name,
    )
    attachments = await _save_attachments(
        db, user=user, session_id=sess.id, raw_files=parsed.raw_files
    )
    result = await orchestrator_run_turn(
        db,
        user=user,
        session_id=sess.id,
        user_message=parsed.message,
        device_id=parsed.device_id,
        device_name=parsed.device_name,
    )
    await _persist_turn(
        db,
        session=sess,
        user_message=parsed.message,
        attachments=attachments,
        result=result,
    )
    await db.commit()
    return ChatResponse(**result)


@router.post("/{domain}", response_model=ChatResponse)
async def post_domain_chat(
    domain: str, request: Request, db: AsyncSession = Depends(get_session)
) -> ChatResponse:
    if domain not in REGISTRY:
        raise HTTPException(404, f"unknown domain: {domain}")

    parsed = await _parse_input(request)

    user = await db.get(User, parsed.user_id)
    if user is None:
        raise HTTPException(404, "user not found")

    sess = await _get_or_create_scoped_session(
        db,
        user=user,
        scope=domain,
        device_id=parsed.device_id,
        device_name=parsed.device_name,
    )
    attachments = await _save_attachments(
        db, user=user, session_id=sess.id, raw_files=parsed.raw_files
    )
    recent = await _load_recent_messages(db, session_id=sess.id)
    agent = REGISTRY[domain]
    result = await agent.run_turn(
        db,
        user=user,
        session_id=sess.id,
        user_message=parsed.message,
        recent_messages=recent,
        attachments=attachments,
    )
    await _persist_turn(
        db,
        session=sess,
        user_message=parsed.message,
        attachments=attachments,
        result=result,
    )
    await db.commit()
    return ChatResponse(**result)
