# Phase 1: chat.py 슬림 + ChatService 단일 추출

**Status:** pending approval (RALPLAN-DR v2, Critic APPROVED at iteration 1/5)
**Date:** 2026-05-17
**Owner:** damien
**Parent roadmap:** `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` (§Phase 1 — wording correction required post-merge; 본 spec §10 참조)
**Scope:** `backend/app/api/chat.py` 슬림화 + `backend/app/services/chat_service.py` 단일 추출 + `backend/app/api/_chat_input.py` HTTP-input 분리 + contract test 사전 commit

**Iteration history:**
- v1: 3 services (`ChatService` + `SessionService` + `MessagePersistenceService`) — 메타-로드맵 mandate 그대로
- Architect v1: 3 HIGH + 3 MEDIUM + 2 LOW issues. 핵심 steelman: 3-service split은 CLAUDE.md §2 위반 (single-consumer abstraction). TodoService canonical pattern은 flat 단일 class.
- v2: Architect synthesis 채택 — **단일 ChatService** + 메타-로드맵 §Phase 1 wording 후처리
- Critic v2: **APPROVE** + 2 MINOR observations (shell-quoting note, naming flip ADR 1줄)

---

## 1. RALPLAN-DR Summary

### Principles

1. **TodoService 패턴 정확 일치** — 단일 class, `__init__(session, user)`, methods `flush()` (no commit), router `commit()`. v1의 3-service 분리는 single-consumer abstraction (CLAUDE.md §2 위반) → 폐기.
2. **Contract-invariant** — `ChatResponse` 응답 키/타입 무변동. drift는 신규 contract test가 즉시 감지.
3. **HTTP-input은 라우터 영역, business는 service** — `parse_input` + `ParsedInput` + `_header_uuid`는 `app/api/_chat_input.py` 모듈로 분리 (라우터 영역 유지). HTTPException은 service 절대 raise 금지 — service는 도메인 에러(`UnknownDomainError`), 라우터에서 404 변환.
4. **FilesAgent 모듈-레벨 singleton 유지** — `files_agent.py`는 stateless (verified at `files_agent.py:65-157`). `chat_service.py`에 module-level `_files = FilesAgent()` 유지.
5. **단일 atomic PR** — contract test 사전 별도 commit + 본 작업 1 PR.

### Decision Drivers

1. **chat.py 266줄 인지 표면 축소** (목표 ≤80 LOC, 실측 예상 ~50)
2. **CLAUDE.md §2 준수** (speculative abstraction 회피 — single consumer)
3. **TodoService 패턴 정확 일치** (`backend/app/services/todo.py:14-17` 동형)

### Viable Options

| Option | 설명 | Pros | Cons |
|---|---|---|---|
| **X. 단일 ChatService** (Architect synthesis, **Recommended**) | 1 class flat, 메타-로드맵 wording 보정 | TodoService 패턴 정확 일치, CLAUDE.md 준수, ~250 LOC churn | 메타-로드맵 §Phase 1 mandate 편차 — 후처리 wording correction |
| **Y. 3 services 유지** (메타-로드맵 mandate strict) | `ChatService` + `SessionService` + `MessagePersistenceService` | 메타-로드맵 strict 준수 | CLAUDE.md §2 위반, ~440 LOC churn, TodoService와 불일치 |
| **Z. 2 services 절충** | persistence만 분리, session 합침 | 메타-로드맵 일부 반영 | 임의적 분리선, 여전히 single-consumer — Y와 동일 위반 |

→ **Option X 채택**. CLAUDE.md §2 (project-level rule)이 메타-로드맵 (project-level decision)보다 우선. 메타-로드맵 wording correction은 후처리 가능 (§10 참조).

---

## 2. 신규 파일: `backend/app/api/_chat_input.py`

HTTP-input parsing 책임을 담당. 라우터 모듈 영역 (underscore-prefixed filename = module-level privacy).

