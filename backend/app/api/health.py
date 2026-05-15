from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
async def db_health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    result = await session.execute(text("SELECT 1"))
    value = result.scalar_one()
    return {"status": "ok", "db": "up" if value == 1 else "down"}
