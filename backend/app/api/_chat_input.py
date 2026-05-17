from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, Request


@dataclass(slots=True)
class ParsedInput:
    message: str
    user_id: UUID
    session_id: UUID | None
    device_id: UUID | None
    device_name: str | None
    raw_files: list[tuple[bytes, str, str]]


def _header_uuid(request: Request, name: str) -> UUID | None:
    raw = request.headers.get(name)
    return UUID(raw) if raw else None


async def parse_input(request: Request) -> ParsedInput:
    """Parse multipart/form-data or JSON body into a ParsedInput.

    Raises HTTPException(422) when user_id is missing in multipart payload.
    """
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
        return ParsedInput(
            message=message,
            user_id=UUID(str(user_id_raw)),
            session_id=UUID(str(session_id_raw)) if session_id_raw else None,
            device_id=device_id,
            device_name=device_name,
            raw_files=raw_files,
        )

    body = await request.json()
    return ParsedInput(
        message=body["message"],
        user_id=UUID(body["user_id"]),
        session_id=UUID(body["session_id"]) if body.get("session_id") else None,
        device_id=device_id,
        device_name=device_name,
        raw_files=[],
    )
