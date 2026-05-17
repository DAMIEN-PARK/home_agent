# Backend Schemas → Service Slim → Scripts (Phase 1-2-3)

**Status:** pending approval (ralplan)
**Date:** 2026-05-16
**Owner:** damien
**Scope:** `backend/`

## Context

`backend/app/api/` 라우터는 todo만 일관된 (Pydantic schema + service) 패턴을 따른다. chat / events / oauth는 inline Pydantic, 또는 `dict` 반환, 또는 라우터 안에 비즈니스 로직(httpx 호출 + DB 기록 등)이 혼재. `app/services/`도 schedule_service / google_calendar / calendar_sync는 있지만 chat·events·oauth용 service 모듈이 없다. seed/dev fixture 같은 운영 스크립트도 부재.

이 plan은 사용자 우선순위대로 1→2→3 순서로 단계별 PR 단위로 정리한다. 각 phase는 독립적으로 머지 가능해야 한다.

---

## RALPLAN-DR Summary

### Principles
1. **TodoService 패턴 일관성**: 새 도메인 스키마/서비스는 todo 모듈의 모양을 그대로 복제 (Pydantic in/out + Service class + `NotFoundError` + router에서 commit/refresh).
2. **표면 변화 0**: 기존 HTTP 응답 JSON 키/타입은 변경 금지. 새 스키마는 *기존 dict 응답을 그대로 직렬화*하는 모양으로만 정의.
3. **Frontend 동기화**: `frontend/src/lib/api.ts` 와 호환 — 응답 키 변동 없으면 프론트 변경 없음. 변동 시 동일 PR에서 같이 손본다.
4. **Migration-free**: Phase 1·2는 DB 스키마 변경 없음 (Pydantic + 라우터/서비스 리팩터링만). Phase 3 seed는 모델만 사용.
5. **테스트 보존**: `tests/test_chat_api.py`, `tests/test_events_api.py`, `tests/test_oauth.py` 통과 유지가 acceptance gate.

### Decision Drivers
1. **백엔드↔프론트엔드 타입 불일치 위험 감소** (현재 `dict` 반환 → 응답 contract 명세 없음)
2. **OAuth/Chat 라우터 비대화 방지** (chat.py는 dependency 5개 + run_turn 호출, oauth.py는 httpx + DB 혼재)
3. **운영 편의성** (시드 사용자/디바이스 생성, dev fixture 재현)

### Viable Options

**A. 단계 분할 (사용자 요청, Recommended)**
- Pros: PR 작아 리뷰 쉬움, 각 단계 독립 머지·롤백, frontend 동기화 시점 명확
- Cons: chat/events 스키마와 service slim 사이에 일시적 비대칭 (Phase 1 후에는 schema는 있으나 service 분리 전)

**B. 통합 PR (3단계 한꺼번에)**
- Pros: 스키마-서비스-스크립트가 한 번에 정합
- Cons: PR 비대, 리뷰 누락 위험, frontend 영향 범위 한 번에 노출
- **Invalidated**: 사용자가 1-2-3 순차 명시

**C. service-first (Phase 2 → 1 → 3 순서)**
- Pros: service 추출 시 자연스럽게 입출력 타입이 드러나 스키마 추출이 쉬움
- Cons: service 추출 PR 자체가 dict 그대로 옮기므로 의미 없음, 스키마 부재 상태가 더 길어짐
- **Invalidated**: 사용자 우선순위 반대

→ **Option A 채택**

---

## Phase 1 — `api/schemas/` 비대칭 해소

### 목표
chat / events / oauth 라우터가 모두 `response_model`을 갖고, request body도 schemas 모듈에서 import.

### 산출물
신규 파일:
- `backend/app/api/schemas/chat.py`:
  - `ChatRequest(message: str, user_id: UUID, session_id: UUID | None)`
  - `ToolCallOut(name: str, result: dict[str, Any])` — `orchestrator.py:80`의 `{"name": name, "result": res}` 구조에 정확히 맞춤. **`arguments` 필드 아님** (orchestrator는 LLM args를 응답에 포함하지 않음).
  - `ChatResponse(assistant_message: str, tool_calls: list[ToolCallOut])`
- `backend/app/api/schemas/events.py`:
  - `EventOut` — id/title/source/start_at/end_at/description. `field_serializer('start_at','end_at')` 추가해 `.isoformat()` 출력 강제 (마이크로초·tz 표기 동일성 보장).
  - `EventsResponse(events: list[EventOut])`
- `backend/app/api/schemas/oauth.py` — `OAuthCallbackResponse(ok: bool, scope: str | None)`

수정 파일:
- `backend/app/api/chat.py` — inline `ChatRequest`/`ChatResponse` 제거, schemas import. `tool_calls: list[dict]` → `list[ToolCallOut]` (`extra` 미설정 — orchestrator는 `{name, result}` 외 키를 내보내지 않으므로 strict가 desired contract).
- `backend/app/api/events.py` — `dict` → `EventsResponse` 반환. ORM Event → EventOut 매핑은 `model_config = ConfigDict(from_attributes=True)` + computed field 또는 명시 변환.
- `backend/app/api/oauth.py` — `/callback` 응답을 `OAuthCallbackResponse`로 명시. `/start`는 `RedirectResponse` 그대로 유지.

