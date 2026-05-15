from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/oauth/google", tags=["oauth"])

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/calendar.readonly"


@router.get("/start")
async def oauth_start(user_id: UUID | None = None) -> RedirectResponse:
    s = get_settings()
    if not s.google_oauth_client_id:
        raise HTTPException(500, "GOOGLE_OAUTH_CLIENT_ID not set")

    params = {
        "client_id": s.google_oauth_client_id,
        "redirect_uri": s.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": str(user_id) if user_id else "",
    }
    return RedirectResponse(f"{GOOGLE_AUTH}?{urlencode(params)}", status_code=302)


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(""),
    session: AsyncSession = Depends(get_session),
) -> dict:
    s = get_settings()
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            GOOGLE_TOKEN,
            data={
                "code": code,
                "client_id": s.google_oauth_client_id,
                "client_secret": s.google_oauth_client_secret,
                "redirect_uri": s.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    resp.raise_for_status()
    token = resp.json()

    if state:
        user = await session.get(User, UUID(state))
        if user:
            existing = user.external_tokens or {}
            existing["google"] = {
                "refresh_token": token.get("refresh_token"),
                "scope": token.get("scope"),
            }
            user.external_tokens = existing
            await session.commit()

    return {"ok": True, "scope": token.get("scope")}
