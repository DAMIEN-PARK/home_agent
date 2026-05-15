from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services.schedule_service import create_local_event, list_events


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


async def handle_intent(
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
