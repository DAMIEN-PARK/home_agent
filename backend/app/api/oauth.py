from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.oauth import OAuthCallbackResponse
from app.db.session import get_session
from app.services.oauth_google import GoogleOAuthConfigError, GoogleOAuthService

router = APIRouter(prefix="/oauth/google", tags=["oauth"])


@router.get("/start")
async def oauth_start(user_id: UUID | None = None) -> RedirectResponse:
    try:
        url = GoogleOAuthService().build_auth_url(user_id)
    except GoogleOAuthConfigError as e:
        raise HTTPException(500, str(e)) from e
    return RedirectResponse(url, status_code=302)


@router.get("/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(""),
    session: AsyncSession = Depends(get_session),
) -> OAuthCallbackResponse:
    result = await GoogleOAuthService().handle_callback(session, code=code, state=state)
    return OAuthCallbackResponse(ok=result.ok, scope=result.scope)
