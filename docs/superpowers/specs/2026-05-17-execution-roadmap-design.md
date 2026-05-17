# 2026-05-17 home_agent 실행 로드맵 v3.2: backend slim → React 토큰 이식 → Todoist → mockup 후속 → 시각 검증

**Status:** pending approval (RALPLAN-DR v3.2, Critic APPROVED at iteration 4/5)
**Date:** 2026-05-17
**Owner:** damien
**Scope:** Meta-roadmap. 각 phase는 진입 시 자체 ralplan을 호출하여 implementation spec 작성.
**User-mandated sequence:** 1 → 4 → 5 → 2 → 3
**Iteration history:** v1 (Architect 9 issues + 2 principle violations) → v2 (Critic ITERATE, 5 issues) → v3 (Architect CONCERNS, 2 fixes) → v3.1 (Critic ITERATE, 1 fix) → v3.2 (Critic APPROVE)

**연관 문서:**
- `planning/2026-05-16-backend-schemas-services-scripts.md` (Phase 2b 부록 — Phase 1 다층 분리 결정 근거)
- `docs/superpowers/specs/2026-05-17-mockup-color-tokens-mobile.md` (§7 Tailwind 이식 블록, §8.2 V1~V7 시각 검증 체크리스트)
- Memory: `project_todoist_integration.md` (Todoist 연동 결정), `feedback_main-branch-default.md` (main 직접 작업), `feedback_decision-velocity.md` (결정 모이면 즉시 산출물)

---

## 1. RALPLAN-DR Summary

### Principles

1. **Locality-first refactor before token port** — Phase 1은 contract-invariant 보장. 목적은 React 이식(Phase 4) 시 chat.py 헬퍼 6개를 시야에 두지 않기 위해 백엔드 인지 표면 축소. (v1의 "contract-first"는 자기충족 prophecy였으므로 폐기.)
2. **외부 통합은 내부 격리 뒤** — Todoist같은 third-party는 ChatService/SessionService 패턴이 자리잡은 후 진입. 새 패턴 + 외부 API 동시 학습 회피.
3. **각 phase 독립 머지 + main visually-degradable** — 1인 사용자 환경 전제. main은 phase 사이에 시각적 회귀를 일시 허용. 단 Principle 5 mid-gate로 한정.
4. **YAGNI for polish phase** — Phase 2 후속은 React 이식 후 실 데이터 만져본 뒤 진짜 필요할 때만.
5. **Mid-gate at Phase 4 boundary** — Phase 3 시각 검증을 시퀀스 말미에만 두지 않고, **Phase 4 머지 직후 mandatory mini-verify** 추가 (Chat·Calendar 2화면 × desktop/mobile 2 viewport = 4 스크린샷, ~15min). Phase 2 완료 후 full V1~V7는 그대로.

### Decision Drivers

1. **백엔드 코드 인지 표면 축소** — chat.py 266줄·헬퍼 6개가 React 이식 작업자(또는 그 시점의 LLM 컨텍스트)에게 chat 백엔드를 "한 페이지에 안 들어오는 영역"으로 만듦. Phase 1은 contract 안정보다 readability/locality 목적.
2. **이중 작업 방지** — Tailwind theme.extend 등록 + Chat.tsx/Calendar.tsx hex→utility 치환 + `.domain-chat.dom-*` border 패턴(commit `890825f`) 포팅을 같은 phase에 묶어 한 번에.
3. **MVP scope 보존** — deferred 5개 후속이 폭발해 시퀀스 잠식하지 않도록 명시 분리.

### Viable Options

| Option | 설명 | Pros | Cons / Invalidation |
|---|---|---|---|
| **A. 1→4(+mid-verify)→5→2→3** (Recommended) | 사용자 명시 + Architect synthesis | 의존성·인지 표면 정합, mid-gate가 누적 회귀 방지 | Phase 5 entry가 mid-verify에 의존 안 함 — mid-verify failure 시 Phase 5 진입 결정 별도 필요 |
| **B. 4→1→5→2→3** (Architect steelman) | UI 가치 우선 노출 | 사용자-가시 가치 빠른 노출, Phase 1 자기충족 prophecy 회피 | chat.py 헬퍼 6개 안고 React 이식 → 인지 부담. 사용자 명시 순서 위반 |
| **C. 1→3→4→5→2** | 검증 조기 | 회귀 조기 발견 | Phase 3은 Phase 1과 의존 없음(독립). 본 v3.2의 mid-gate가 동일 효과를 더 적은 비용으로 달성. **Invalidated** |

