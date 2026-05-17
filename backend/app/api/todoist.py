"""On-demand Todoist sync endpoint.

Triggered by user (or TodoAgent.sync_todoist tool). No cron/webhook in Phase 5.
"""
from time import perf_counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.todoist import TodoistSyncResponse
from app.core.logging import get_logger
from app.db.models import User
from app.db.session import get_session
from app.services.todoist import TodoistAuthError, TodoistClient
from app.services.todoist_sync import sync_user_todoist


router = APIRouter(prefix="/todoist", tags=["todoist"])
log = get_logger("todoist")


@router.post("/sync", response_model=TodoistSyncResponse)
async def sync_todoist(
    user_id: UUID = Query(...),
    db: AsyncSession = Depends(get_session),
) -> TodoistSyncResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")

    tokens = (user.external_tokens or {}).get("todoist") or {}
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            422,
            "Todoist token not configured. Re-authenticate at /oauth/todoist/start.",
        )

    started = perf_counter()
    async with TodoistClient(access_token) as client:
        try:
            result = await sync_user_todoist(db, user=user, client=client)
        except TodoistAuthError:
            user.external_tokens["todoist"] = None
            await db.commit()
            raise HTTPException(
                422,
                "Todoist token revoked. Re-authenticate at /oauth/todoist/start.",
            )

    duration_ms = int((perf_counter() - started) * 1000)
    log.info(
        "todoist.sync",
        synced=result["synced"],
        pushed=result["pushed"],
        tombstoned=result["tombstoned"],
        errors=result["errors"],
        duration_ms=duration_ms,
    )
    return TodoistSyncResponse(**result)