### 검증
- `pytest backend/tests/test_chat_api.py backend/tests/test_events_api.py backend/tests/test_oauth.py` 모두 통과
- **응답 byte-동일성 검사**: 변경 전 `curl /events?...` 응답을 baseline으로 캡처 → 변경 후 동일 호출 → `jq -S` 정렬 후 `diff` 0 byte 차이. baseline 캡처/비교 한 줄짜리 헬퍼를 `backend/scripts/check_response_shape.sh`에 함께 추가 (Phase 3에 포함시키되 Phase 1 검증에 사용).
- **OpenAPI codegen 동기화**: 백엔드 `/openapi.json` export → `frontend/src/lib/openapi.json` 갱신을 **같은 PR**에 포함. `frontend/src/lib/api.ts`에서 `tool_calls: unknown[]` → 생성 타입으로 교체.

### 비고
- `EventOut`의 `field_serializer('start_at','end_at')`는 `lambda v: v.isoformat()`로 고정해 현재 라우터의 `e.start_at.isoformat()` 출력과 byte-identical 보장. naive datetime 방어 차원에서 service 레이어에서 `astimezone(UTC)` 강제 (현재 DB는 `DateTime(timezone=True)`이므로 정상 경로에선 no-op).
- `events.py`의 query alias `from` 처리는 라우터에 그대로 남김 (Pydantic Query 모델로 빼지 않음 — 단일 라우트라 과잉).

---

## Phase 2a — oauth service 추출 (immediate)

### 목표
oauth 라우터에서 httpx 호출 + DB 토큰 저장 로직을 service로 분리. todo 패턴 (`TodoService` + `NotFoundError`) 모양 그대로.

### 산출물
신규 파일:
- `backend/app/services/oauth_google.py`:
  - `class GoogleOAuthService`
  - `build_auth_url(user_id: UUID | None) -> str` — settings·SCOPES·params 조합.
  - `async def handle_callback(session, code, state, *, http: httpx.AsyncClient | None = None) -> OAuthCallbackResult` — token exchange + `User.external_tokens` 업데이트. httpx 클라이언트 인자 주입 가능 (테스트 stub용).
  - `OAuthCallbackResult` dataclass: `ok: bool, scope: str | None`.

수정 파일:
- `backend/app/api/oauth.py` — `/start`, `/callback` 모두 `GoogleOAuthService` 호출만 남기고 본문 슬림화.

### 검증
- `pytest backend/tests/test_oauth.py` 통과.
- 기존 httpx mock을 service 인터페이스 지점으로 옮긴 후에도 회귀 없음.
- `/oauth/google/callback` 응답 JSON byte-identical (Phase 1 baseline 비교).

---

## Phase 2b — chat service 추출 (blocked precondition)

### 목표
chat 라우터에서 User 조회 + `run_turn` 호출 + 결과 매핑을 service로 이동.

### **Hard precondition (block until satisfied)**
- `backend/app/agents/orchestrator.py`의 미커밋 변경(`M`)이 **머지 또는 폐기**될 것. 의도가 확정되기 전에 chat service를 추출하면 두 번 재추출하는 위험 (현재 `tool_calls` shape이 `{name, result}`이지만 변경 중이라면 contract가 흔들림).
- 위 조건 충족 시점에 Phase 2b 진행. 충족 전엔 Phase 1 + 2a + 3 만 머지하고 멈춘다.

### 산출물 (precondition 충족 후)
신규 파일:
- `backend/app/services/chat.py`:
  - `class ChatService(session, user_id)`
  - `async def run(message, session_id, device_id, device_name) -> ChatResult`
  - `ChatResult` dataclass: `assistant_message: str, tool_calls: list[ToolCallOut]` (Phase 1에서 정의한 ToolCallOut 재사용).
  - `UserNotFoundError(NotFoundError)`.

수정 파일:
- `backend/app/api/chat.py` — 라우터 본문은 `service = ChatService(session, req.user_id); result = await service.run(...); return ChatResponse(**result)` 만 남김.

### 검증
- `pytest backend/tests/test_chat_api.py backend/tests/test_orchestrator.py` 통과.

### 비고
- events는 이미 `list_events`를 `schedule_service`에서 호출하므로 Phase 2 작업 대상 아님 (이미 slim).

---

## Phase 3 — `scripts/` 디렉터리

### 목표
로컬 dev 환경에서 빈 DB → 동작 가능한 상태까지 1 커맨드.

### 산출물
신규 파일:
- `backend/scripts/__init__.py`
- `backend/scripts/seed_dev.py` — `python -m scripts.seed_dev` 진입점. 다음을 멱등 생성:
  - default user (email: damien@bctone.kr, name: damien)
  - sample project + context + 3 tasks
  - sample local Event 2건 (오늘/내일)