→ **Option A 채택**. Architect steelman B는 mid-gate 추가로 risk 차이 축소 + 사용자 명시 우선.

---

## 2. Phase별 게이트

각 phase는 **진입 시 자체 ralplan을 호출**해 implementation spec을 만든다. 본 로드맵은 entry/exit/acceptance gate만 정의.

### Phase 1 — Backend chat.py 로컬리티 리팩터 (단일 ChatService 추출)

**Wording history**: v3.2 원안은 "다층 분리 — ChatService + SessionService + MessagePersistenceService" mandate였으나, Phase 1 ralplan (`docs/superpowers/specs/2026-05-17-chat-service-extraction-design.md`) Architect steelman으로 3-service split은 CLAUDE.md §2 ("speculative abstraction for single-use code") 위반으로 판명. Phase 1 v2에서 **단일 ChatService flat class** (TodoService 패턴 정확 일치)로 collapse. 본 §Phase 1 wording은 Phase 1 머지(commit 60f6733) 직후 정정됨. 결정 근거는 신규 **MA-3** 참조.

- **Entry**: working tree clean. Main HEAD = current (5/17 작업 종료 기준; SHA pin 제거 — 시간 흐름에 따라 stale 방지).
- **단일 ChatService 추출**: `ChatService` 1개 class (TodoService 패턴), session lifecycle + attachments + context loading + turn persistence + 2 public entry points(run_orchestrator/run_domain) 모두 internal section으로 조직.
- **이동 대상 헬퍼 (6개 → 5개 service + 1개 HTTP-input module)**:
  - `ChatService`로 이동: `_get_or_create_scoped_session`, `_save_attachments`, `_persist_turn`, `_load_recent_messages` (4개) + `_files = FilesAgent()` module singleton
  - `backend/app/api/_chat_input.py`로 이동: `_parse_input` → `parse_input`, `_ParsedInput` → `ParsedInput` (`@dataclass(slots=True)`), `_header_uuid` (HTTP request 헤더 파싱은 라우터 영역 유지)
- **결과물**:
  - `backend/app/services/chat_service.py` 신규 (단일 class)
  - `backend/app/api/_chat_input.py` 신규 (HTTP-input parsing)
  - `backend/app/services/chat_service.py::UnknownDomainError` — domain error, 라우터에서 HTTPException(404) translation (TodoService `NotFoundError` 동형)
  - 라우터는 `parse_input → user 조회 → ChatService.run_* → db.commit() → ChatResponse 반환`만 남음
- **Acceptance**:
  - (a) `grep -cE "^(async )?def _" backend/app/api/chat.py` → 0건 (모든 헬퍼 이동)
  - (b) `tests/test_chat_api.py` 그린 유지
  - (c) **신규 contract assertion test** — `backend/tests/test_chat_api.py`에 `test_chat_response_contract` 함수 추가 (Phase 1 시작 전 commit):
    - **기준선 검증 (plan-write 시점)**: `backend/app/api/schemas/chat.py:18-20` 에서 `ChatResponse = {assistant_message: str, tool_calls: list[ToolCallOut]}` 정확 2필드. `ToolCallOut = {name: str, result: dict[str, Any]}` 정확 2필드. 추가 필드 없음 확인됨.
    - fixed mock input (user_id, message, no attachments, no session_id) 으로 `POST /chat` 호출
    - `assert set(response.json().keys()) == {"assistant_message", "tool_calls"}` (정확 일치)
    - `assert isinstance(response.json()["assistant_message"], str)`
    - `assert isinstance(response.json()["tool_calls"], list)`
    - `tool_calls` 비어있지 않으면 각 element keys == `{"name", "result"}`
    - 동일 테스트가 Phase 1 머지 후에도 그린 → contract 무변동 입증
    - **Rationale for exact equality** (not subset): 1인 프로젝트 + `ChatResponse`가 `frontend/src/lib/api.ts`와 1:1 contract. 필드 추가도 frontend 영향이 있는 변경 → 의식적 검토 강제가 옳음 (drift detection).
  - (d) **외부 의존성 추가 없음**: `pyproject.toml` dev deps 무변동. 기존 `resp.json()` + key assertion 패턴 (`test_chat_api.py:33-36`) 재사용. `syrupy` 등 snapshot 라이브러리 도입 금지.
  - (e) frontend `api.ts` working-tree 변경은 Phase 1과 독립 — 별도 commit으로 분리 처리 (Phase 1 PR에 포함 금지).