```python
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, Request


@dataclass(slots=True)
class ParsedInput:
    message: str
    user_id: UUID
    session_id: UUID | None
    device_id: UUID | None
    device_name: str | None
    raw_files: list[tuple[bytes, str, str]]


def _header_uuid(request: Request, name: str) -> UUID | None:
    raw = request.headers.get(name)
    return UUID(raw) if raw else None


async def parse_input(request: Request) -> ParsedInput:
    """Parse multipart/form-data or JSON body into a ParsedInput.
    Raises HTTPException(422) when user_id is missing in multipart payload.
    """
    ct = request.headers.get("content-type", "")
    device_id = _header_uuid(request, "X-Device-Id")
    device_name = request.headers.get("X-Device-Name")

    if ct.startswith("multipart/"):
        form = await request.form()
        message = str(form.get("message", ""))
        user_id_raw = form.get("user_id")
        session_id_raw = form.get("session_id")
        files_field = form.getlist("attachments") if "attachments" in form else []
        raw_files: list[tuple[bytes, str, str]] = []
        for f in files_field:
            data = await f.read()
            raw_files.append((data, f.filename or "upload.bin", f.content_type or "application/octet-stream"))
        if user_id_raw is None:
            raise HTTPException(422, "user_id is required")
        return ParsedInput(
            message=message,
            user_id=UUID(str(user_id_raw)),
            session_id=UUID(str(session_id_raw)) if session_id_raw else None,
            device_id=device_id,
            device_name=device_name,
            raw_files=raw_files,
        )

    body = await request.json()
    return ParsedInput(
        message=body["message"],
        user_id=UUID(body["user_id"]),
        session_id=UUID(body["session_id"]) if body.get("session_id") else None,
        device_id=device_id,
        device_name=device_name,
        raw_files=[],
    )
```

**Naming**: 본문 함수/클래스에서 underscore 제거 (`_parse_input` → `parse_input`, `_ParsedInput` → `ParsedInput`). 모듈 자체가 `_chat_input.py` (underscore-prefixed)로 internal helper 신호. `_header_uuid`만 private 유지 (모듈 외부에서 호출되지 않음).

---

## 3. 신규 파일: `backend/app/services/chat_service.py`

flat 단일 class. TodoService (`backend/app/services/todo.py:14-17`)와 동형.

