# Week 1 Implementation Plan — 일정 도메인 도그푸딩 활성화

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 챗에서 "내일 3시 회의 잡아줘" → DB에 일정 저장 → 캘린더 화면에서 확인. Google Calendar 기존 일정이 캘린더 화면에 함께 표시됨.

**Architecture:** FastAPI 단일 프로세스 안에 orchestrator(Claude Agent SDK) + schedule_agent 호스팅. MCP 서버 분리는 v0.2로 미루고 agent들은 service 모듈 직접 호출 (orchestrator → tool → service → DB). Google Calendar는 별도 서비스로 추상화, APScheduler 15분 cron으로 sync. 프론트엔드는 chat + calendar 두 페이지만.

**Tech Stack:** FastAPI · Claude Agent SDK · SQLAlchemy 2 async · Alembic · APScheduler · Google OAuth (offline, refresh token) · React 18 + Vite + TS + Tailwind · React Router · TanStack Query · pytest + httpx-AsyncClient · testcontainers-python (Postgres) · vitest + React Testing Library · docker-compose.

**Scope:** Spec `docs/superpowers/specs/2026-05-15-mvp-v0.1-design.md` §3 Week 1만. TODO/가계부/대시보드/다이제스트는 후속 plan.

---

## File Structure

```
backend/
  app/
    db/models/
      schedule.py           # CREATE — Event 모델
      core.py               # MODIFY — User.external_tokens JSONB 컬럼 추가
    services/
      schedule_service.py   # CREATE — 일정 CRUD (DB 직접 접근)
      google_calendar.py    # CREATE — Google OAuth + Calendar API 클라이언트
      calendar_sync.py      # CREATE — Google → schedule.events upsert
    agents/
      orchestrator.py       # CREATE — Claude Agent SDK 호출, tool 디스패치
      schedule_agent.py     # CREATE — orchestrator가 호출하는 tool 래퍼
    api/
      chat.py               # CREATE — POST /chat
      events.py             # CREATE — GET /events
      oauth.py              # CREATE — Google OAuth start/callback
    scheduler.py            # CREATE — APScheduler 설정
    core/config.py          # MODIFY — Google OAuth 설정 필드
    main.py                 # MODIFY — 라우터/스케줄러 등록
  alembic/versions/
    0003_schedule_events_and_external_tokens.py  # CREATE
  tests/
    conftest.py             # CREATE — testcontainers fixture
    test_schedule_service.py    # CREATE
    test_google_calendar.py     # CREATE
    test_calendar_sync.py       # CREATE
    test_orchestrator.py        # CREATE
    test_chat_api.py            # CREATE — 통합 테스트
    test_events_api.py          # CREATE
  pyproject.toml           # MODIFY — dev deps: pytest-httpx, testcontainers, freezegun

frontend/
  src/
    App.tsx                # MODIFY — BrowserRouter + 라우트
    main.tsx               # MODIFY — QueryClient provider
    lib/
      api.ts               # CREATE — fetch wrapper
      queryClient.ts       # CREATE
    components/
      Sidebar.tsx          # CREATE
    pages/
      Chat.tsx             # CREATE
      Calendar.tsx         # CREATE
    __tests__/
      Chat.test.tsx        # CREATE
      Calendar.test.tsx    # CREATE
  Dockerfile               # CREATE
  package.json             # MODIFY — react-router-dom, @tanstack/react-query, vitest, RTL

docker-compose.yml         # MODIFY — frontend 서비스 추가
```

**Decomposition principle:** 각 task는 1 file(또는 동시 변경되는 짝)만 건드린다. 백엔드는 service → agent → api → main 통합 → scheduler 순(아래에서 위로). 프론트엔드는 routing → 페이지 → docker 순.

---

## Task 0: 의존성 및 환경 변수 추가

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Modify: `frontend/package.json`

- [ ] **Step 1: 백엔드 dev deps 추가**

`backend/pyproject.toml`의 `dev` extras에 추가:

```toml
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-httpx>=0.32",
    "testcontainers[postgres]>=4.8",
    "freezegun>=1.5",
    "ruff>=0.8",
    "mypy>=1.13",
]
```

`google-auth-oauthlib`와 `google-api-python-client`를 main deps에 추가:

```toml
dependencies = [
    # ... 기존 ...
    "google-auth>=2.36",
    "google-auth-oauthlib>=1.2",
    "google-api-python-client>=2.150",
]
```

- [ ] **Step 2: config.py에 Google OAuth 설정 추가**

`backend/app/core/config.py`의 `Settings` 클래스에 필드 추가:

```python
class Settings(BaseSettings):
    # ... 기존 ...
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/oauth/google/callback"
    google_calendar_id: str = "primary"
```

- [ ] **Step 3: .env.example 갱신**

`backend/.env.example`에 추가:

```
ANTHROPIC_API_KEY=
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/oauth/google/callback
GOOGLE_CALENDAR_ID=primary
```

- [ ] **Step 4: 프론트엔드 deps 추가**

`frontend/package.json`의 `dependencies`에 추가:

```json
"react-router-dom": "^7.0.2",
"@tanstack/react-query": "^5.62.0"
```

`devDependencies`에 추가:

```json
"vitest": "^2.1.6",
"@vitest/ui": "^2.1.6",
"@testing-library/react": "^16.1.0",
"@testing-library/jest-dom": "^6.6.3",
"@testing-library/user-event": "^14.5.2",
"jsdom": "^25.0.1"
```

`scripts`에 추가:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 5: 설치 실행 후 커밋**

```bash
cd backend && pip install -e '.[dev]'
cd ../frontend && npm install
cd .. && git add backend/pyproject.toml backend/app/core/config.py backend/.env.example frontend/package.json frontend/package-lock.json
git commit -m "feat(deps): add Google API, testcontainers, vitest, react-router for Week 1"
```

---

## Task 1: schedule.events 모델 + User.external_tokens 컬럼

**Files:**
- Create: `backend/app/db/models/schedule.py`
- Modify: `backend/app/db/models/core.py:11-19` (User에 external_tokens 추가)
- Modify: `backend/app/db/models/__init__.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_models.py` (없으면 생성):

```python
import pytest
from datetime import datetime, timedelta, timezone

from app.db.models import Event, User


def test_event_required_fields():
    event = Event(
        user_id="00000000-0000-0000-0000-000000000001",
        title="Test",
        start_at=datetime.now(timezone.utc),
    )
    assert event.source == "local"  # 기본값
    assert event.external_id is None


def test_user_has_external_tokens():
    user = User(name="me", external_tokens={"google": {"refresh_token": "x"}})
    assert user.external_tokens["google"]["refresh_token"] == "x"
```

- [ ] **Step 2: 테스트가 import error로 실패하는지 확인**

```bash
cd backend && pytest tests/test_models.py -v
```
Expected: `ImportError: cannot import name 'Event'`