- `backend/scripts/reset_db.py` — `--yes` flag 강제, alembic downgrade base + upgrade head + seed_dev 호출. 가드: `settings.environment != "production"` 검사.
- `backend/scripts/README.md` — 사용법 1페이지.

수정 파일:
- `backend/Makefile` 또는 `pyproject.toml` scripts 섹션에 alias 추가 (있다면). 없으면 README만.

### 검증
- 깨끗한 DB에서 `python -m scripts.seed_dev` → 에러 없이 종료, 재실행 시도 시 ON CONFLICT 또는 존재 체크로 멱등.
- `pytest` 영향 없음 (scripts는 import 안 됨).
- `python -m scripts.reset_db` 가 운영 환경에서 거부되는지 단위 테스트 1개.

### 비고
- alembic CLI 호출은 subprocess가 아니라 `alembic.command` 모듈 사용 — Windows shell 차이 회피.
- seed_dev는 SQLAlchemy `select` + 존재 시 skip 패턴 (todo 서비스에서 사용하는 비동기 세션 활용).
- `0004_session_device_columns.py`는 `core.sessions`에 `device_id`/`device_name`을 추가했지만, seed_dev는 user/project/context/task/event만 만들고 sessions는 만들지 않으므로 영향 없음. 향후 device 시드를 추가한다면 device 모델 존재 여부부터 확인 (현재 device 전용 모델 없음 — sessions 컬럼만 존재).

---

## ADR

- **Decision**: 1 → 2a → 3 순차 분할 PR (2b는 orchestrator 미커밋 변경 정리 후 별도). todo 패턴을 그대로 복제, 표면 변화 금지.
- **Drivers**: 프론트 contract 명세 부재, oauth 라우터 비대화 (chat은 이미 18줄로 작음), dev 환경 재현성.
- **Alternatives**:
  - **Option B (통합 PR)**: PR 비대 + frontend 영향 한꺼번에 노출 → 기각.
  - **Option C (service-first)**: 기술적 장점은 service 추출 시 dict shape이 드러나 schema 정의가 쉬워진다는 것. 그러나 표면 변화 0 원칙 하에선 Phase 1의 schema가 service 추출 후에도 그대로 유효 (입출력은 동일). 따라서 Phase 1 → 2 와 Phase 2 → 1 은 기술적으로 동치이며, 사용자가 명시한 1-2-3 순서를 따라도 손실 없음.
- **Why chosen**: 1-2-3 순서가 (a) 사용자 우선순위와 일치 (b) 기술적으로 동치 (c) 각 phase 독립 머지·롤백 + (d) 2b를 orchestrator 안정화에 게이팅함으로써 재추출 위험 회피.
- **Consequences**: Phase 1 직후엔 chat은 schema만 정리되고 service는 미분리 상태가 일시적으로 유지됨. 2a 머지 후엔 oauth만 깔끔하고 chat은 schema-only 상태. 2b는 orchestrator commit 후 진행.
- **Follow-ups**:
  - Phase 1 머지 후 `frontend/src/lib/api.ts`의 events·chat·oauth 응답 타입을 생성 OpenAPI 타입으로 교체.
  - orchestrator.py 미커밋 변경 의도 파악 → 머지 후 Phase 2b 트리거.
  - 추후 chat 응답에 `session_id` 포함 여부 결정 (현재 미반환).

## Acceptance Criteria

- **Phase 1**: 모든 라우터(`chat`, `events`, `oauth/callback`)에 `response_model` 명시. 기존 pytest 100% 통과. `curl` baseline → 변경 후 응답 `jq -S` diff 0 byte. `frontend/src/lib/openapi.json` 같은 PR에서 갱신.
- **Phase 2a (oauth)**: `/oauth/google/start`, `/oauth/google/callback` 라우터 본문에 httpx 호출과 DB 쓰기가 직접 등장하지 않음. `tests/test_oauth.py`의 httpx mock 지점이 `GoogleOAuthService` 인터페이스(예: `_exchange_code` 또는 주입된 `http`)로 이동. pytest 100% 통과.
- **Phase 2b (chat, blocked)**: chat 라우터 본문에서 `User` 조회·`run_turn` 호출·결과 매핑이 service로 전부 이동 — 라우터엔 `service.run(...)` 호출과 `ChatResponse(**result)` 반환만 남음. precondition: `backend/app/agents/orchestrator.py`의 미커밋 변경이 머지 또는 폐기되어 working tree clean.
- **Phase 3**: 깨끗한 DB → `python -m scripts.seed_dev` 1회 → 에러 없이 종료, 재실행 시 멱등 (행 수 동일). API가 seed 데이터로 즉시 응답. `python -m scripts.reset_db`는 `settings.environment == "production"`에서 SystemExit/예외 — 단위 테스트 1개로 검증.
