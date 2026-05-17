# 구현 Plan — 오케스트레이터 ↔ 도메인 서브에이전트

**작성일**: 2026-05-17
**Spec**: [`docs/superpowers/specs/2026-05-16-orchestrator-domain-subagents.md`](../specs/2026-05-16-orchestrator-domain-subagents.md)
**상태**: ready
**예상 작업**: 10 단계, 단계마다 verify 후 다음으로

원칙: 각 단계를 작은 commit 단위로. 단계 사이엔 테스트가 깨지면 안 된다 (단, stub 도메인이 노출되기 전 step 7까지는 schedule만 사용하므로 기존 테스트 그대로 통과해야 함).

---

## Step 1 — 마이그레이션 `0005_session_scope`

**목표**: `core.sessions`에 `scope` 컬럼 추가.

**변경**:
- 신규 `backend/alembic/versions/0005_session_scope.py`
  - revision="0005", down_revision="0004"
  - upgrade: ADD COLUMN scope VARCHAR(32) NOT NULL DEFAULT 'orchestrator'
  - upgrade: CREATE INDEX ix_core_sessions_device_scope ON core.sessions(device_id, scope)
  - downgrade: 인덱스/컬럼 둘 다 drop
- 수정 `backend/app/db/models/core.py` `Session`에 `scope: Mapped[str] = mapped_column(String(32), nullable=False, default="orchestrator")` 추가

**verify**:
- `docker compose exec backend alembic upgrade head` 성공
- `docker compose exec postgres psql -c "\d core.sessions"`에 scope 컬럼 존재
- `alembic downgrade -1 && alembic upgrade head` 왕복 성공

---

## Step 2 — `agents/base.py` (DomainAgent Protocol)

**목표**: 모든 도메인 agent가 따를 인터페이스 확정.

**변경**:
- 신규 `backend/app/agents/base.py`
  - `class DomainAgent(Protocol)`: `name`, `tools`, `model`, `async def handle_tool(...)`, `async def run_turn(...)`
  - 공통 헬퍼 (LLM 호출 wrapper, 메시지 직렬화)

**verify**:
- `python -c "from app.agents.base import DomainAgent"` import 성공
- mypy/pyright: 없으면 skip (프로젝트가 type-check 셋업되어 있는지 확인)

---

## Step 3 — `agents/registry.py`

**목표**: 도메인 agent 인스턴스 1곳에서 조립.

**변경**:
- 신규 `backend/app/agents/registry.py` — `REGISTRY: dict[str, DomainAgent]`. 이 시점엔 schedule만 등록(Step 4 이후 todo, Step 6 이후 stub들 추가).

**verify**:
- `python -c "from app.agents.registry import REGISTRY; print(list(REGISTRY))"` → `['schedule']`

---

## Step 4 — `schedule_agent.py` 리팩터

**목표**: 기존 `handle_intent` 함수를 `ScheduleAgent` 클래스로 감싸고 `run_turn` 추가.

**변경**:
- 수정 `backend/app/agents/schedule_agent.py`
  - `class ScheduleAgent`로 wrap (`name="schedule"`, `tools=[...]`, `model=settings.agent_models["schedule"]`)
  - 기존 `handle_intent` 함수는 `handle_tool` 메서드로 옮김 (시그니처 호환)
  - 신규 `run_turn` — schedule 한정 system prompt + 자기 tools만으로 LLM 호출 → 도구 호출 결과 합쳐 응답
- 수정 `agents/registry.py` — `ScheduleAgent()` 등록
- 수정 `agents/orchestrator.py` — 기존 `schedule_handle` import를 REGISTRY 참조로 임시 교체(Step 7에서 완전 리라이트)

**verify**:
- 기존 `tests/test_schedule_agent.py` 통과
- 신규 단위 테스트: `test_schedule_agent_run_turn.py` — LLM mock으로 tool_call 분기 검증

---

## Step 5 — `todo_agent.py` 신규 (로컬 DB만)

**목표**: todo 도메인 풀구현. Todoist 동기화는 제외.

**선행 확인**:
- `backend/app/db/models/todo.py` 모델 존재 — 컬럼 확인. 없으면 task 모델/마이그레이션 작업이 추가됨.

**변경**:
- 신규 `backend/app/agents/todo_agent.py`
  - tools: `todo.add_task`, `todo.list_tasks`, `todo.complete_task`, `todo.set_priority`
  - `handle_tool`: 각 intent를 `services/todo_service.py`로 위임 (서비스 레이어 없으면 같이 신규)
  - `run_turn`: todo 한정 system prompt
- (필요시) 신규 `backend/app/services/todo_service.py` — CRUD
- 수정 `agents/registry.py` — `TodoAgent()` 등록

**verify**:
- 단위 테스트: `tests/test_todo_agent.py` — add → list → complete → set_priority CRUD 라운드트립 (실제 DB)
- `run_turn` LLM mock 테스트
- 기존 schedule 테스트는 그대로 통과

---

## Step 6 — Stub 도메인 4종

**목표**: ledger/finance/ideas/files도 registry에 올려서 오케스트레이터 LLM이 도구로 인식하도록.