- [ ] **Step 3: Event 모델 작성**

`backend/app/db/models/schedule.py` 생성:

```python
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_events_source_external"),
        Index("ix_schedule_events_user_start", "user_id", "start_at"),
        {"schema": "schedule"},
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="local")
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: User에 external_tokens 컬럼 추가**

`backend/app/db/models/core.py:11-19`의 User 클래스를 수정:

```python
class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    # OAuth tokens per external service: {"google": {"refresh_token": "...", ...}}
    external_tokens: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
```

- [ ] **Step 5: models/__init__.py에 Event export**

`backend/app/db/models/__init__.py` 수정:

```python
from app.db.models.core import AgentRun, Message, Session, User
from app.db.models.memory import MemoryEntry
from app.db.models.schedule import Event
from app.db.models.todo import Project, Task, TaskContext

__all__ = [
    "User", "Session", "Message", "AgentRun",
    "MemoryEntry",
    "Event",
    "Project", "Task", "TaskContext",
]
```

- [ ] **Step 6: 테스트 재실행**

```bash
cd backend && pytest tests/test_models.py -v
```
Expected: 2 PASS

- [ ] **Step 7: 커밋**

```bash
git add backend/app/db/models/schedule.py backend/app/db/models/core.py backend/app/db/models/__init__.py backend/tests/test_models.py
git commit -m "feat(db): add schedule.Event model and User.external_tokens column"
```

---

## Task 2: Alembic 마이그레이션 0003

**Files:**
- Create: `backend/alembic/versions/0003_schedule_events_and_external_tokens.py`

- [ ] **Step 1: 마이그레이션 파일 작성**

`backend/alembic/versions/0003_schedule_events_and_external_tokens.py`:

```python
"""schedule.events table and core.users.external_tokens column

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("external_tokens", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="core",
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="local"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["core.users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("source", "external_id", name="uq_events_source_external"),
        schema="schedule",
    )
    op.create_index(
        "ix_schedule_events_user_start",
        "events",
        ["user_id", "start_at"],
        schema="schedule",
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_events_user_start", table_name="events", schema="schedule")
    op.drop_table("events", schema="schedule")
    op.drop_column("users", "external_tokens", schema="core")
```

- [ ] **Step 2: 마이그레이션 적용 (postgres 컨테이너 필요)**

```bash
docker compose up -d postgres
cd backend && alembic upgrade head
```
Expected: `INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003`

- [ ] **Step 3: psql로 테이블 확인**

```bash
docker exec -it home_agent_postgres psql -U home_agent -d home_agent -c "\dt schedule.*"
```
Expected: `schedule | events` 표시

- [ ] **Step 4: 커밋**

```bash
git add backend/alembic/versions/0003_schedule_events_and_external_tokens.py
git commit -m "feat(db): add migration 0003 — schedule.events and external_tokens"
```

---

## Task 3: pytest conftest.py — testcontainers Postgres fixture

**Files:**
- Create: `backend/tests/__init__.py` (빈 파일)
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: 빈 __init__.py**

```bash
touch backend/tests/__init__.py
```

- [ ] **Step 2: conftest.py 작성**

`backend/tests/conftest.py`:

```python
import asyncio
from typing import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
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
    raw_url = postgres_container.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")
    engine = create_async_engine(raw_url, future=True)

    # Run alembic migrations against this container
    import os, subprocess
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
```

- [ ] **Step 3: 간단 sanity 테스트**

`backend/tests/test_conftest_sanity.py` 생성:

```python
import pytest


@pytest.mark.asyncio
async def test_db_session_works(db_session):
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_user_fixture(test_user):
    assert test_user.name == "test_user"
```

- [ ] **Step 4: 실행**

```bash
cd backend && pytest tests/test_conftest_sanity.py -v
```
Expected: 2 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/tests/__init__.py backend/tests/conftest.py backend/tests/test_conftest_sanity.py
git commit -m "test: add testcontainers Postgres fixtures for integration tests"
```

---

## Task 4: schedule_service — 일정 CRUD

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/schedule_service.py`
- Test: `backend/tests/test_schedule_service.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_schedule_service.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest

from app.services.schedule_service import create_local_event, list_events


@pytest.mark.asyncio
async def test_create_local_event(db_session, test_user):
    now = datetime.now(timezone.utc)
    event = await create_local_event(
        db_session,
        user_id=test_user.id,
        title="회의",
        start_at=now,
        end_at=now + timedelta(hours=1),
    )
    assert event.title == "회의"
    assert event.source == "local"
    assert event.external_id is None


@pytest.mark.asyncio
async def test_list_events_filters_by_time_range(db_session, test_user):
    now = datetime.now(timezone.utc)
    await create_local_event(db_session, user_id=test_user.id, title="in", start_at=now)
    await create_local_event(
        db_session,
        user_id=test_user.id,
        title="out",
        start_at=now + timedelta(days=30),
    )
    events = await list_events(
        db_session,
        user_id=test_user.id,
        from_=now - timedelta(hours=1),
        to=now + timedelta(days=1),
    )
    titles = [e.title for e in events]
    assert "in" in titles
    assert "out" not in titles
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
cd backend && pytest tests/test_schedule_service.py -v
```
Expected: ImportError

- [ ] **Step 3: schedule_service 작성**

`backend/app/services/__init__.py` 빈 파일.

`backend/app/services/schedule_service.py`:

```python
from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event


async def create_local_event(
    session: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    start_at: datetime,
    end_at: datetime | None = None,
    description: str | None = None,
) -> Event:
    event = Event(
        user_id=user_id,
        source="local",
        title=title,
        start_at=start_at,
        end_at=end_at,
        description=description,
    )
    session.add(event)
    await session.flush()
    await session.commit()
    return event


async def list_events(
    session: AsyncSession,
    *,
    user_id: UUID,
    from_: datetime,
    to: datetime,
) -> Sequence[Event]:
    stmt = (
        select(Event)
        .where(Event.user_id == user_id, Event.start_at >= from_, Event.start_at < to)
        .order_by(Event.start_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def upsert_google_event(
    session: AsyncSession,
    *,
    user_id: UUID,
    external_id: str,
    title: str,
    start_at: datetime,
    end_at: datetime | None,
    description: str | None,
    synced_at: datetime,
) -> Event:
    stmt = select(Event).where(Event.source == "google", Event.external_id == external_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.title = title
        existing.start_at = start_at
        existing.end_at = end_at
        existing.description = description
        existing.synced_at = synced_at
        await session.commit()
        return existing

    event = Event(
        user_id=user_id,
        source="google",
        external_id=external_id,
        title=title,
        start_at=start_at,
        end_at=end_at,
        description=description,
        synced_at=synced_at,
    )
    session.add(event)
    await session.commit()
    return event
```

- [ ] **Step 4: 테스트 재실행**

```bash
cd backend && pytest tests/test_schedule_service.py -v
```
Expected: 2 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/__init__.py backend/app/services/schedule_service.py backend/tests/test_schedule_service.py
git commit -m "feat(schedule): add create_local_event / list_events / upsert_google_event services"
```

---

## Task 5: google_calendar 서비스 (OAuth + list)

**Files:**
- Create: `backend/app/services/google_calendar.py`
- Test: `backend/tests/test_google_calendar.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_google_calendar.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest
from pytest_httpx import HTTPXMock

from app.services.google_calendar import GoogleCalendarClient


@pytest.mark.asyncio
async def test_list_events_parses_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url__regex=r"https://www\.googleapis\.com/calendar/v3/calendars/.*",
        json={
            "items": [
                {
                    "id": "evt_001",
                    "summary": "Standup",
                    "start": {"dateTime": "2026-05-19T10:00:00+09:00"},
                    "end": {"dateTime": "2026-05-19T10:30:00+09:00"},
                    "description": "daily standup",
                }
            ]
        },
    )

    client = GoogleCalendarClient(access_token="fake")
    events = await client.list_events(
        calendar_id="primary",
        time_min=datetime(2026, 5, 1, tzinfo=timezone.utc),
        time_max=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    assert len(events) == 1
    assert events[0]["id"] == "evt_001"
    assert events[0]["start_at"].isoformat() == "2026-05-19T01:00:00+00:00"
```

- [ ] **Step 2: 실패 확인**

```bash
cd backend && pytest tests/test_google_calendar.py -v
```
Expected: ImportError

- [ ] **Step 3: google_calendar 모듈 작성**

`backend/app/services/google_calendar.py`:

```python
from datetime import datetime
from typing import Any

import httpx


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
CAL_API_BASE = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarClient:
    def __init__(self, access_token: str, *, http: httpx.AsyncClient | None = None):
        self.access_token = access_token
        self._http = http or httpx.AsyncClient(timeout=15)

    async def list_events(
        self,
        *,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
    ) -> list[dict[str, Any]]:
        params = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 250,
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"{CAL_API_BASE}/calendars/{calendar_id}/events"
        resp = await self._http.get(url, params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

        out = []
        for item in payload.get("items", []):
            start_raw = item.get("start", {})
            end_raw = item.get("end", {})
            start_at = _parse_dt(start_raw.get("dateTime") or start_raw.get("date"))
            end_at = _parse_dt(end_raw.get("dateTime") or end_raw.get("date")) if end_raw else None
            if start_at is None:
                continue
            out.append({
                "id": item["id"],
                "summary": item.get("summary", "(제목 없음)"),
                "start_at": start_at,
                "end_at": end_at,
                "description": item.get("description"),
            })
        return out


async def exchange_refresh_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    http: httpx.AsyncClient | None = None,
) -> str:
    http = http or httpx.AsyncClient(timeout=15)
    resp = await http.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # all-day events come as "YYYY-MM-DD"; treat as UTC midnight for simplicity
    if len(value) == 10:
        return datetime.fromisoformat(value + "T00:00:00+00:00")
    return datetime.fromisoformat(value).astimezone()
```

- [ ] **Step 4: 테스트 재실행**

```bash
cd backend && pytest tests/test_google_calendar.py -v
```
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/google_calendar.py backend/tests/test_google_calendar.py
git commit -m "feat(google): add GoogleCalendarClient.list_events + refresh_token exchange"
```

---

## Task 6: calendar_sync — Google 일정을 DB에 upsert

**Files:**
- Create: `backend/app/services/calendar_sync.py`
- Test: `backend/tests/test_calendar_sync.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_calendar_sync.py`:

```python
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.calendar_sync import sync_user_google_calendar
from app.services.schedule_service import list_events


@pytest.mark.asyncio
async def test_sync_upserts_google_events(db_session, test_user, monkeypatch):
    # mock client
    fake_client = AsyncMock()
    fake_client.list_events.return_value = [
        {
            "id": "g_evt_1",
            "summary": "Standup",
            "start_at": datetime(2026, 5, 20, 1, 0, tzinfo=timezone.utc),
            "end_at": datetime(2026, 5, 20, 1, 30, tzinfo=timezone.utc),
            "description": None,
        }
    ]

    await sync_user_google_calendar(
        db_session,
        user=test_user,
        client=fake_client,
        calendar_id="primary",
        window_days_back=1,
        window_days_forward=30,
    )

    events = await list_events(
        db_session,
        user_id=test_user.id,
        from_=datetime(2026, 5, 1, tzinfo=timezone.utc),
        to=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert len(events) == 1
    assert events[0].external_id == "g_evt_1"
    assert events[0].source == "google"


@pytest.mark.asyncio
async def test_sync_is_idempotent(db_session, test_user):
    fake_client = AsyncMock()
    fake_client.list_events.return_value = [
        {
            "id": "g_evt_1",
            "summary": "Standup v1",
            "start_at": datetime(2026, 5, 20, 1, 0, tzinfo=timezone.utc),
            "end_at": None,
            "description": None,
        }
    ]
    await sync_user_google_calendar(db_session, user=test_user, client=fake_client, calendar_id="primary")

    fake_client.list_events.return_value = [
        {
            "id": "g_evt_1",
            "summary": "Standup v2",  # title changed
            "start_at": datetime(2026, 5, 20, 1, 0, tzinfo=timezone.utc),
            "end_at": None,
            "description": None,
        }
    ]
    await sync_user_google_calendar(db_session, user=test_user, client=fake_client, calendar_id="primary")

    events = await list_events(
        db_session,
        user_id=test_user.id,
        from_=datetime(2026, 5, 1, tzinfo=timezone.utc),
        to=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert len(events) == 1
    assert events[0].title == "Standup v2"
```

- [ ] **Step 2: 실패 확인**

```bash
cd backend && pytest tests/test_calendar_sync.py -v
```
Expected: ImportError

- [ ] **Step 3: calendar_sync 모듈 작성**

`backend/app/services/calendar_sync.py`:

```python
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services.schedule_service import upsert_google_event


class _CalendarClient(Protocol):
    async def list_events(
        self, *, calendar_id: str, time_min: datetime, time_max: datetime
    ) -> list[dict]: ...


async def sync_user_google_calendar(
    session: AsyncSession,
    *,
    user: User,
    client: _CalendarClient,
    calendar_id: str = "primary",
    window_days_back: int = 1,
    window_days_forward: int = 90,
) -> int:
    """Pull events from Google Calendar and upsert into schedule.events.
    Returns number of events synced."""
    now = datetime.now(timezone.utc)
    time_min = now - timedelta(days=window_days_back)
    time_max = now + timedelta(days=window_days_forward)

    raw_events = await client.list_events(
        calendar_id=calendar_id, time_min=time_min, time_max=time_max
    )

    for evt in raw_events:
        await upsert_google_event(
            session,
            user_id=user.id,
            external_id=evt["id"],
            title=evt["summary"],
            start_at=evt["start_at"],
            end_at=evt.get("end_at"),
            description=evt.get("description"),
            synced_at=now,
        )

    return len(raw_events)
```

- [ ] **Step 4: 테스트 재실행**

```bash
cd backend && pytest tests/test_calendar_sync.py -v
```
Expected: 2 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/calendar_sync.py backend/tests/test_calendar_sync.py
git commit -m "feat(schedule): sync_user_google_calendar with upsert + idempotency"
```

---

## Task 7: schedule_agent — orchestrator가 호출하는 tool 래퍼

**Files:**
- Create: `backend/app/agents/schedule_agent.py`
- Test: `backend/tests/test_schedule_agent.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_schedule_agent.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest

from app.agents.schedule_agent import handle_intent


@pytest.mark.asyncio
async def test_handle_create_event(db_session, test_user):
    result = await handle_intent(
        db_session,
        user=test_user,
        intent="create_event",
        params={
            "title": "회의",
            "start_at": "2026-05-19T15:00:00+09:00",
            "end_at": "2026-05-19T16:00:00+09:00",
        },
    )
    assert result["ok"] is True
    assert result["event"]["title"] == "회의"


@pytest.mark.asyncio
async def test_handle_list_events(db_session, test_user):
    await handle_intent(
        db_session,
        user=test_user,
        intent="create_event",
        params={"title": "x", "start_at": "2026-05-20T10:00:00+09:00"},
    )
    result = await handle_intent(
        db_session,
        user=test_user,
        intent="list_events",
        params={"from": "2026-05-01T00:00:00Z", "to": "2026-06-01T00:00:00Z"},
    )
    assert result["ok"] is True
    assert len(result["events"]) == 1


@pytest.mark.asyncio
async def test_handle_unknown_intent_returns_error(db_session, test_user):
    result = await handle_intent(db_session, user=test_user, intent="???", params={})
    assert result["ok"] is False
```

- [ ] **Step 2: 실패 확인**

```bash
cd backend && pytest tests/test_schedule_agent.py -v
```
Expected: ImportError

- [ ] **Step 3: schedule_agent 작성**

`backend/app/agents/__init__.py`는 빈 파일이면 둔다 (이미 존재).

`backend/app/agents/schedule_agent.py`:

```python
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services.schedule_service import create_local_event, list_events


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _serialize_event(e) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "title": e.title,
        "source": e.source,
        "external_id": e.external_id,
        "start_at": e.start_at.isoformat(),
        "end_at": e.end_at.isoformat() if e.end_at else None,
        "description": e.description,
    }


async def handle_intent(
    session: AsyncSession,
    *,
    user: User,
    intent: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    if intent == "create_event":
        try:
            event = await create_local_event(
                session,
                user_id=user.id,
                title=params["title"],
                start_at=_parse_iso(params["start_at"]),
                end_at=_parse_iso(params["end_at"]) if params.get("end_at") else None,
                description=params.get("description"),
            )
            return {"ok": True, "event": _serialize_event(event)}
        except (KeyError, ValueError) as exc:
            return {"ok": False, "error": f"invalid params: {exc}"}

    if intent == "list_events":
        try:
            events = await list_events(
                session,
                user_id=user.id,
                from_=_parse_iso(params["from"]),
                to=_parse_iso(params["to"]),
            )
            return {"ok": True, "events": [_serialize_event(e) for e in events]}
        except (KeyError, ValueError) as exc:
            return {"ok": False, "error": f"invalid params: {exc}"}

    return {"ok": False, "error": f"unknown intent: {intent}"}
```

- [ ] **Step 4: 테스트 재실행**

```bash
cd backend && pytest tests/test_schedule_agent.py -v
```
Expected: 3 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/agents/schedule_agent.py backend/tests/test_schedule_agent.py
git commit -m "feat(agent): schedule_agent.handle_intent for create_event / list_events"
```

---

## Task 8: orchestrator — Claude Agent SDK로 의도 분류 + tool 호출

**Files:**
- Create: `backend/app/agents/orchestrator.py`
- Test: `backend/tests/test_orchestrator.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_orchestrator.py`:

```python
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.orchestrator import run_turn


@pytest.mark.asyncio
async def test_run_turn_dispatches_create_event(db_session, test_user):
    """When LLM emits a create_event tool call, orchestrator persists the event."""
    fake_llm_response = {
        "tool_calls": [
            {
                "name": "schedule.create_event",
                "arguments": {
                    "title": "내일 3시 회의",
                    "start_at": "2026-05-16T15:00:00+09:00",
                },
            }
        ],
        "final_text": "내일 3시에 회의 잡았어요.",
    }

    with patch("app.agents.orchestrator._call_llm", new=AsyncMock(return_value=fake_llm_response)):
        result = await run_turn(
            db_session,
            user=test_user,
            session_id=None,  # one-off
            user_message="내일 3시에 회의 잡아줘",
        )

    assert "회의 잡았어요" in result["assistant_message"]
    assert len(result["tool_calls"]) == 1
    # event actually persisted
    from sqlalchemy import select
    from app.db.models import Event
    rows = (await db_session.execute(select(Event))).scalars().all()
    assert len(rows) == 1
    assert rows[0].title == "내일 3시 회의"
```

- [ ] **Step 2: 실패 확인**

```bash
cd backend && pytest tests/test_orchestrator.py -v
```
Expected: ImportError

- [ ] **Step 3: orchestrator 작성 (Claude Agent SDK 사용)**

`backend/app/agents/orchestrator.py`:

```python
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schedule_agent import handle_intent as schedule_handle
from app.db.models import User


SCHEDULE_TOOLS = [
    {
        "name": "schedule.create_event",
        "description": "Create a calendar event in the user's local calendar (not Google).",
        "input_schema": {
            "type": "object",
            "required": ["title", "start_at"],
            "properties": {
                "title": {"type": "string"},
                "start_at": {"type": "string", "description": "ISO-8601 datetime with tz"},
                "end_at": {"type": "string"},
                "description": {"type": "string"},
            },
        },
    },
    {
        "name": "schedule.list_events",
        "description": "List events between two datetimes (includes Google-synced and local).",
        "input_schema": {
            "type": "object",
            "required": ["from", "to"],
            "properties": {
                "from": {"type": "string"},
                "to": {"type": "string"},
            },
        },
    },
]


SYSTEM_PROMPT = """\
You are home_agent, a personal assistant orchestrator. The user speaks Korean.
Today's date is provided by the tool runtime. When the user asks about scheduling,
creating, or listing events, call the appropriate schedule.* tool. When relative
times are given ("내일 3시"), resolve them against today's date in the user's
timezone (KST, Asia/Seoul). Respond briefly in Korean after the tool call.
"""


async def _call_llm(messages: list[dict], tools: list[dict]) -> dict[str, Any]:
    """Real implementation uses claude_agent_sdk. Mocked in tests."""
    from claude_agent_sdk import ClaudeClient  # lazy import to keep tests fast
    client = ClaudeClient()
    return await client.run(messages=messages, tools=tools, system=SYSTEM_PROMPT)


async def run_turn(
    session: AsyncSession,
    *,
    user: User,
    session_id: UUID | None,
    user_message: str,
) -> dict[str, Any]:
    """Single conversational turn: LLM decides which tools to call, we dispatch."""
    messages = [{"role": "user", "content": user_message}]
    llm_resp = await _call_llm(messages, SCHEDULE_TOOLS)

    tool_results = []
    for call in llm_resp.get("tool_calls", []):
        name = call["name"]
        args = call["arguments"]
        if name == "schedule.create_event":
            res = await schedule_handle(session, user=user, intent="create_event", params=args)
        elif name == "schedule.list_events":
            res = await schedule_handle(session, user=user, intent="list_events", params=args)
        else:
            res = {"ok": False, "error": f"unknown tool {name}"}
        tool_results.append({"name": name, "result": res})

    return {
        "assistant_message": llm_resp.get("final_text", ""),
        "tool_calls": tool_results,
    }
```

> Note for engineer: this stub uses a simplified `_call_llm`. The real Claude Agent SDK API (`claude_agent_sdk.ClaudeClient`) may differ — check `https://docs.anthropic.com/en/api/agent-sdk` before writing. If the SDK requires a different shape, adapt `_call_llm` so it returns `{tool_calls: [...], final_text: "..."}` and keep the rest of orchestrator unchanged.

- [ ] **Step 4: 테스트 재실행**

```bash
cd backend && pytest tests/test_orchestrator.py -v
```
Expected: PASS (LLM mocked)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/agents/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat(orchestrator): Claude Agent SDK turn loop with schedule tools"
```

---

## Task 9: POST /chat 엔드포인트

**Files:**
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/main.py:36-37` (라우터 등록)
- Test: `backend/tests/test_chat_api.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_chat_api.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_post_chat_creates_event(app_client: AsyncClient, test_user):
    fake_response = {
        "tool_calls": [
            {"name": "schedule.create_event", "arguments": {
                "title": "회의", "start_at": "2026-05-19T15:00:00+09:00",
            }}
        ],
        "final_text": "회의 잡았어요.",
    }
    with patch("app.agents.orchestrator._call_llm", new=AsyncMock(return_value=fake_response)):
        resp = await app_client.post(
            "/chat",
            json={"message": "5월 19일 3시 회의 잡아줘", "user_id": str(test_user.id)},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "회의 잡았어요" in data["assistant_message"]
    assert len(data["tool_calls"]) == 1
```

- [ ] **Step 2: app_client fixture 추가 (conftest)**

`backend/tests/conftest.py`에 추가:

```python
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest_asyncio.fixture
async def app_client(db_engine, monkeypatch):
    # Override the app's session factory to use our test engine
    from app.db import session as session_module
    test_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", test_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
```

- [ ] **Step 3: 실패 확인**

```bash
cd backend && pytest tests/test_chat_api.py -v
```
Expected: 404 (no /chat route)

- [ ] **Step 4: /chat 라우터 작성**

`backend/app/api/chat.py`:

```python
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
```

- [ ] **Step 5: db/session.py에 get_session dep 추가**

`backend/app/db/session.py`가 비어있거나 부족하면 다음을 보장:

```python
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


_settings = get_settings()
_engine = create_async_engine(_settings.database_url, future=True)
AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 6: main.py에 chat router include**

`backend/app/main.py:36-37`:

```python
    app.include_router(health_router)
    from app.api.chat import router as chat_router
    app.include_router(chat_router)
    return app
```

- [ ] **Step 7: 테스트 재실행**

```bash
cd backend && pytest tests/test_chat_api.py -v
```
Expected: PASS

- [ ] **Step 8: 커밋**

```bash
git add backend/app/api/chat.py backend/app/main.py backend/app/db/session.py backend/tests/conftest.py backend/tests/test_chat_api.py
git commit -m "feat(api): POST /chat — orchestrator turn loop end-to-end"
```

---

## Task 10: GET /events 엔드포인트

**Files:**
- Create: `backend/app/api/events.py`
- Modify: `backend/app/main.py` (router include)
- Test: `backend/tests/test_events_api.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_events_api.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.services.schedule_service import create_local_event


@pytest.mark.asyncio
async def test_get_events_returns_in_range(app_client: AsyncClient, db_session, test_user):
    now = datetime.now(timezone.utc)
    await create_local_event(db_session, user_id=test_user.id, title="A", start_at=now)
    await create_local_event(
        db_session, user_id=test_user.id, title="B", start_at=now + timedelta(days=60)
    )

    resp = await app_client.get(
        "/events",
        params={
            "user_id": str(test_user.id),
            "from": (now - timedelta(hours=1)).isoformat(),
            "to": (now + timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == 200
    titles = [e["title"] for e in resp.json()["events"]]
    assert "A" in titles
    assert "B" not in titles
```

- [ ] **Step 2: 실패 확인 → 라우터 작성**

`backend/app/api/events.py`:

```python
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.schedule_service import list_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def get_events(
    user_id: UUID = Query(...),
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    events = await list_events(session, user_id=user_id, from_=from_, to=to)
    return {
        "events": [
            {
                "id": str(e.id),
                "title": e.title,
                "source": e.source,
                "start_at": e.start_at.isoformat(),
                "end_at": e.end_at.isoformat() if e.end_at else None,
                "description": e.description,
            }
            for e in events
        ]
    }
```

- [ ] **Step 3: main.py에 등록**

`backend/app/main.py`에 추가:

```python
    from app.api.events import router as events_router
    app.include_router(events_router)
```

- [ ] **Step 4: 테스트 통과 확인 + 커밋**

```bash
cd backend && pytest tests/test_events_api.py -v
git add backend/app/api/events.py backend/app/main.py backend/tests/test_events_api.py
git commit -m "feat(api): GET /events — list events in time range"
```

---

## Task 11: Google OAuth start + callback

**Files:**
- Create: `backend/app/api/oauth.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_oauth.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_oauth.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_oauth_start_redirects_to_google(app_client: AsyncClient, monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "fake_id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "fake_secret")
    # rebuild settings cache
    from app.core import config
    config.get_settings.cache_clear()

    resp = await app_client.get("/oauth/google/start", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "accounts.google.com" in resp.headers["location"]
    assert "fake_id" in resp.headers["location"]
```

- [ ] **Step 2: oauth.py 작성**

`backend/app/api/oauth.py`:

```python
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/oauth/google", tags=["oauth"])

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/calendar.readonly"


@router.get("/start")
async def oauth_start(user_id: UUID | None = None):
    s = get_settings()
    if not s.google_oauth_client_id:
        raise HTTPException(500, "GOOGLE_OAUTH_CLIENT_ID not set")

    params = {
        "client_id": s.google_oauth_client_id,
        "redirect_uri": s.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": str(user_id) if user_id else "",
    }
    return RedirectResponse(f"{GOOGLE_AUTH}?{urlencode(params)}", status_code=302)


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(""),
    session: AsyncSession = Depends(get_session),
) -> dict:
    import httpx
    s = get_settings()
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            GOOGLE_TOKEN,
            data={
                "code": code,
                "client_id": s.google_oauth_client_id,
                "client_secret": s.google_oauth_client_secret,
                "redirect_uri": s.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    resp.raise_for_status()
    token = resp.json()

    if state:
        user = await session.get(User, UUID(state))
        if user:
            user.external_tokens = (user.external_tokens or {}) | {
                "google": {
                    "refresh_token": token.get("refresh_token"),
                    "scope": token.get("scope"),
                }
            }
            await session.commit()

    return {"ok": True, "scope": token.get("scope")}
```

- [ ] **Step 3: main.py에 등록**

추가:
```python
    from app.api.oauth import router as oauth_router
    app.include_router(oauth_router)
```

- [ ] **Step 4: 테스트 + 커밋**

```bash
cd backend && pytest tests/test_oauth.py -v
git add backend/app/api/oauth.py backend/app/main.py backend/tests/test_oauth.py
git commit -m "feat(oauth): Google OAuth start/callback storing refresh token"
```

---

## Task 12: APScheduler — 15분마다 sync

**Files:**
- Create: `backend/app/scheduler.py`
- Modify: `backend/app/main.py` (lifespan)
- Test: `backend/tests/test_scheduler.py`

- [ ] **Step 1: 테스트 작성**

`backend/tests/test_scheduler.py`:

```python
import pytest

from app.scheduler import build_scheduler, schedule_sync_job


def test_scheduler_registers_sync_job():
    scheduler = build_scheduler()
    schedule_sync_job(scheduler, interval_minutes=15)
    jobs = scheduler.get_jobs()
    assert any(j.name == "google_calendar_sync" for j in jobs)
```

- [ ] **Step 2: scheduler.py 작성**

`backend/app/scheduler.py`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.logging import get_logger

log = get_logger("scheduler")


def build_scheduler() -> AsyncIOScheduler:
    return AsyncIOScheduler(timezone="Asia/Seoul")


def schedule_sync_job(scheduler: AsyncIOScheduler, *, interval_minutes: int = 15) -> None:
    scheduler.add_job(
        _sync_all_users,
        "interval",
        minutes=interval_minutes,
        name="google_calendar_sync",
        id="google_calendar_sync",
        replace_existing=True,
    )


async def _sync_all_users() -> None:
    """For every user with a Google refresh token, sync their calendar."""
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.db.models import User
    from app.db.session import AsyncSessionLocal
    from app.services.calendar_sync import sync_user_google_calendar
    from app.services.google_calendar import GoogleCalendarClient, exchange_refresh_token

    s = get_settings()
    async with AsyncSessionLocal() as session:
        users = (await session.execute(select(User))).scalars().all()
        for user in users:
            tokens = (user.external_tokens or {}).get("google") or {}
            refresh_token = tokens.get("refresh_token")
            if not refresh_token:
                continue
            try:
                access_token = await exchange_refresh_token(
                    refresh_token=refresh_token,
                    client_id=s.google_oauth_client_id,
                    client_secret=s.google_oauth_client_secret,
                )
                client = GoogleCalendarClient(access_token=access_token)
                count = await sync_user_google_calendar(
                    session, user=user, client=client, calendar_id=s.google_calendar_id
                )
                log.info("google.sync", user_id=str(user.id), count=count)
            except Exception as exc:  # noqa: BLE001
                log.error("google.sync.failed", user_id=str(user.id), error=str(exc))
```

- [ ] **Step 3: main.py lifespan에 통합**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(debug=settings.debug)
    log = get_logger("startup")
    log.info("home_agent.start", env=settings.environment)

    from app.scheduler import build_scheduler, schedule_sync_job
    scheduler = build_scheduler()
    schedule_sync_job(scheduler)
    scheduler.start()
    app.state.scheduler = scheduler

    yield
    scheduler.shutdown(wait=False)
    log.info("home_agent.stop")
```

- [ ] **Step 4: 테스트 + 커밋**

```bash
cd backend && pytest tests/test_scheduler.py -v
git add backend/app/scheduler.py backend/app/main.py backend/tests/test_scheduler.py
git commit -m "feat(sync): APScheduler 15-min Google Calendar sync job"
```

---

## Task 13: Frontend — Router + Sidebar + 페이지 placeholders

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/pages/Chat.tsx`
- Create: `frontend/src/pages/Calendar.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/queryClient.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/setupTests.ts`

- [ ] **Step 1: QueryClient + API helper**

`frontend/src/lib/queryClient.ts`:

```typescript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});
```

`frontend/src/lib/api.ts`:

```typescript
const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export async function postChat(message: string, userId: string) {
  const r = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, user_id: userId }),
  });
  if (!r.ok) throw new Error(`chat failed: ${r.status}`);
  return r.json() as Promise<{ assistant_message: string; tool_calls: unknown[] }>;
}

export async function getEvents(userId: string, from: string, to: string) {
  const r = await fetch(
    `${BASE}/events?user_id=${userId}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`,
  );
  if (!r.ok) throw new Error(`events failed: ${r.status}`);
  return r.json() as Promise<{ events: { id: string; title: string; source: string; start_at: string }[] }>;
}
```

- [ ] **Step 2: Sidebar.tsx**

`frontend/src/components/Sidebar.tsx`:

```tsx
import { NavLink } from 'react-router-dom';

export function Sidebar() {
  return (
    <aside className="w-60 h-screen border-r border-stone-200 bg-white p-4 flex flex-col gap-1">
      <div className="font-mono text-sm font-semibold mb-4">home·agent</div>
      <NavLink to="/chat" className={({ isActive }) => `px-3 py-2 rounded-md text-sm ${isActive ? 'bg-indigo-50 text-indigo-600' : 'hover:bg-stone-100'}`}>◐ 챗</NavLink>
      <NavLink to="/calendar" className={({ isActive }) => `px-3 py-2 rounded-md text-sm ${isActive ? 'bg-indigo-50 text-indigo-600' : 'hover:bg-stone-100'}`}>▣ 캘린더</NavLink>
    </aside>
  );
}
```

- [ ] **Step 3: 페이지 placeholders**

`frontend/src/pages/Chat.tsx`:

```tsx
export default function Chat() {
  return <div className="p-6">Chat (TBD)</div>;
}
```

`frontend/src/pages/Calendar.tsx`:

```tsx
export default function Calendar() {
  return <div className="p-6">Calendar (TBD)</div>;
}
```

> 이 두 placeholder는 Task 14, 15에서 실제 구현으로 교체된다. Task 13은 routing이 동작함만 검증.

- [ ] **Step 4: App.tsx + main.tsx**

`frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import Chat from './pages/Chat';
import Calendar from './pages/Calendar';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex">
        <Sidebar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/calendar" element={<Calendar />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
```

`frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 5: vitest 설정**

`frontend/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/setupTests.ts'],
  },
});
```

`frontend/src/setupTests.ts`:

```typescript
import '@testing-library/jest-dom';
```

- [ ] **Step 6: routing 테스트**

`frontend/src/__tests__/Routing.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import Chat from '../pages/Chat';
import Calendar from '../pages/Calendar';

function harness(initialPath: string) {
  return (
    <MemoryRouter initialEntries={[initialPath]}>
      <Sidebar />
      <Routes>
        <Route path="/chat" element={<Chat />} />
        <Route path="/calendar" element={<Calendar />} />
      </Routes>
    </MemoryRouter>
  );
}

test('chat route renders Chat placeholder', () => {
  render(harness('/chat'));
  expect(screen.getByText(/Chat/)).toBeInTheDocument();
});

test('calendar route renders Calendar placeholder', () => {
  render(harness('/calendar'));
  expect(screen.getByText(/Calendar/)).toBeInTheDocument();
});
```

- [ ] **Step 7: 실행**

```bash
cd frontend && npm run test
```
Expected: 2 PASS

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/ frontend/vitest.config.ts
git commit -m "feat(frontend): React Router + Sidebar + page scaffolds + vitest"
```

---

## Task 14: Chat 페이지 — 입력/전송/응답 표시

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`
- Test: `frontend/src/__tests__/Chat.test.tsx`

- [ ] **Step 1: 테스트 작성**

`frontend/src/__tests__/Chat.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Chat from '../pages/Chat';

const fetchMock = vi.fn();
globalThis.fetch = fetchMock as unknown as typeof fetch;

function renderChat() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Chat />
    </QueryClientProvider>,
  );
}

beforeEach(() => fetchMock.mockReset());

test('sends message and renders assistant reply', async () => {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ assistant_message: '회의 잡았어요', tool_calls: [] }),
  });

  renderChat();
  const input = screen.getByPlaceholderText(/메시지/);
  await userEvent.type(input, '내일 3시 회의 잡아줘');
  await userEvent.click(screen.getByRole('button', { name: /전송/ }));

  await waitFor(() => expect(screen.getByText('회의 잡았어요')).toBeInTheDocument());
});
```

- [ ] **Step 2: Chat.tsx 구현**

`frontend/src/pages/Chat.tsx`:

```tsx
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { postChat } from '../lib/api';

interface Turn { who: 'user' | 'assistant'; text: string }

const TEMP_USER_ID = import.meta.env.VITE_USER_ID ?? '00000000-0000-0000-0000-000000000001';

export default function Chat() {
  const [thread, setThread] = useState<Turn[]>([]);
  const [draft, setDraft] = useState('');
  const send = useMutation({
    mutationFn: (msg: string) => postChat(msg, TEMP_USER_ID),
    onSuccess: (data) => setThread((t) => [...t, { who: 'assistant', text: data.assistant_message }]),
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim()) return;
    setThread((t) => [...t, { who: 'user', text: draft }]);
    send.mutate(draft);
    setDraft('');
  };

  return (
    <div className="h-screen flex flex-col">
      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {thread.map((t, i) => (
          <div key={i} className={t.who === 'user' ? 'text-indigo-600' : 'text-stone-800'}>
            <span className="font-mono text-xs text-stone-400 mr-2">{t.who}</span>
            {t.text}
          </div>
        ))}
        {send.isPending && <div className="text-stone-400">생각 중…</div>}
      </div>
      <form onSubmit={onSubmit} className="border-t border-stone-200 p-3 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="메시지를 입력하세요…"
          className="flex-1 border rounded px-3 py-2"
        />
        <button type="submit" className="bg-indigo-600 text-white px-4 rounded">전송</button>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd frontend && npm run test
git add frontend/src/pages/Chat.tsx frontend/src/__tests__/Chat.test.tsx
git commit -m "feat(frontend): Chat page — send message, render reply"
```

---

## Task 15: Calendar 페이지 — 월간 뷰

**Files:**
- Modify: `frontend/src/pages/Calendar.tsx`
- Test: `frontend/src/__tests__/Calendar.test.tsx`

- [ ] **Step 1: 테스트 작성**

`frontend/src/__tests__/Calendar.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Calendar from '../pages/Calendar';

const fetchMock = vi.fn();
globalThis.fetch = fetchMock as unknown as typeof fetch;

function renderCalendar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Calendar />
    </QueryClientProvider>,
  );
}

beforeEach(() => fetchMock.mockReset());

test('renders events from API', async () => {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      events: [
        { id: 'e1', title: 'Standup', source: 'google', start_at: '2026-05-15T10:00:00+09:00' },
        { id: 'e2', title: '회의', source: 'local', start_at: '2026-05-15T15:00:00+09:00' },
      ],
    }),
  });

  renderCalendar();
  await waitFor(() => expect(screen.getByText('Standup')).toBeInTheDocument());
  expect(screen.getByText('회의')).toBeInTheDocument();
});
```

- [ ] **Step 2: Calendar.tsx 구현 (월간 그리드 단순화)**

`frontend/src/pages/Calendar.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { getEvents } from '../lib/api';

const TEMP_USER_ID = import.meta.env.VITE_USER_ID ?? '00000000-0000-0000-0000-000000000001';

function monthRange(now = new Date()) {
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return { from: start.toISOString(), to: end.toISOString() };
}

export default function Calendar() {
  const { from, to } = monthRange();
  const { data, isLoading } = useQuery({
    queryKey: ['events', from, to],
    queryFn: () => getEvents(TEMP_USER_ID, from, to),
  });

  const byDay = new Map<string, typeof data['events']>();
  for (const e of data?.events ?? []) {
    const day = e.start_at.slice(0, 10);
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day)!.push(e);
  }

  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const cells: (Date | null)[] = [];
  for (let i = 0; i < firstDay.getDay(); i++) cells.push(null);
  for (let d = 1; d <= lastDay.getDate(); d++) cells.push(new Date(now.getFullYear(), now.getMonth(), d));

  return (
    <div className="p-6">
      <h1 className="text-xl mb-4">{now.getFullYear()}년 {now.getMonth() + 1}월</h1>
      {isLoading && <div>로딩…</div>}
      <div className="grid grid-cols-7 border border-stone-200">
        {['일', '월', '화', '수', '목', '금', '토'].map((d) => (
          <div key={d} className="bg-stone-50 px-2 py-1 text-xs uppercase">{d}</div>
        ))}
        {cells.map((cell, i) => {
          const key = cell ? cell.toISOString().slice(0, 10) : `empty-${i}`;
          const events = (cell && byDay.get(key)) || [];
          return (
            <div key={key} className="border-t border-stone-200 min-h-[90px] p-1 text-xs">
              {cell && <div className="text-stone-400">{cell.getDate()}</div>}
              {events.map((e) => (
                <div
                  key={e.id}
                  className={`mt-1 px-1 truncate border-l-2 ${e.source === 'google' ? 'border-emerald-500' : 'border-indigo-500'}`}
                >
                  {e.title}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd frontend && npm run test
git add frontend/src/pages/Calendar.tsx frontend/src/__tests__/Calendar.test.tsx
git commit -m "feat(frontend): Calendar page — monthly grid showing local + Google events"
```

---

## Task 16: docker-compose에 frontend 서비스 + Dockerfile

**Files:**
- Create: `frontend/Dockerfile`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Dockerfile**

`frontend/Dockerfile`:

```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

- [ ] **Step 2: docker-compose.yml에 frontend 추가**

`docker-compose.yml` 끝에 추가 (services 안):

```yaml
  frontend:
    build:
      context: ./frontend
    container_name: home_agent_frontend
    depends_on:
      - backend
    environment:
      VITE_API_BASE: http://localhost:8000
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
```

- [ ] **Step 3: 통합 기동 검증**

```bash
docker compose up --build -d
curl -s http://localhost:8000/health
curl -s http://localhost:5173 | head -20
```
Expected: 양쪽 모두 200, frontend html이 `<!doctype html>`로 시작.

- [ ] **Step 4: 커밋**

```bash
git add frontend/Dockerfile docker-compose.yml
git commit -m "feat(docker): compose frontend service alongside backend"
```

---

## Task 17: 수동 E2E 스모크 + Week 1 종료 검증

**Files:**
- None (수동 검증)

- [ ] **Step 1: 환경 세팅**
  - `.env`에 `ANTHROPIC_API_KEY` 입력
  - Google Cloud Console에서 OAuth client 만들고 `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` 입력
  - `docker compose up`

- [ ] **Step 2: 테스트 유저 생성**

```bash
docker exec home_agent_postgres psql -U home_agent -d home_agent -c \
"INSERT INTO core.users (id, name) VALUES ('00000000-0000-0000-0000-000000000001', 'me');"
```

- [ ] **Step 3: Google OAuth 연동**
  - 브라우저로 `http://localhost:8000/oauth/google/start?user_id=00000000-0000-0000-0000-000000000001`
  - Google 동의 완료
  - `psql ... 'SELECT external_tokens FROM core.users;'` 로 refresh_token 저장됐는지 확인

- [ ] **Step 4: Google sync 수동 트리거**

```bash
docker exec home_agent_backend python -c "
import asyncio
from app.scheduler import _sync_all_users
asyncio.run(_sync_all_users())
"
```
Expected: 로그에 `google.sync user_id=... count=N`

- [ ] **Step 5: 챗 + 캘린더 검증**
  - 브라우저로 `http://localhost:5173/chat`
  - "내일 3시 회의 잡아줘" 입력 → 응답 "잡았어요" 비슷한 메시지
  - `http://localhost:5173/calendar` 이동 → Google 일정(녹색)과 방금 추가한 로컬 일정(보라)이 같이 표시

- [ ] **Step 6: Week 1 완료 마커 — progress.txt 갱신**

`.omc/progress.txt` 아래에 한 줄 추가:

```
## Week 1 완료 — 2026-MM-DD
일정 도메인 thin slice 가동. 챗에서 "내일 3시 회의 잡아줘" → DB 저장 → 캘린더 화면 표시 확인.
Google Calendar 읽기 동기화도 동작. 다음 주차: TODO + Todoist 양방향.
```

- [ ] **Step 7: 최종 커밋**

```bash
git add .omc/progress.txt
git commit -m "chore(progress): Week 1 complete — schedule domain dogfooding ready"
```

---

## Self-Review

이 plan을 검토한 결과:

- **Spec coverage**:
  - Week 1 종료 기준 "챗에서 '내일 3시 회의 잡아줘' → 일정 생성, 캘린더에서 확인" — Task 8, 9, 14, 17이 커버.
  - "Google Cal의 기존 일정도 보임" — Task 5, 6, 11, 12가 커버.
  - 스펙 §5의 `schedule.events` DDL — Task 1, 2가 커버.
  - 스펙 §6의 Google read-only 정책 (15분 cron) — Task 11, 12가 커버.
- **Placeholders**:
  - 페이지 placeholder "Chat (TBD)" / "Calendar (TBD)"는 Task 13에서 의도적으로 사용 후 Task 14, 15에서 즉시 교체된다. 명시했음. 진짜 미완 placeholder는 없음.
  - orchestrator의 Claude Agent SDK API shape이 "check SDK before writing"으로 명시됨 — 이 부분은 SDK 실제 API에 따라 약간 조정될 수 있는 known unknown. 의도적으로 남김(SDK 문서 확인이 필요한 외부 의존성).
- **Type consistency**:
  - `Event.source` 값: `'local'` / `'google'` 일관됨 (Task 1 모델 정의, Task 4 service, Task 6 sync, Task 10 API에서 동일).
  - `external_tokens` 형태: `{"google": {"refresh_token": "..."}}` 일관됨 (Task 1 모델, Task 11 OAuth callback, Task 12 scheduler).
  - 함수명: `create_local_event`, `list_events`, `upsert_google_event`, `sync_user_google_calendar`, `handle_intent`, `run_turn`, `_sync_all_users` — 각 task에서 동일하게 호출/정의됨.

---

## Notes for the implementing agent

- **Claude Agent SDK 실제 API**: Task 8의 `_call_llm` stub은 가설적 시그니처. 실제 SDK 호출 형태가 다를 수 있으므로 SDK 문서를 먼저 확인하고 stub을 어댑트할 것. orchestrator의 다른 부분은 SDK 시그니처와 무관하게 동작하도록 격리됨.
- **testcontainers**: Task 3 conftest가 Docker가 실행 중이어야 동작. CI/로컬 모두 동일.
- **Google OAuth 환경**: Task 11, 17은 실제 Google Cloud Console에서 OAuth client 발급이 필요. 발급 안 되어 있으면 Task 11의 단위 테스트(mocked)는 통과하지만 Task 17 수동 검증을 못 한다. 그 경우 Week 1 종료 기준 일부 (Google 동기화) 미달.
- **시간대**: APScheduler는 Asia/Seoul, ISO timestamp는 모두 timezone-aware. naive datetime 사용 금지.
- **커밋 빈도**: 매 Task 종료 시 atomic commit. 17개 task ≈ 17개 커밋. Task 사이에 리뷰가 가능하다.
