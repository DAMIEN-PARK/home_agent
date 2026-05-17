from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.oauth import OAuthCallbackResponse
from app.db.session import get_session
from app.services.oauth_google import GoogleOAuthConfigError, GoogleOAuthService
from app.services.oauth_todoist import TodoistOAuthConfigError, TodoistOAuthService

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/google/start")
async def oauth_google_start(user_id: UUID | None = None) -> RedirectResponse:
    try:
        url = GoogleOAuthService().build_auth_url(user_id)
    except GoogleOAuthConfigError as e:
        raise HTTPException(500, str(e)) from e
    return RedirectResponse(url, status_code=302)


@router.get("/google/callback", response_model=OAuthCallbackResponse)
async def oauth_google_callback(
    code: str = Query(...),
    state: str = Query(""),
    session: AsyncSession = Depends(get_session),
) -> OAuthCallbackResponse:
    result = await GoogleOAuthService().handle_callback(session, code=code, state=state)
    return OAuthCallbackResponse(ok=result.ok, scope=result.scope)


@router.get("/todoist/start")
async def oauth_todoist_start(user_id: UUID | None = None) -> RedirectResponse:
    try:
        url = TodoistOAuthService().build_auth_url(user_id)
    except TodoistOAuthConfigError as e:
        raise HTTPException(500, str(e)) from e
    return RedirectResponse(url, status_code=302)


@router.get("/todoist/callback", response_model=OAuthCallbackResponse)
async def oauth_todoist_callback(
    code: str = Query(...),
    state: str = Query(""),
    session: AsyncSession = Depends(get_session),
) -> OAuthCallbackResponse:
    result = await TodoistOAuthService().handle_callback(session, code=code, state=state)
    return OAuthCallbackResponse(ok=result.ok, scope=result.scope)
