from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._chat_input import parse_input
from app.api.schemas.chat import ChatResponse
from app.db.models import User
from app.db.session import get_session
from app.services.chat_service import ChatService, UnknownDomainError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def post_chat(
    request: Request, db: AsyncSession = Depends(get_session)
) -> ChatResponse:
    parsed = await parse_input(request)
    user = await db.get(User, parsed.user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    svc = ChatService(db, user)
    result = await svc.run_orchestrator(
        message=parsed.message,
        device_id=parsed.device_id,
        device_name=parsed.device_name,
        raw_files=parsed.raw_files,
    )
    await db.commit()
    return ChatResponse(**result)


@router.post("/{domain}", response_model=ChatResponse)
async def post_domain_chat(
    domain: str, request: Request, db: AsyncSession = Depends(get_session)
) -> ChatResponse:
    parsed = await parse_input(request)
    user = await db.get(User, parsed.user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    svc = ChatService(db, user)
    try:
        result = await svc.run_domain(
            domain,
            message=parsed.message,
            device_id=parsed.device_id,
            device_name=parsed.device_name,
            raw_files=parsed.raw_files,
        )
    except UnknownDomainError:
        raise HTTPException(404, f"unknown domain: {domain}")
    await db.commit()
    return ChatResponse(**result)