```python
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.files_agent import FilesAgent
from app.agents.orchestrator import run_turn as orchestrator_run_turn
from app.agents.registry import REGISTRY
from app.db.models import Attachment, Message, Session, User


_files = FilesAgent()  # module-level singleton — FilesAgent is stateless (verified files_agent.py:65-157)


class UnknownDomainError(LookupError):
    """Raised when chat/{domain} hits an unregistered domain. Router translates → HTTP 404."""


class ChatService:
    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user

    # ---- Session lifecycle ------------------------------------------------

    async def get_or_create_scoped_session(
        self,
        *,
        scope: str,
        device_id: UUID | None,
        device_name: str | None,
    ) -> Session:
        # 현재 chat.py:85-117 본문 그대로 이식
        stmt = (
            select(Session)
            .where(
                Session.user_id == self.user.id,
                Session.device_id == device_id,
                Session.scope == scope,
                Session.ended_at.is_(None),
            )
            .order_by(Session.created_at.desc())
            .limit(1)
        )
        sess = (await self.session.scalars(stmt)).first()
        if sess is not None:
            if device_name and sess.device_name != device_name:
                sess.device_name = device_name
            return sess
        sess = Session(
            user_id=self.user.id,
            scope=scope,
            device_id=device_id,
            device_name=device_name,
        )
        self.session.add(sess)
        await self.session.flush()
        return sess

    # ---- Attachments ------------------------------------------------------

    async def save_attachments(
        self,
        *,
        session_id: UUID,
        raw_files: list[tuple[bytes, str, str]],
    ) -> list[Attachment]:
        # 현재 chat.py:137-155 본문 — _files 모듈 singleton 사용
        out: list[Attachment] = []
        for raw, name, mime in raw_files:
            att = await _files.save_attachment(
                self.session,
                user=self.user,
                raw=raw,
                original_name=name,
                mime=mime,
                session_id=session_id,
            )
            out.append(att)
        return out

    # ---- Context loading --------------------------------------------------

    async def load_recent(
        self,
        *,
        session_id: UUID,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        # 현재 chat.py:120-134 본문
        stmt = (
            select(Message)
            .where(
                Message.session_id == session_id,
                Message.role.in_(["user", "assistant"]),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = list((await self.session.scalars(stmt)).all())
        rows.reverse()
        return [{"role": m.role, "content": m.content} for m in rows]

    # ---- Turn persistence -------------------------------------------------

    async def persist_turn(
        self,
        *,
        session: Session,
        user_message: str,
        attachments: list[Attachment],
        result: dict[str, Any],
    ) -> None:
        # 현재 chat.py:158-183 본문
        extra = {"attachment_ids": [str(a.id) for a in attachments]} if attachments else None
        self.session.add(Message(session_id=session.id, role="user", content=user_message, extra=extra))
        self.session.add(
            Message(
                session_id=session.id,
                role="assistant",
                content=result.get("assistant_message", ""),
            )
        )
        for tc in result.get("tool_calls", []):
            self.session.add(
                Message(
                    session_id=session.id,
                    role="tool",
                    content=json.dumps(tc, ensure_ascii=False),
                    extra=tc,
                )
            )

    # ---- Public entry points ---------------------------------------------

    async def run_orchestrator(
        self,
        *,
        message: str,
        device_id: UUID | None,
        device_name: str | None,
        raw_files: list[tuple[bytes, str, str]],
    ) -> dict[str, Any]:
        sess = await self.get_or_create_scoped_session(
            scope="orchestrator", device_id=device_id, device_name=device_name
        )
        attachments = await self.save_attachments(
            session_id=sess.id, raw_files=raw_files
        )
        result = await orchestrator_run_turn(
            self.session,
            user=self.user,
            session_id=sess.id,
            user_message=message,
            device_id=device_id,
            device_name=device_name,
        )
        await self.persist_turn(
            session=sess, user_message=message,
            attachments=attachments, result=result,
        )
        return result

    async def run_domain(
        self,
        domain: str,
        *,
        message: str,
        device_id: UUID | None,
        device_name: str | None,
        raw_files: list[tuple[bytes, str, str]],
    ) -> dict[str, Any]:
        if domain not in REGISTRY:
            raise UnknownDomainError(domain)
        sess = await self.get_or_create_scoped_session(
            scope=domain, device_id=device_id, device_name=device_name
        )
        attachments = await self.save_attachments(
            session_id=sess.id, raw_files=raw_files
        )
        recent = await self.load_recent(session_id=sess.id)
        agent = REGISTRY[domain]
        result = await agent.run_turn(
            self.session,
            user=self.user,
            session_id=sess.id,
            user_message=message,
            recent_messages=recent,
            attachments=attachments,
        )
        await self.persist_turn(
            session=sess, user_message=message,
            attachments=attachments, result=result,
        )
        return result
```

**메모**:
- `flush()` only (commit은 라우터). TodoService 패턴.
- `UnknownDomainError` 정의는 service 모듈 내부 — TodoService의 `NotFoundError` (todo.py:10-11)와 동형.
- 모든 method는 user-scoped (instance attribute `self.user`).
- HTTPException 0건 (service layer cleanliness).

---

## 4. 슬림 라우터: `backend/app/api/chat.py`

목표 ≤80 LOC, 실측 예상 ~50.

```python
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
```

**잔존 헬퍼**: 0건. `_header_uuid`, `parse_input`, `ParsedInput`, `_files`, 6개 helper, `_ParsedInput` 클래스 모두 이동.

---

## 5. Contract Test (사전 별도 commit)

`backend/tests/test_chat_api.py`에 추가. **Phase 1 본 작업 시작 전 별도 commit으로 머지** — baseline 확립.