- **Non-goal (Phase 1 scope 외)**: `ChatService`는 chat 라우터만 소비. `events.py`/`oauth.py`의 service 추출은 별도 ralplan. session/persistence 로직을 다른 도메인에서 재사용할 필요가 실측 발생할 때만 별도 ralplan으로 분리 검토 (지금은 single consumer — YAGNI).
- **Spec 진입 명령** (실행 완료): `/oh-my-claudecode:ralplan "chat.py 다층 서비스 분리: ChatService + SessionService + MessagePersistenceService"` → Phase 1 ralplan 결과 단일 ChatService로 수정됨. Spec: `docs/superpowers/specs/2026-05-17-chat-service-extraction-design.md`.

### Phase 4 — React Tailwind 토큰 이식 (border 포팅은 Phase 4.5로 이관)

**Wording history**: 원안은 "Tailwind 토큰 + Chat/Calendar hex→utility + **890825f .domain-chat.dom-* border 포팅**" mandate였으나, Phase 4 ralplan (`docs/superpowers/specs/2026-05-17-frontend-tailwind-tokens-design.md`) Architect steelman으로 React에 도메인 페이지(Schedule.tsx 등) 미존재 → border 포팅 대상 컴포넌트 부재 판명. v3에서 **단일 ChatService 추출(MA-3)과 동일 패턴**으로 deferred + Phase 4.5 신설. MA-4 (ii) 정합 (prerequisite 컴포넌트 부재). 본 §Phase 4 wording은 Phase 4 머지(commit `abef6c8`) 직후 정정됨.

- **Entry**: Phase 1 머지 후.
- **단일 atomic 작업 (3 파일)**:
  - `frontend/tailwind.config.ts`: `theme.extend.colors`에 mockup spec §7 lines 286-309 블록 byte-equal 등록 (6 도메인 + 7 카테고리, 각 `{DEFAULT, soft}` 페어, **hex 직접 — opacity modifier 호환**, mockup spec §3 결정).
  - `frontend/src/pages/Calendar.tsx`: 월 헤더 `text-domain-schedule` + local event `border-domain-schedule` (2-consumer end-to-end proof).
  - `frontend/src/components/Sidebar.tsx`: `flex flex-col` → `hidden md:flex flex-col` (모바일 hide, mid-gate screenshot 의미 확보).
- **Chat.tsx 변경 0**: orchestrator entry, 도메인 context 부재. Tailwind indigo-600 = mockup `--accent #4f46e5` 정확 일치 → 변경 무의미.
- **Tailwind SSOT 채택**: `tailwind.config.ts`가 React 측 컬러 SSOT. `index.css`/`tokens.css`와 1:1 매핑 요구 폐기 — 현재 `frontend/src/index.css`에 `--domain-*`/`--cat-*` 변수 0개, hex 0개 (매핑 대상 부재).
- **Acceptance** (Phase 4 ralplan §3 그대로):
  - (a-1) **구조 게이트 (automated grep)**: domain 키 6 / cat 키 7 / DEFAULT ≥13 / soft ≥13
  - (a-2) **수동 byte-equal diff**: mockup spec §7 (lines 286-309) vs `tailwind.config.ts theme.extend.colors` 26 hex 일치
  - (c) **utility 소비처 ≥2** (Calendar.tsx 단독 — fabricated UI 금지): `grep -cE "(bg|text|border)-(domain|cat)-" frontend/src/pages/Calendar.tsx` ≥ 2
  - (d) ~~border-l-4 border-domain- in Chat.tsx~~ → **DEFERRED to Phase 4.5: First domain page (Schedule.tsx)**
  - (e) Calendar.tsx `border-domain-schedule` ≥1
  - (f) Sidebar.tsx `hidden md:flex` ≥1
  - (g) Mid-gate 4 스크린샷 — 아래 §Mid-gate 참조
  - (h) `npm run build` exit 0, (i) `npm run test` 그린, (j) `package.json`/`lock` 무변동
