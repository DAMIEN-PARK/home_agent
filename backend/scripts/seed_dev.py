"""Seed dev DB with a default user + sample data. Idempotent.

Usage (from backend/):
    python -m scripts.seed_dev
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.models import Event, Project, Task, TaskContext, User
from app.db.session import get_engine

SEED_EMAIL = "damien@bctone.kr"
SEED_NAME = "damien"
SEED_PROJECT = "Home Agent"
SEED_CONTEXT = "@home"
SEED_TASK_TITLES = ["Inbox 정리", "주간 회고", "독서 30분"]
SEED_EVENT_PREFIX = "seed:dev:"


async def _seed(session: AsyncSession) -> None:
    user = (
        await session.scalars(select(User).where(User.email == SEED_EMAIL))
    ).first()
    if user is None:
        user = User(email=SEED_EMAIL, name=SEED_NAME)
        session.add(user)
        await session.flush()
        print(f"[seed] created user {user.email}")
    else:
        print(f"[seed] user {user.email} exists")

    project = (
        await session.scalars(
            select(Project).where(
                Project.user_id == user.id, Project.name == SEED_PROJECT
            )
        )
    ).first()
    if project is None:
        project = Project(
            user_id=user.id, name=SEED_PROJECT, description="Default seeded project"
        )
        session.add(project)
        await session.flush()
        print(f"[seed] created project {project.name}")

    ctx = (
        await session.scalars(
            select(TaskContext).where(
                TaskContext.user_id == user.id, TaskContext.name == SEED_CONTEXT
            )
        )
    ).first()
    if ctx is None:
        ctx = TaskContext(user_id=user.id, name=SEED_CONTEXT)
        session.add(ctx)
        await session.flush()
        print(f"[seed] created context {ctx.name}")

    existing_task_titles = set(
        (
            await session.scalars(
                select(Task.title).where(
                    Task.user_id == user.id, Task.title.in_(SEED_TASK_TITLES)
                )
            )
        ).all()
    )
    for title in SEED_TASK_TITLES:
        if title in existing_task_titles:
            continue
        session.add(
            Task(
                user_id=user.id,
                project_id=project.id,
                context_id=ctx.id,
                title=title,
                priority=3,
            )
        )
        print(f"[seed] created task {title}")

    now = datetime.now(timezone.utc)
    seed_events = [
        (f"{SEED_EVENT_PREFIX}1", "오늘 일정 샘플", now + timedelta(hours=2)),
        (f"{SEED_EVENT_PREFIX}2", "내일 일정 샘플", now + timedelta(days=1, hours=10)),
    ]
    for ext_id, title, start_at in seed_events:
        existing = (
            await session.scalars(
                select(Event).where(
                    Event.source == "local", Event.external_id == ext_id
                )
            )
        ).first()
        if existing is not None:
            continue
        session.add(
            Event(
                user_id=user.id,
                source="local",
                external_id=ext_id,
                title=title,
                start_at=start_at,
            )
        )
        print(f"[seed] created event {title}")

    await session.commit()


async def run() -> None:
    settings = get_settings()
    if settings.environment == "production":
        raise SystemExit("[seed] refusing to run against production environment")

    engine = get_engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await _seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