```python
@pytest.mark.asyncio
async def test_chat_response_contract(app_client, test_user):
    """ChatResponse keys exactly {assistant_message, tool_calls}; drift detection.
    
    Verified baseline at plan-write: schemas/chat.py:18-20 has exactly 2 fields.
    Any future field addition forces test update — intended drift detection.
    """
    fake_llm = {
        "tool_calls": [{"name": "x.y", "arguments": {"k": "v"}}],
        "final_text": "ok",
    }
    with patch(
        "app.agents.orchestrator.call_llm",
        new=AsyncMock(return_value=fake_llm),
    ):
        resp = await app_client.post(
            "/chat", json={"message": "hi", "user_id": str(test_user.id)}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"assistant_message", "tool_calls"}
    assert isinstance(data["assistant_message"], str)
    assert isinstance(data["tool_calls"], list)
    for tc in data["tool_calls"]:
        assert set(tc.keys()) == {"name", "result"}
```

**Mock target**: `app.agents.orchestrator.call_llm` (low-level, 기존 `test_post_chat_creates_event`와 동일 layer). `run_turn` mocking 하면 orchestrator의 transform이 skip되어 contract 검증 안 됨 (Architect 이슈 #1 fix).

---

## 6. ChatService Unit Test (신규 파일)

`backend/tests/test_chat_service.py`. 최소 1건 — `get_or_create_scoped_session`의 device_name 갱신 분기 (chat.py:106-107) 보존 검증.

```python
import pytest
from uuid import uuid4

from app.db.models import Session, User
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_get_or_create_scoped_session_updates_device_name(
    db_session, test_user
):
    """Existing session with stale device_name gets refreshed."""
    device_id = uuid4()
    # Pre-existing session with old name
    sess = Session(
        user_id=test_user.id,
        scope="orchestrator",
        device_id=device_id,
        device_name="old-laptop",
    )
    db_session.add(sess)
    await db_session.commit()

    svc = ChatService(db_session, test_user)
    refreshed = await svc.get_or_create_scoped_session(
        scope="orchestrator", device_id=device_id, device_name="new-laptop"
    )
    assert refreshed.id == sess.id
    assert refreshed.device_name == "new-laptop"
```

**Rationale (Critic Q6)**: device_name 갱신은 `get_or_create_scoped_session` 본문 내 유일한 non-trivial 분기. 추출 후 동작 보존 게이트. 추가 unit test 과대 추가는 integration test (test_chat_api.py)와 중복 → YAGNI.

---

## 7. 실행 순서

**Step 1** — Contract test 사전 commit
- `backend/tests/test_chat_api.py`에 `test_chat_response_contract` 추가
- `pytest backend/tests/test_chat_api.py::test_chat_response_contract` green 확인
- Commit (예: `test(chat): add ChatResponse contract assertion for Phase 1 baseline`)
- main 머지

**Step 2** — Atomic 추출 PR (단일 commit 또는 PR)
- `backend/app/api/_chat_input.py` 신규
- `backend/app/services/chat_service.py` 신규
- `backend/app/api/chat.py` 슬림화 (헬퍼 6개 + `_ParsedInput` + `_files` 모두 제거)
- `backend/tests/test_chat_service.py` 신규 (unit test 1건)
- `pytest backend/tests/test_chat_api.py backend/tests/test_chat_service.py` 전체 green 확인
- Commit (예: `refactor(chat): extract ChatService + slim router (Phase 1)`)
- main 머지

**Step 3** — Meta-roadmap §Phase 1 wording correction (§10 참조)
- 별도 단일 commit (위 2 commit 이후)

---

## 8. Acceptance Criteria

| # | Criterion | Verification (binary pass/fail) |
|---|---|---|
| a | chat.py 헬퍼 0건 | `grep -cE "^(async )?def _" backend/app/api/chat.py` == `0`【shell-agnostic regex; Critic minor note 반영】 |
| b | 기존 `test_chat_api.py` 그린 | `pytest backend/tests/test_chat_api.py` exit 0 |
| c | 신규 contract test 그린 | `pytest backend/tests/test_chat_api.py::test_chat_response_contract` exit 0 — Step 1 commit 이후, Step 2 이후 동일 |
| d | frontend `api.ts` 무변동 | Phase 1 PR 변경 파일에 `frontend/` 0건 |
| e | chat.py LOC ≤ 80 | `wc -l backend/app/api/chat.py` ≤ 80 |
| f | 신규 모듈 import OK | `python -c "from app.services.chat_service import ChatService, UnknownDomainError; from app.api._chat_input import parse_input, ParsedInput"` exit 0 |
| g | service에 HTTPException 0건 | `grep -c "HTTPException" backend/app/services/chat_service.py` == `0` |
| h | ChatService unit test 그린 | `pytest backend/tests/test_chat_service.py` exit 0 |
| i | dev deps 무변동 | `git diff main backend/pyproject.toml` == `''` (외부 의존성 추가 금지 — 메타-로드맵 §Phase 1 (d)) |

---

## 9. Open Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | 메타-로드맵 §Phase 1 wording deviation을 사용자가 거부 | v2 폐기, Option Y (3 services) 채택 + CLAUDE.md §2 위반 acknowledged (의식적). 본 spec approval 시점에 결정. |
| 2 | `_files` module singleton이 test에서 mock 어려움 | 현재 chat.py도 동일 패턴 (`chat.py:18`) — 회귀 없음. mock 필요 시 `monkeypatch.setattr("app.services.chat_service._files", ...)` |
| 3 | `_chat_input.py` 위치가 `app/api/` 안 underscore-prefixed — `schemas/`와 혼동 가능 | 추후 명명 검토 (Phase 1 scope 외). 단 underscore prefix는 internal 신호 — 외부 import 금지 컨벤션 |
| 4 | atomic PR (Step 2)의 churn ~250 LOC — 1인 review 부담 | 본 spec이 implementation 명세를 다 가지므로 PR 본문이 spec 링크만으로 충분. ~250 LOC는 본질적으로 verbatim move + 라우터 슬림 |
| 5 | `UnknownDomainError`가 미래에 다른 service 패턴과 충돌 | TodoService `NotFoundError` 패턴 그대로 — 충돌 가능성 낮음 |

---

## 10. Meta-Roadmap Reconciliation

메타-로드맵 (`docs/superpowers/specs/2026-05-17-execution-roadmap-design.md`) §Phase 1 "다층 분리 (이미 결정): ChatService + SessionService + MessagePersistenceService" 문구가 본 v2와 충돌.

**Architect/Critic 합의 사항**: 메타-로드맵의 3-service mandate는 CLAUDE.md §2 ("No abstractions for single-use code")와 정면 충돌. CLAUDE.md (project-level rule)가 우선. 메타-로드맵 wording은 후처리 commit으로 정정.

### 후처리 commit (Step 3)

본 Phase 1 머지 직후 별도 단일 commit:
- `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` §Phase 1 "다층 분리" 문구 → "단일 ChatService 추출 + `_chat_input.py` HTTP-input 분리" 로 정정
- 메타-로드맵 ADR에 본 deviation 명시 (신규 MA-3 추가): **"Single-service flat pattern for chat domain — matches TodoService canonical pattern; 3-service split would have been speculative abstraction (CLAUDE.md §2)."**
- 메타-로드맵 Open Risk #1 "Phase 1 ralplan이 다층 분리로 큰 PR 생성 → sub-phase 1a/1b/1c로 더 쪼개야 할 수도" → "해당 없음 (단일 service)" 라벨링

Commit message 예: `docs(planning): correct §Phase 1 wording — single ChatService (matches TodoService pattern)`

---

## 11. ADR

### Decision
단일 `ChatService` 추출 (3-service 분리 폐기). `_chat_input.py`로 HTTP-input 분리. Contract test 사전 별도 commit. atomic refactor PR (Step 2).

### Drivers
- TodoService 패턴 정확 일치
- CLAUDE.md §2 준수 (single-consumer abstraction 회피)
- chat.py 인지 표면 축소 (266 → ~50 LOC)

### Alternatives considered
- **Y (3 services, 메타-로드맵 strict)**: CLAUDE.md §2 위반, ~440 LOC churn
- **Z (2 services 절충)**: 임의적 분리선, Y와 동일 violation

### Why chosen
Architect steelman 채택. CLAUDE.md (project rule)이 메타-로드맵 (project decision)보다 우선. 메타-로드맵 wording은 후처리로 정정 가능.

### Consequences
- 메타-로드맵 §Phase 1 wording 후처리 commit 필요 (§10)
- Phase 5 (Todoist) 진입 시 todoist_service.py도 동일 flat 패턴 → 외부 통합 service 패턴 명확
- service unit test는 method 단위로 충분 (단일 class 안에서도 isolation 가능)
- `parse_input` / `ParsedInput` underscore 제거 — `_chat_input.py` 모듈 자체가 underscore prefix로 internal privacy 신호【Critic minor note 반영】

### Follow-ups
- `schedule_service` / `oauth_google` in-service commit 패턴 정리는 별도 spec (Phase 1 scope 외)
- 후처리 메타-로드맵 wording commit (Step 3) — 본 Phase 1 머지 직후
- Phase 2 (React Tailwind 이식) ralplan 진입 — 본 Phase 1 머지 + meta-roadmap wording correction 완료 후

---

## 12. Verification References

본 spec의 사실 주장은 다음 소스에서 확인됨 (Architect/Critic verification log):

- `backend/app/api/chat.py:18` — `_files = FilesAgent()` module-level singleton (이식 대상)
- `backend/app/api/chat.py:21-39` — `_ParsedInput` class (→ `_chat_input.py` 로 `ParsedInput`)
- `backend/app/api/chat.py:42-44` — `_header_uuid` (→ `_chat_input.py` private 유지)
- `backend/app/api/chat.py:47-82` — `_parse_input` (→ `_chat_input.py::parse_input`)
- `backend/app/api/chat.py:85-117` — `_get_or_create_scoped_session` (→ `ChatService.get_or_create_scoped_session`)
- `backend/app/api/chat.py:106-107` — device_name 갱신 분기 (unit test 대상)
- `backend/app/api/chat.py:120-134` — `_load_recent_messages` (→ `ChatService.load_recent`)
- `backend/app/api/chat.py:137-155` — `_save_attachments` (→ `ChatService.save_attachments`)
- `backend/app/api/chat.py:158-183` — `_persist_turn` (→ `ChatService.persist_turn`)
- `backend/app/api/chat.py:229-230` — `domain not in REGISTRY` HTTPException (→ service `UnknownDomainError` + 라우터 translation)
- `backend/app/api/schemas/chat.py:18-20` — `ChatResponse` 정확 2 필드 (contract test 기준선)
- `backend/app/api/schemas/chat.py:13-15` — `ToolCallOut` 정확 2 필드 (contract test inner assertion)
- `backend/app/services/todo.py:10-11` — `NotFoundError` 패턴 (UnknownDomainError 미러)
- `backend/app/services/todo.py:14-17` — TodoService canonical pattern (단일 class, `__init__(session, user_id)`)
- `backend/app/api/todo.py:48,68-69` — router `await session.commit()` + `NotFoundError → HTTPException(404)` translation 패턴
- `backend/app/agents/files_agent.py:65-157` — FilesAgent statelessness (module singleton 안전)
- `backend/app/agents/orchestrator.py:7,93` — `call_llm` import location (contract test mock target)
- `backend/tests/test_chat_api.py:21-22` — 기존 mock target = `call_llm` (contract test 동일 layer)

---

## 13. Status & Next Action

- **Status**: pending approval (Critic APPROVED v2 at iteration 1/5)
- **Next action** (approve 시):
  1. Step 1 commit (contract test) — `test(chat): add ChatResponse contract assertion for Phase 1 baseline`
  2. Step 2 commit/PR (refactor + ChatService + _chat_input + unit test)
  3. Step 3 commit (메타-로드맵 wording correction)
- **Out of spec**: implementation은 본 ralplan에서 호출하지 않음. 사용자 approve 후 별도 execution.
