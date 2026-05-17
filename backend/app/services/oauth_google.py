from dataclasses import dataclass
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/calendar.readonly"


class GoogleOAuthConfigError(ValueError):
    """Raised when required Google OAuth env vars are missing."""


@dataclass
class OAuthCallbackResult:
    ok: bool
    scope: str | None


class GoogleOAuthService:
    """Encapsulates Google OAuth handshake. httpx client is injectable for tests."""

    def __init__(self, http: httpx.AsyncClient | None = None):
        self._http = http

    def build_auth_url(self, user_id: UUID | None) -> str:
        s = get_settings()
        if not s.google_oauth_client_id:
            raise GoogleOAuthConfigError("GOOGLE_OAUTH_CLIENT_ID not set")
        params = {
            "client_id": s.google_oauth_client_id,
            "redirect_uri": s.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": str(user_id) if user_id else "",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def _exchange_code(self, code: str) -> dict:
        s = get_settings()
        data = {
            "code": code,
            "client_id": s.google_oauth_client_id,
            "client_secret": s.google_oauth_client_secret,
            "redirect_uri": s.google_oauth_redirect_uri,
            "grant_type": "authorization_code",
        }
        if self._http is not None:
            resp = await self._http.post(GOOGLE_TOKEN_URL, data=data)
        else:
            async with httpx.AsyncClient() as http:
                resp = await http.post(GOOGLE_TOKEN_URL, data=data)
        resp.raise_for_status()
        return resp.json()

    async def handle_callback(
        self,
        session: AsyncSession,
        *,
        code: str,
        state: str,
    ) -> OAuthCallbackResult:
        token = await self._exchange_code(code)

        if state:
            user = await session.get(User, UUID(state))
            if user is not None:
                existing = user.external_tokens or {}
                existing["google"] = {
                    "refresh_token": token.get("refresh_token"),
                    "scope": token.get("scope"),
                }
                user.external_tokens = existing
                await session.commit()

        return OAuthCallbackResult(ok=True, scope=token.get("scope"))
