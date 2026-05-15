from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.core import User
from app.db.session import get_session

DEFAULT_USER_NAME = "default"


async def get_default_user(session: AsyncSession = Depends(get_session)) -> User:
    """MVP single-user bootstrap: return the default user, creating it on first call."""
    user = (
        await session.scalars(select(User).where(User.name == DEFAULT_USER_NAME))
    ).first()
    if user is None:
        user = User(name=DEFAULT_USER_NAME)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def get_default_user_id(user: User = Depends(get_default_user)) -> UUID:
    return user.id