**변경**:
- 신규 4개 파일:
  - `backend/app/agents/ledger_agent.py` — tools 스키마 (`ledger.add_transaction`, `ledger.sum_by_category`, `ledger.list_transactions`), `handle_tool`/`run_turn`은 `{"ok": False, "error": "not implemented yet"}` 반환
  - `finance_agent.py` (`finance.update_valuation`, `finance.net_worth_snapshot`)
  - `ideas_agent.py` (`ideas.create_note`, `ideas.search_semantic`, `ideas.extract_action_items`)
  - `files_agent.py` (`files.upload`, `files.search_files`)
- 수정 `agents/registry.py` — 4개 등록

**verify**:
- `python -c "from app.agents.registry import REGISTRY; print(sorted(REGISTRY))"` → 6개 도메인
- 도구 이름 충돌 없음 검증 (모든 tool name이 unique)

---

## Step 7 — `orchestrator.py` 리라이트

**목표**: REGISTRY 합집합 dispatch + cross-domain context inject.

**변경**:
- 수정 `backend/app/agents/orchestrator.py`
  - `all_tools = [t for a in REGISTRY.values() for t in a.tools]`
  - 시스템 프롬프트 갱신 (모든 도메인 도구 사용법 명시)
  - tool_call 처리: `domain, intent = call.name.split(".", 1)` → `REGISTRY[domain].handle_tool(...)`
  - cross-domain context: 헬퍼 `load_domain_recent_turns(db, user, device_id, n=3)` 추가 → 각 도메인 scope 세션의 최근 user/assistant pair 3쌍을 가져와 system 메시지에 prepend
  - 모델은 `settings.agent_models["orchestrator"]`

**verify**:
- 단위 테스트: orchestrator가 schedule tool_call 정상 dispatch
- 단위 테스트: orchestrator가 ledger tool_call → stub 501 응답을 그대로 받아 응답에 포함
- 통합 테스트: 도메인 챗 turn을 미리 쌓아두고 → 오케스트레이터 chat이 그 컨텍스트를 시스템에 inject하는지

---

## Step 8 — `/chat/{domain}` 라우트 추가

**목표**: 도메인 챗 엔드포인트 + 스코프 세션 자동 라우팅.

**변경**:
- 수정 `backend/app/api/chat.py`
  - 신규 라우트 `POST /chat/{domain}` (domain ∈ REGISTRY)
  - 신규 헬퍼 `get_or_create_scoped_session(db, user_id, device_id, scope)` — (user, device, scope) 조합당 활성 1개 유지
  - 기존 `POST /chat`은 scope='orchestrator'로 동일 헬퍼 사용
  - 알 수 없는 domain → 404
  - 응답 body는 기존 `ChatResponse` 재사용

**verify**:
- `curl -X POST localhost:8000/chat/schedule -d '{"message":"내일 3시 회의","user_id":"..."}'` → 200
- `curl -X POST localhost:8000/chat/ledger ...` → 200 (assistant_message에 "아직 구현 안 됨" 류)
- `curl -X POST localhost:8000/chat/unknown ...` → 404
- DB에 (device_id, scope) 별 별도 session row 생성 확인

---

## Step 9 — `agent_models` config

**목표**: settings에서 도메인별 모델 라우팅을 코드/env에서 관리.

**변경**:
- 수정 `backend/app/core/config.py` `Settings`에 `agent_models: dict[str, str]` 추가 (spec section 9의 기본값)
- 환경 변수로 오버라이드 가능하도록 `Field(default_factory=...)` + Pydantic Settings JSON 파싱
- `.env.example`에 `AGENT_MODELS='{"orchestrator":"claude-sonnet-4-6", ...}'` 예시 추가

**verify**:
- `python -c "from app.core.config import get_settings; print(get_settings().agent_models)"` → dict 6개 키
- env 오버라이드: `AGENT_MODELS='{"orchestrator":"claude-haiku-4-5"}'` → 그 값이 우선

---

## Step 10 — 테스트/문서 정리

**목표**: 회귀 방지 + 메모 업데이트.

**변경**:
- `pytest backend/tests` 풀패스 통과
- `alembic upgrade head && alembic downgrade base && alembic upgrade head` 왕복
- `planning/AGENTS.md` 또는 별도 doc에 새 인터페이스 한 줄 요약 (오케스트레이터는 평면 도구 dispatch, 도메인 챗은 thin sub-agent, scope로 격리)

**verify**:
- 전체 pytest green
- docker compose up 새로 띄워서 frontend → /chat/schedule, /chat 양쪽 POST 동작

---

## 의존성 / 병렬 가능성

```
1 ─→ 2 ─→ 3 ─→ 4 ─→ 5 ─┐
                       ├→ 7 ─→ 8 ─→ 10
                  6 ───┘
9는 4 이후 어디서나 (Step 4가 settings.agent_models를 처음 참조)
```

병렬 가능한 짝: Step 5 (todo)와 Step 6 (stub들)은 독립. Step 9는 Step 4 이후 아무 때나.

## 비고

- 각 step 끝나면 별도 commit (Spec 12절 순서 그대로 commit 단위).
- Step 1 마이그레이션이 깨지면 그 자리에서 중단 — 이후 모든 step이 영향.
- `claude_agent_sdk`의 실제 API가 spec과 다르면 step 2의 `_call_llm` 헬퍼만 손보고 진행 가능.
