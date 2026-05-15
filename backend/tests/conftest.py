import asyncio
import os
import subprocess
from typing import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.db.models import User


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg


@pytest_asyncio.fixture(scope="session")
async def db_engine(postgres_container):
    raw_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )
    engine = create_async_engine(raw_url, future=True)

    # Run alembic migrations against this container
    env = {**os.environ, "DATABASE_URL": raw_url}
    subprocess.run(["alembic", "upgrade", "head"], check=True, cwd="backend", env=env)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    SessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session) -> User:
    user = User(id=uuid4(), name="test_user")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def app_client(db_engine, monkeypatch) -> AsyncIterator[AsyncClient]:
    """ASGI test client with the app's session factory pointing at the test DB."""
    from app.db import session as session_module
    from app.main import app

    test_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    monkeypatch.setattr(session_module, "_session_factory", test_factory)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
