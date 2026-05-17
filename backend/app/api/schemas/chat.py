from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    user_id: UUID
    session_id: UUID | None = None


class ToolCallOut(BaseModel):
    name: str
    result: dict[str, Any]


class ChatResponse(BaseModel):
    assistant_message: str
    tool_calls: list[ToolCallOut]
