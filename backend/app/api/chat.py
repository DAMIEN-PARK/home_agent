from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_turn
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    user_id: UUID
    session_id: UUID | None = None


class ChatResponse(BaseModel):
    assistant_message: str
    tool_calls: list[dict]


@router.post("", response_model=ChatResponse)
async def post_chat(
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    user = await session.get(User, req.user_id)
    if user is None:
        raise HTTPException(404, "user not found")

    result = await run_turn(
        session,
        user=user,
        session_id=req.session_id,
        user_message=req.message,
    )
    return ChatResponse(**result)
