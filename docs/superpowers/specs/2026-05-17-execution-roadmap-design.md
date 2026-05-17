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

### Phase 1 — Backend chat.py 로컬리티 리팩터 (다층 서비스 분리)

- **Entry**: working tree clean. Main HEAD = current (5/17 작업 종료 기준; SHA pin 제거 — 시간 흐름에 따라 stale 방지).
- **다층 분리 (이미 결정)**: `ChatService`(orchestrator/domain dispatch) + `SessionService`(device/scope 세션) + `MessagePersistenceService`(turn + 첨부).
- **이동 대상 헬퍼 (6개 → 5개 service 이동 + 1개 router 잔존)**:
  - service로 이동: `_parse_input` (multipart), `_get_or_create_scoped_session`, `_save_attachments`, `_persist_turn`, `_load_recent_messages`
  - router 잔존: `_header_uuid` — HTTP request 헤더 파싱은 라우터 책임 (service에 Request 의존성 주입 회피)
- **결과물**:
  - `backend/app/services/chat_service.py`, `session_service.py`, `message_persistence_service.py` 신규
  - 라우터는 `service.run(...) + return ChatResponse(**result)` 패턴 + `_header_uuid` 보조함수 1개만
- **Acceptance**:
  - (a) `grep "^def _\|^async def _" backend/app/api/chat.py` → 1건 (`_header_uuid`만)
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
- **Non-goal (Phase 1 scope 외)**: `SessionService`는 Phase 1에서 **chat 라우터만 소비**. `events.py`/`oauth.py`의 사용은 Phase 1 scope 외 — 추후 별도 ralplan에서 결정.
- **Spec 진입 명령**: `/oh-my-claudecode:ralplan "chat.py 다층 서비스 분리: ChatService + SessionService + MessagePersistenceService"`

### Phase 4 — React Tailwind 토큰 이식 + 도메인 챗 border 포팅

- **Entry**: Phase 1 머지 후. (실제 데이터 의존성은 없으나 사용자 명시 순서 준수 + 백엔드 인지 표면 축소 후 React 작업이 더 명확.)
- **결과물**:
  - `frontend/tailwind.config.ts`의 `theme: { extend: {} }` (현재 비어있음)에 mockup spec §7 블록 등록:
    - `colors.domain.{schedule, todo, ledger, finance, ideas, files}` (각 base + soft pair)
    - `colors.cat.{food, transport, living, leisure, medical, fixed, misc}` (각 base + soft pair)
    - **hex 직접 등록** (opacity modifier 호환 — mockup spec §3 결정)
  - `Chat.tsx`, `Calendar.tsx`에 `bg-domain-*` / `bg-cat-*` / `text-domain-*` / `border-domain-*` utility 적용 (대응 mockup 화면과 같은 도메인 색)
  - commit `890825f`의 `.domain-chat.dom-*` border-left 패턴 포팅 — `Chat.tsx`의 도메인 인라인 챗 영역에 동등 시각 표현 (좌측 4px solid var(--domain-*))
- **Tailwind SSOT 채택** (v3 결정): `tailwind.config.ts`가 React 측 컬러 SSOT. `index.css`/`tokens.css`와 1:1 매핑 요구 폐기 — 현재 `frontend/src/index.css`에 `--domain-*`/`--cat-*` 변수 0개, hex 0개 (매핑 대상 부재). Tailwind utility가 유일한 consumption surface.
- **Acceptance**:
  - (a) **Hex byte-diff**: `tailwind.config.ts`의 `theme.extend.colors`가 mockup spec §7 (lines 51-65) hex 값 byte-for-byte 일치. 수동 diff (검토자가 spec 파일과 config 파일 양쪽 열어 13쌍 hex 일치 확인).
  - (b) **구조 게이트 (key-position 강화, comment line 게임 차단)**:
    - `grep -E "^\s*['\"]domain-(schedule|todo|ledger|finance|ideas|files)['\"]\s*:" frontend/tailwind.config.ts | wc -l` ≥ 6 (각 도메인 키 1줄, 6개)
    - `grep -E "^\s*['\"]cat-(food|transport|living|leisure|medical|fixed|misc)['\"]\s*:" frontend/tailwind.config.ts | wc -l` ≥ 7 (각 카테고리 키 1줄, 7개)
    - soft pair는 nested object 내부이므로 별도 카운트 안 함; (a) byte-diff가 soft 페어 존재까지 보장
  - (c) **utility 사용 게이트**: `grep -rn "bg-domain-\|bg-cat-\|text-domain-\|border-domain-" frontend/src --include="*.tsx"` → 최소 4건 (Chat.tsx + Calendar.tsx)
  - (d) **border port 게이트** (890825f 패턴): `grep -E "border-l-4 border-domain-" frontend/src/pages/Chat.tsx` → 각 도메인 챗 영역 렌더링부에 ≥1 매치
  - (e) **수동 비주얼 confirm**: Mid-gate 4 스크린샷에서 Chat·Calendar 페이지가 mockup 대응 화면과 같은 도메인 색
- **Spec 진입 명령**: `/oh-my-claudecode:ralplan "frontend Tailwind 토큰 이식: theme.extend.colors + Chat/Calendar 페이지 hex→utility + 890825f domain-chat border 포팅"`

### Mid-gate — Phase 4 직후 mandatory mini-verify (신규, v2)

- **What**: Chat.tsx + Calendar.tsx × {desktop 1440, mobile 390} = 4 스크린샷
- **Pass criteria**:
  - 토큰 매핑 일치 (대응 mockup 화면과 같은 색)
  - 모바일 drawer 동작 정상 (820px breakpoint)
  - **Console error 0** — capture method: (i) browse 도구로 navigate 후 `console.errors()` 호출 결과 빈 배열, OR (ii) 수동 Chrome DevTools console 비어있음 스크린샷. 1인 환경 — 둘 중 편한 쪽.
- **Cost**: ~15min. 자동화 불가 (시각 검증).
- **Record**: 결과는 commit message 또는 PR 본문에 기록.
- **Fail**: Phase 5 진입 전 fix. (Phase 5 entry condition에 mid-verify pass 포함)

### Phase 5 — Todoist 연동 (todo 에이전트 외부 백엔드)

- **Entry**:
  - Phase 4 머지 + mid-verify pass
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

```
Phase 1 (chat.py 로컬리티 리팩터, contract-invariant)
   │
   │ 백엔드 인지 표면 축소
   ▼
Phase 4 (Tailwind theme.extend + hex→utility + 890825f border 포팅)
   │
   │ ━━━ Mid-gate (mandatory) ━━━
   │     Chat/Calendar × desktop/mobile = 4 스크린샷, ~15min
   │     console error 0, drawer 동작, 토큰 매핑 일치
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
| 1 | Phase 1 ralplan이 다층 분리로 큰 PR 생성 | sub-phase 1a(SessionService)/1b(MessagePersistenceService)/1c(ChatService) 으로 더 쪼개야 할 수 있음 — Phase 1 ralplan에서 결정 |
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