- **Spec 진입 명령** (실행 완료): `/oh-my-claudecode:ralplan "frontend Tailwind 토큰 이식: theme.extend.colors + Chat/Calendar 페이지 hex→utility + 890825f domain-chat border 포팅"` → border 포팅 부분은 Phase 4.5로 이관됨. Spec: `docs/superpowers/specs/2026-05-17-frontend-tailwind-tokens-design.md`. Implementation commit: `abef6c8`.

### Mid-gate — Phase 4 직후 mandatory mini-verify (Phase 4 ralplan에서 scope 조정됨)

- **What**: Chat.tsx + Calendar.tsx × {desktop 1440, mobile 390} = 4 스크린샷
- **Pass criteria**:
  - 토큰 매핑 일치 (대응 mockup 화면과 같은 색): Calendar 월 헤더 보라색 + local event 보라색 + google event 초록색 + Chat 색 무변동(indigo)
  - **Sidebar 모바일 hide** (`hidden md:flex` 적용 확인) — drawer 자체는 Phase 4.5+로 deferred (React에 drawer toggle 미구현, Sidebar.tsx always-visible이었음)
  - **Console error 0** — capture method: (i) browse 도구 `console.errors()` 빈 배열, OR (ii) Chrome DevTools console 비어있음 스크린샷. 1인 환경 — 둘 중 편한 쪽.
- **Cost**: ~15min. 자동화 불가 (시각 검증).
- **Record**: 결과는 commit message 또는 PR 본문에 기록.
- **Fail**: Phase 4.5 진입 전 fix. 거부 시 Phase 4 ralplan §5 Risk #2 fallback (day-of-week header `bg-stone-50` → `bg-domain-schedule-soft`) 적용.

### Phase 4.5 — First domain page (Schedule.tsx) + .domain-chat border 포팅 (신규)

**신설 사유**: Phase 4 ralplan Architect 발견 — 메타-로드맵 §Phase 4 결과물의 "Chat.tsx 도메인 인라인 챗 영역 border 포팅"이 도메인 페이지 React 부재로 적용 불가. Tailwind 토큰은 이미 Phase 4에서 등록되어 즉시 사용 가능. Phase 4.5는 첫 도메인 페이지 1개(Schedule.tsx)에서 토큰 + border 패턴이 작동함을 입증.

- **Entry**: Phase 4 머지 (`abef6c8`) + Mid-gate pass
- **결과물**:
  - `frontend/src/pages/Schedule.tsx` 신규 (mockup `planning/screens/schedule.html`의 React 이식 — 캘린더 + 도메인 챗 영역)
  - 도메인 챗 영역에 `<div className="border-l-4 border-domain-schedule ...">` 적용 (mockup `_shared/style.css:440` `.domain-chat.dom-schedule` border-left 패턴 React 등가)
  - `App.tsx` 라우터에 `/schedule` 추가, `Sidebar.tsx`에 NavLink 추가
- **Acceptance**:
  - `grep -E "border-l-4 border-domain-schedule" frontend/src/pages/Schedule.tsx` ≥1 (메타-로드맵 §Phase 4 acceptance (d)의 이관 충족)
  - Schedule.tsx mid-verify: desktop 1440 + mobile 390 스크린샷 + console error 0
  - 기존 Chat/Calendar 회귀 없음 (test 4건 그대로 그린)
- **Out of scope (Phase 4.5)**:
  - 나머지 5개 도메인 페이지 (todo/ledger/finance/ideas/files) — 별도 phase
  - 모바일 drawer toggle — 별도 UX phase
  - Schedule.tsx의 backend 연동 깊이 — events list 표시까지만, CRUD는 후속
- **Spec 진입 명령**: `/oh-my-claudecode:ralplan "Schedule.tsx 첫 도메인 페이지 + .domain-chat border 포팅"`

### Phase 5 — Todoist 연동 (todo 에이전트 외부 백엔드)

