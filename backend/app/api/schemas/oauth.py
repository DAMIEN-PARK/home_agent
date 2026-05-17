from pydantic import BaseModel


class OAuthCallbackResponse(BaseModel):
    ok: bool
    scope: str | None = None
