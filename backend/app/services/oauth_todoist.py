"""Todoist OAuth v2 handshake. Mirrors GoogleOAuthService pattern.

Todoist OAuth returns a long-lived access_token (no refresh_token).
MA-1 (meta-roadmap) requires 3-key shape; refresh_token stored as None.
"""
from dataclasses import dataclass
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User


TODOIST_AUTH_URL = "https://todoist.com/oauth/authorize"
TODOIST_TOKEN_URL = "https://todoist.com/oauth/access_token"
SCOPES = "data:read_write"


class TodoistOAuthConfigError(ValueError):
    """Raised when required Todoist OAuth env vars are missing."""


@dataclass
class OAuthCallbackResult:
    ok: bool
    scope: str | None


class TodoistOAuthService:
    """Encapsulates Todoist OAuth handshake. httpx client is injectable for tests."""

    def __init__(self, http: httpx.AsyncClient | None = None):
        self._http = http

    def build_auth_url(self, user_id: UUID | None) -> str:
        s = get_settings()
        if not s.todoist_client_id:
            raise TodoistOAuthConfigError("TODOIST_CLIENT_ID not set")
        params = {
            "client_id": s.todoist_client_id,
            "scope": SCOPES,
            "state": str(user_id) if user_id else "",
        }
        return f"{TODOIST_AUTH_URL}?{urlencode(params)}"

    async def _exchange_code(self, code: str) -> dict:
        s = get_settings()
        data = {
            "client_id": s.todoist_client_id,
            "client_secret": s.todoist_client_secret,
            "code": code,
            "redirect_uri": s.todoist_redirect_uri,
        }
        if self._http is not None:
            resp = await self._http.post(TODOIST_TOKEN_URL, data=data)
        else:
            async with httpx.AsyncClient() as http:
                resp = await http.post(TODOIST_TOKEN_URL, data=data)
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
                # MA-1 strict 3-key shape: Todoist has no refresh_token
                existing["todoist"] = {
                    "access_token": token.get("access_token"),
                    "refresh_token": None,
                    "scope": token.get("scope"),
                }
                user.external_tokens = existing
                await session.commit()

        return OAuthCallbackResult(ok=True, scope=token.get("scope"))