- **Entry**:
  - Phase 4 머지 + Mid-gate pass + **Phase 4.5 머지** (Schedule.tsx + .domain-chat border 포팅 — 메타-로드맵 §Phase 4 acceptance (d) 이관 충족)
  - **Task 모델 migration spec 작성 완료** (entry gate, in-phase 결정 아님) — Phase 5 ralplan 시작 전 별도 짧은 spec
- **Migration scope (entry gate)**: `backend/app/db/models/todo.py:43` Task 모델에 `source: str` + `external_id: str | None` + `UniqueConstraint("user_id", "source", "external_id")` 추가 — `backend/app/db/models/schedule.py:14,25-26` events 패턴 미러. Alembic migration 별도.
- **선행 패턴**: `schedule_agent ↔ Google Calendar` (`backend/app/services/calendar_sync.py::sync_user_google_calendar`, `schedule_service.py::upsert_google_event`)와 동형.
- **결과물**:
  - `backend/app/services/todoist.py` (HTTP 클라이언트)
  - `backend/app/services/todoist_sync.py` (sync orchestration — `upsert_todoist_task` 미러)
  - Todoist OAuth callback (`backend/app/services/oauth_google.py` 패턴 미러 — 새 라우터 또는 `oauth.py` 확장)
  - todo 에이전트의 `add_todo` / `list_todos` / `complete_todo` tool이 Todoist API 호출 + sync
  - alembic migration: tasks 테이블에 `source`/`external_id` 컬럼 + `UniqueConstraint`
- **Acceptance**:
  - Todoist sandbox 토큰으로 e2e: 로컬 add → Todoist UI 노출, Todoist add → 다음 sync에서 로컬 노출, 완료 양방향 sync
  - 기존 todo 라우터 응답 contract 무변동
  - secret 저장: 기존 JSON dict 패턴 (`existing["todoist"] = {access_token, refresh_token, scope}`) — Meta-ADR MA-1 결정
- **Open Risks (in-phase 결정 필요)**: project 매핑 정책 (Todoist project = home_agent project 1:1 vs N:1), conflict resolution (delete-edit race), webhook vs polling 주기
- **Spec 진입 명령**: `/oh-my-claudecode:ralplan "Todoist 연동: todo 에이전트 외부 백엔드 (schedule↔Google Calendar 패턴 동형)"`

### Phase 2 — Mockup 후속 (deferred 분할 처리)

- **Entry**: Phase 5 머지 후 또는 사용자가 명시적으로 우선순위 끌어올릴 때
- **후보 (각각 별도 spec 필요, 차트 라이브러리 선정은 #1 ralplan 내 결정)**:
  1. 차트 컴포넌트화 — 라이브러리 선정(recharts vs chart.js) 포함
  2. 대시보드 "오케스트레이터 인사이트" 카드 위치 변경
  3. stat 카드 → 도메인 화면 drill-down 링크 (`<a>` wrap)
  4. 데이터 신선도 timestamp (stat 카드별 "as of HH:MM")
  5. 다크 모드 (토큰 페어링 전략 — 진입 시 결정)
- **본 로드맵 위치**: 명시 deferred. Phase 5까지 완료 후 어느 항목이 실 데이터 운용에서 진짜 필요한지 평가 후 항목별 ralplan.
- **Acceptance**: 각 후속 spec 별도 정의.

### Phase 3 — 시각 회귀 최종 검증 (V1~V7 full)

- **Entry**: Phase 2 일부/전부 완료. Mid-gate에서 cover 안 된 mockup 9화면 + Phase 2에서 추가된 컴포넌트.
- **결과물**: spec `docs/superpowers/specs/2026-05-17-mockup-color-tokens-mobile.md` §8.2의 V1~V7 desktop(1440) + mobile(390) 전 화면 보고서.
- **Acceptance**:
  - 11개 mockup + React 페이지 전부 통과
  - 회귀 발견 시 fix → 재검증 (mini loop)
- **Note**: Phase 4 직후 mid-gate가 Chat/Calendar는 이미 커버. 본 phase는 mockup + Phase 2 신규 컴포넌트의 회귀 점검 책임.

---

## 3. Sequence Flow

사용자 명시 원안 시퀀스 **1→4→5→2→3은 유지**. Phase 4.5는 4의 자연 연장 sub-phase로 표기 (5→2→3 시퀀스 의미 불변, phase 카운트만 +1).

```
Phase 1 (chat.py 로컬리티 리팩터, contract-invariant)
   │
   │ 백엔드 인지 표면 축소
   ▼
Phase 4 (Tailwind theme.extend + Calendar 2-consumer + Sidebar 모바일 hide)
   │
   │ ━━━ Mid-gate (mandatory) ━━━
   │     Chat/Calendar × desktop/mobile = 4 스크린샷, ~15min
   │     console error 0, 토큰 매핑 일치, Sidebar 모바일 hide 확인
   ▼
Phase 4.5 (Schedule.tsx 첫 도메인 페이지 + .domain-chat border 포팅)
   │
   │ 메타-로드맵 §Phase 4 acceptance (d) 이관 충족
   ▼
Phase 5 (Todoist 연동)
   │ entry gate: Task.source/external_id migration spec 완료
   │ 양방향 sync 안정
   ▼
Phase 2 (mockup 후속 — 분할, 항목별 ralplan)
   │
   │ 실 데이터 polish
   ▼
Phase 3 (mockup + 신규 컴포넌트 full 시각 회귀 검증)
```

---

## 4. Out of Scope (메타 plan)

- 각 phase implementation 디테일 (별도 ralplan)
- Phase 2 후속 5항목의 라이브러리 선정·디자인 — 각 항목 ralplan에서 결정
- 신규 도메인 에이전트 추가 (현재 6개 sub-agent 외)
- 인프라 변경 (docker-compose, CI/CD)
- Todoist webhook vs polling 결정 — Phase 5 ralplan
- 태블릿 (820~1100) 별도 최적화 — mockup spec §2 deferred 그대로 유지

---

## 5. Open Risks (메타 plan 레벨)

| # | Risk | Mitigation |
|---|---|---|
| 1 | ~~Phase 1 ralplan이 다층 분리로 큰 PR 생성~~ — **해당 없음** | Phase 1 ralplan에서 단일 ChatService (MA-3)로 결정. ~250 LOC churn으로 단일 atomic PR (commit 60f6733). sub-phase 1a/1b/1c 불필요. |
| 2 | Phase 5 양방향 sync conflict가 todo 라우터 contract 침범 | conflict 발생 시 새 에러 상태 필요. v3.2 acceptance "contract 무변동"이 silent conflict swallowing 강제 risk → Phase 5 ralplan에서 conflict 결과 표현 방식 명시 |
| 3 | Mid-gate failure → Phase 5 진입 결정 모호 | fail 시 Phase 4 fix 후 mid-gate 재실행. 본 로드맵은 abort/escalate 정책 정의 안 함 — 1인 사용자 판단 (accepted, no mitigation) |
| 4 | Phase 2 5항목 폭발 | 명시 deferred + 항목별 spec 강제 (재진입 시 본 로드맵 재확인) |
| 5 | Phase 1 SessionService가 다른 라우터로 spillover | non-goal 명시로 차단. 추후 reuse 요구 시 별도 ralplan |

---

## 6. Meta-ADR (roadmap-level decisions, phase ralplan에서 재논의 금지)

### MA-1: Todoist token storage strategy

**Decision**: 기존 user OAuth JSON dict 패턴 재사용. `backend/app/services/oauth_google.py:77`의 `existing["google"] = {refresh_token, scope}` 패턴을 확장하여 `existing["todoist"] = {access_token, refresh_token, scope}` 형태로 저장.

**Rationale**:
- `oauth_google.py:77` precedent 존재 — 패턴 일관성
- 새 polymorphic `oauth_tokens` 테이블 추가 비용 회피
- 1인 사용자 환경 적합 (token 종류 적음)

**Consequence**: 본 결정은 Phase 5 ralplan 진입 시 재논의 금지. 변경 시 본 로드맵 reopen.

### MA-2: External-id mirror policy

**Decision**: Todoist Task ↔ 내부 Task 매핑은 schedule Event와 동형으로 `source` + `external_id` + `UniqueConstraint("user_id", "source", "external_id")` 컬럼을 Task 모델에 추가.

**Rationale**:
- `backend/app/db/models/schedule.py:14,25-26` precedent
- 향후 다른 외부 backend 추가 시 동일 모양으로 확장 가능
- 패턴 일관성 (events ↔ tasks 동형)

**Consequence**: 본 결정은 Phase 5 ralplan 진입 시 재논의 금지. Phase 5 entry gate(Task migration spec)는 이 결정을 그대로 적용.

### MA-3: Single-service flat pattern for chat domain

**Decision**: chat 도메인의 backend service는 **단일 ChatService** flat class. 메타 로드맵 v3.2 원안의 "ChatService + SessionService + MessagePersistenceService" 3-service 분리는 폐기.

**Rationale**:
- TodoService(`backend/app/services/todo.py:14-17`) canonical pattern과 정확 일치 — 단일 class, `__init__(session, user)`, internal section 조직
- 3-service split은 **single consumer**(chat 라우터 하나) 대상의 abstraction → CLAUDE.md §2 ("No abstractions for single-use code") 위반
- session/persistence 로직을 다른 도메인이 재사용할 필요는 실측 없음 — speculative future-proofing 회피
- Phase 1 ralplan Architect steelman + Critic APPROVE (iteration 1)

**Consequence**: 향후 외부 통합 service (Phase 5 Todoist 등)도 동일 flat 패턴으로 진입. 만약 session/persistence를 정말 다른 도메인에서 재사용해야 한다면 그 시점에 별도 ralplan으로 분리 검토 (지금 분리는 금지).

**Precedent commit**: `60f6733 refactor(chat): extract ChatService + slim router (Phase 1)`

### MA-4: General deviation protocol (approved roadmap items become advisory)

**Decision**: Approved roadmap line items become advisory when subsequent verified state contradicts them; deviation requires (a) post-hoc amendment commit, (b) ADR entry naming the deviation + reason + successor phase.

**Permitted only when**:
- (i) deviation is forced by CLAUDE.md project rule (e.g., §2 "no abstractions for single-use code", §3 "surgical changes"), OR
- (ii) deviation is forced by missing prerequisite state **that was explicitly named in a prior approved phase and is verifiably absent in the codebase at the time of deviation** (e.g., `_chat_input.py` was absent in Phase 1, domain page React routes were absent in Phase 4)

**Rationale**:
- 메타-로드맵은 합의 artifact이지만 frozen 명세 아님. 실제 verified state과 충돌 시 strict adherence는 CLAUDE.md project rule 위반 강제 → 본 메타 합의보다 project rule 우선.
- 단 (i)/(ii) 조건 외 임의 deviation은 금지 (drift 방지). 후속 phase는 본 protocol을 evidence trail로 사용.

**Permitted patterns observed**:
- Phase 1 (MA-3): 3-service mandate → 단일 ChatService (CLAUDE.md §2 force)
- Phase 4: Chat.tsx border 포팅 + 모바일 drawer mandate → Phase 4.5로 이관 (MA-4 (ii): prerequisite Schedule.tsx + drawer 미존재)

**Precedent commits**:
- Phase 1: `60f6733` + `74b31ad docs(planning): correct §Phase 1 — single ChatService`
- Phase 4: `abef6c8 feat(frontend): port mockup color tokens to Tailwind + Calendar consumers (Phase 4)` + 본 후처리 commit

---

## 7. ADR (Architecture Decision Record)

### Decision
1 → 4 (+ mandatory mid-gate) → 5 (+ migration entry gate) → 2 (분할 후속) → 3 (full 시각 회귀) 순차 실행. 각 phase는 자체 ralplan + main 독립 머지.

### Drivers
- 백엔드 코드 인지 표면 축소 (Phase 1 → Phase 4)
- React 토큰 이식 동시성 (Tailwind config + utility 치환 + border 포팅 한 phase)
- 외부 통합 격리 (Phase 1 service 패턴 자리잡은 후 Phase 5 진입)
- MVP scope 보존 (Phase 2 deferred 5항목 명시 분리)
- 회귀 게이트 (Mid-gate + 최종 Phase 3)

### Alternatives considered
- **B. 4→1→5→2→3** (UI 가치 우선): chat.py 헬퍼 안고 React 이식 시 인지 부담 + 사용자 명시 순서 위반
- **C. 1→3→4→5→2** (검증 조기): Phase 3은 Phase 1과 의존 없음 → mid-gate가 더 cheap하게 동일 효과

### Why chosen
- 사용자 명시 + 의존성 그래프 합치
- B의 회귀 risk를 mid-gate 추가로 해소
- C의 검증 효과를 mid-gate가 더 적은 비용으로 달성

### Consequences
- Phase 1은 contract-invariant 리팩터 — readability/locality 목적이라는 점이 명시되어야 작업자 동기 명확
- Mid-gate 1회 추가 → ~15min, 자동화 불가 (1인 환경 accepted)
- Phase 2 deferred 5항목이 영구 미진행 가능 (정상 — YAGNI)
- 각 phase 진입 시 별도 ralplan 호출 필요 (workflow 부담 — but 메타 plan 1회로 합의 비용 amortize)

### Follow-ups
- 본 plan approve 즉시 `/oh-my-claudecode:ralplan "chat.py 다층 서비스 분리: ChatService + SessionService + MessagePersistenceService"` 호출로 Phase 1 진입
- Phase 1 ralplan 결과에 따라 본 로드맵의 Phase 1 entry/acceptance 갱신 가능 (단 메타 시퀀스 1→4→5→2→3은 변경 시 본 로드맵 reopen)
- 각 phase 머지 후 main에 commit, 다음 phase 진입 전 `git status` clean 확인

---

## 8. Verification References

본 spec의 사실 주장은 다음 소스에서 확인됨 (Critic/Architect verification log):

- `backend/app/api/chat.py:42` — `_header_uuid` helper (router-jurisdiction)
- `backend/app/api/chat.py:222,266` — 두 라우터 모두 `return ChatResponse(**result)` (contract-invariance 입증)
- `backend/app/api/schemas/chat.py:13-20` — ChatResponse, ToolCallOut 필드 정확 2개씩 (Phase 1 acceptance (c) 기준선)
- `backend/app/services/oauth_google.py:77` — `existing["google"] = {...}` JSON dict 패턴 (MA-1 precedent)
- `backend/app/db/models/schedule.py:14,25-26` — `source` + `external_id` + `UniqueConstraint` 패턴 (MA-2 precedent)
- `backend/app/db/models/todo.py:43-73` — Task 모델에 source/external_id 부재 확인 (Phase 5 migration 필요)
- `backend/app/services/calendar_sync.py:36-45` — `upsert_google_event` 패턴 (Phase 5 Todoist sync 미러)
- `backend/tests/test_chat_api.py:33-36` — 기존 `resp.json()` + key assertion 패턴 (Phase 1 (c) 재사용)
- `backend/pyproject.toml:25-34` — dev deps에 snapshot 라이브러리 없음 (Phase 1 (d) 외부 의존성 추가 금지)
- `frontend/tailwind.config.ts:6` — `theme: { extend: {} }` 비어있음 (Phase 4 작업 대상)
- `frontend/src/index.css:1-13` — `--domain-*`/`--cat-*` 변수 0개, hex 0개 (Tailwind SSOT 채택 근거)
- `frontend/src/pages/Chat.tsx`, `Calendar.tsx` — `bg-domain-*`/`bg-cat-*` 사용 0건 today (Phase 4 acceptance 강화 근거)
- `planning/screens/_shared/style.css:440-445` — commit `890825f` `.domain-chat.dom-*` border 룰 (Phase 4 포팅 대상)
- `docs/superpowers/specs/2026-05-17-mockup-color-tokens-mobile.md` §3 (lines 32-42), §7 (lines 282-313), §8.2 (line 330) — hex 결정, Tailwind 이식 블록, V1~V7 시각 검증

---

## 9. Status & Next Action

- **Status**: pending approval (RALPLAN-DR Critic APPROVED v3.2, iteration 4 of 5)
- **Next action**: 본 spec 사용자 검토 → approve 시 즉시 Phase 1 ralplan 호출:
  ```
  /oh-my-claudecode:ralplan "chat.py 다층 서비스 분리: ChatService + SessionService + MessagePersistenceService"
  ```
- **Sequence guarantee**: 본 plan에서 implementation 단계는 호출되지 않음. 메타 시퀀스 결정만 commit.
