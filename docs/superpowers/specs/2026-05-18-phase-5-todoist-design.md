# Phase 5: Todoist 연동 — Write-through asymmetric sync

**Status:** pending approval (RALPLAN-DR v3, Critic APPROVED at iteration 2/5, **deliberate mode**)
**Date:** 2026-05-18
**Owner:** damien
**Parent roadmap:** `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` (§Phase 5)
**Scope:** Todoist 연동을 todo 에이전트의 외부 백엔드로 추가. write-through asymmetric sync (local create/update push + on-demand pull). OAuth + 모델 migration + sync orchestration + agent tool 1건 추가. **MA-4 트리거 없음** — 메타-로드맵 mandate strict 충족.

**Iteration history:**
- v1 (Option A one-way pull "Google parity"): memory "동형" strict 적용. → Architect NOT-approved: spec primacy 위반 ("양방향" acceptance binding), §2 misapplied, schedule_service precedent miscited
- v2 (Option C-lite write-through asymmetric, Architect synthesis): 8 issues 흡수. → Critic ITERATE 12 issues (3 HIGH: MA-1 drift, Risk #2 unresolved, test count vague) + pre-mortem/test caveats
- v3 (12 fixes + pre-mortem S7 신규 + test enumeration): → Critic **APPROVE** at iteration 2 + 2 minor non-blocking observations (반영)

---

## 1. RALPLAN-DR Summary (deliberate mode)

### Principles

1. **Spec primacy** — 메타-로드맵 acceptance "양방향 sync" 가 binding. memory "동형" 휴리스틱은 이를 override 못 함 (Architect 명시).
2. **Write-through asymmetric** — `add_task` / `complete_task` / `set_priority`: local update + 동기 Todoist push. `sync_todoist`: Todoist → local pull (on-demand). 양방향 그러나 conflict resolution machinery 없음 (last-write-wins by call order).
3. **Commit semantics boundary** — `TodoService` (legacy todo.py) = **flush only** (router commits, ChatService 패턴). `todoist_sync.py` (sync + upsert + tombstone) = **service commits** (schedule_service precedent). `push_local_task` = **flush only** (chat turn commit과 통합).
4. **Tombstone for upstream DELETE** — Todoist 측 삭제된 source="todoist" task는 local에서 `status="deferred"` 마킹 (hard-delete 회피). Tombstone은 **immutable** (`status`만 변경, 다른 필드 갱신 없음).
5. **MA-1 / MA-2 strict** — token `existing["todoist"] = {access_token, refresh_token: None, scope}` (3-key shape 유지, Todoist OAuth는 refresh_token 미발급 → None). Task 모델 `source` + `external_id` + `UniqueConstraint("source","external_id")` (schedule.events 미러).

### Decision Drivers

1. 메타-로드맵 acceptance "양방향" strict 충족 (deviation 0, MA-4 트리거 없음)
2. CLAUDE.md §1 (surface tradeoffs) + §4 (verifiable goals via expanded test plan)
3. 1인 환경 minimum: single default project + on-demand trigger + retry cap 5

### Viable Options

| Option | 설명 | Pros | Cons |
|---|---|---|---|
| **C-lite. Write-through asymmetric** (Architect synthesis, **Recommended**) | local create/edit → Todoist push (sync); Todoist→local pull on-demand; tombstone DELETE | acceptance 충족, ~350 LOC, conflict 없음 (last-write-wins), single default project | push 실패 시 `sync_state="pending"` 재시도 (S6) |
| **A. One-way pull (Google parity)** | Todoist→local만 | ~250 LOC, 패턴 동일 | acceptance "양방향" 위반 — **v1 폐기, Architect NOT-approved** |
| **B. Full bidirectional + conflict ML** | + last-write-wins ML + project mapping | strict bidirectional | ~500 LOC, speculative, CLAUDE.md §2 위반 |

→ **Option C-lite 채택**.

---

## 2. Pre-mortem (deliberate mode, 7 scenarios)

| # | Scenario | Mitigation |
|---|---|---|
| **S1** | Todoist API rate-limit (450 req / 15min) 초과 — 초기 bulk sync에서 429 | `httpx` exponential backoff + retry-on-429. `sync_user_todoist` 는 idempotent (upsert) — 재실행 safe. Integration test에서 검증. |
| **S2** | 사용자 local edit on source="todoist" task | **즉시 push 동기 동작** — silent overwrite 없음. push 실패 시 `sync_state="pending"` + 다음 sync 재시도. (v2 "design 의도" rebrand 폐기) |
| **S3** | Todoist OAuth token revoked | `TodoistClient`가 401 → `TodoistAuthError` raise. `/api/todoist/sync` catch → 422 응답 + `user.external_tokens["todoist"] = None` 클리어 + log. Agent surface 메시지: "Todoist 재인증 필요. /oauth/todoist/start 를 새 창에서 열어주세요." |
| **S4** | Upstream Todoist task DELETE | pull 시 server 에 없는 source="todoist" task → `tombstone_missing_todoist_tasks` 가 `status="deferred"` + `synced_at=now` 마킹. Hard-delete 회피로 user 인지 가능. Tombstone은 immutable (다른 필드 갱신 없음). |
| **S5** | 동일 external_id 재upsert (re-pull) | `UniqueConstraint("source","external_id")` + idempotent upsert — no-op. |
| **S6** | local create push 실패 (Todoist 다운) | local insert 성공 + Todoist POST 실패 → `external_id=NULL` + `sync_state="pending"` + `retry_count=1` + 다음 `/sync` 에서 재시도. `retry_count >= 5` 시 `sync_state="failed"`. Failed task는 자동 재시도 안 함 (manual unblock: 사용자가 `/sync` 직접 호출 시 failed → pending 재활성화 옵션 검토 — **본 phase scope에서는 manual DB reset만 지원, 자동화는 별도 spec**). |
| **S7** (신규) | Todoist project archival mid-sync — 사용자가 default project를 archive → 후속 push가 archived project_id 참조 → 422 | `_fetch_default_project_id(client) -> str` helper가 매 sync 시작 시 project list 재조회. archived 시 Inbox (Todoist 시스템 default) 로 fallback. |

---

## 3. Expanded Test Plan (deliberate mode, 4 layers, ≥13 enumerated tests)

| Layer | File | Test | Coverage |
|---|---|---|---|
| Unit | `tests/test_todoist_client.py` | `test_list_tasks_parses_payload` | TodoistClient.list_tasks() mock httpx → 정상 payload parse |
| Unit | 〃 | `test_list_tasks_raises_on_401` | TodoistAuthError raise |
| Unit | 〃 | `test_aenter_aexit_closes_http` | `async with TodoistClient(...)` 종료 시 httpx aclose 호출 |
| Integration | `tests/test_todoist_client.py` | `test_backoff_on_429` | 429 → exponential backoff + retry (실 retry timing) |
| Integration | `tests/test_oauth_todoist.py` | `test_callback_persists_three_key_dict` | OAuth callback → `existing["todoist"] == {access_token, refresh_token: None, scope: "data:read_write"}` (MA-1 contract) |
| Integration | 〃 | `test_sync_endpoint_returns_422_without_token` | `/api/todoist/sync` 호출 시 `external_tokens["todoist"]` 부재 → 422 |
| Integration | `tests/test_todoist_sync.py` | `test_sync_upserts_new_tasks` | mock client + DB → 새 source="todoist" task 생성 |
| Integration | 〃 | `test_sync_updates_existing_tasks` | 재sync 시 기존 source="todoist" task 갱신 (idempotent) |
| Integration | 〃 | `test_sync_tombstones_deleted_tasks` | upstream DELETE → local status="deferred" + synced_at 갱신, 다른 필드 immutable |
| Integration | 〃 | `test_sync_does_not_touch_local_tasks` | source="local" task 영향 없음 |
| Integration | 〃 | `test_push_failure_sets_sync_state_pending` | TodoistClient mock 실패 → `task.sync_state == "pending"` + `retry_count == 1` |
| Integration | `tests/test_todo_agent_todoist.py` | `test_add_task_pushes_to_todoist` | TodoAgent.add_task → local insert + Todoist POST + external_id 채워짐 |
| Integration | 〃 | `test_complete_task_on_todoist_source_closes_remote` | source="todoist" complete → Todoist `/tasks/{id}/close` POST + local update |
| Integration | 〃 | `test_sync_tool_invokes_endpoint` | TodoAgent.handle_tool("sync_todoist") → `/api/todoist/sync` 호출 |
| E2E (수동) | runbook | 4-step e2e | chat add → Todoist UI / Todoist add → /sync → local / Todoist delete → /sync → deferred / 완료 양방향 |
| Observability | (runtime) | log line on every sync | `logger.info("todoist.sync", extra={synced, pushed, tombstoned, errors, duration_ms})` 5 keys |

**총 신규 test cases: 14 (unit 3 + integration 11)** + E2E manual + observability log assertion.

---

## 4. Implementation Plan

### A. Migration `backend/alembic/versions/0007_tasks_external_id_sync_state.py`

`todo.tasks` 테이블에 5 컬럼 추가:
- `source: String(16), default "local"`
- `external_id: String(255), nullable`
- `synced_at: DateTime(timezone=True), nullable`
- `sync_state: String(16), nullable` (NULL | "pending" | "failed")
- `retry_count: Integer, default 0`

+ `UniqueConstraint("source", "external_id", name="uq_tasks_source_external")` (schedule.events:38 미러)
+ Index `ix_todo_tasks_sync_state` on `sync_state` (펜딩 task 빠른 조회)

`down_revision = "0006"`.

### B. `backend/app/db/models/todo.py` Task 모델 갱신

5 컬럼 추가 (위 migration과 동기). 기존 컬럼 무변동.

### C. `backend/app/services/todoist.py` 신규

```python
TODOIST_API_BASE = "https://api.todoist.com/rest/v2"

class TodoistAuthError(Exception):
    """Raised on 401 from Todoist API. Caller clears token + surface re-auth."""

class TodoistClient:
    def __init__(self, access_token: str, *, http: httpx.AsyncClient | None = None):
        self.access_token = access_token
        self._http = http or httpx.AsyncClient(timeout=15)
        self._owns_http = http is None

    async def __aenter__(self): return self
    async def __aexit__(self, *exc):
        if self._owns_http: await self._http.aclose()

    async def list_tasks(self, *, project_id: str | None = None) -> list[dict]: ...
    async def post_task(self, *, content: str, project_id: str, due_string: str | None = None) -> dict: ...
    async def close_task(self, task_id: str) -> None: ...  # POST /tasks/{id}/close
    async def list_projects(self) -> list[dict]: ...
```

httpx 호출 시 401 → `TodoistAuthError`, 429 → exponential backoff + retry (max 3, base 1s).

### D. `backend/app/services/todoist_sync.py` 신규

```python
async def sync_user_todoist(
    session, *, user, client: TodoistClient,
) -> dict[str, int | list[UUID]]:
    """Pull Todoist tasks → upsert local; tombstone missing.
    Returns {synced, pushed, tombstoned, errors, pending_task_ids}.
    Service commits (schedule precedent)."""

async def upsert_todoist_task(session, *, user_id, external_id, ...): ...  # service commits
async def tombstone_missing_todoist_tasks(session, *, user_id, server_external_ids): ...  # service commits

async def push_local_task(
    session, client, *, task: Task,
) -> str | None:
    """POST local task → Todoist. Returns external_id on success, None on failure
    (sync_state='pending', retry_count++). Flush only (caller commits)."""

async def _fetch_default_project_id(client: TodoistClient) -> str:
    """Find default project (Inbox) for push when local project_id is invalid/archived."""
```

### E. `backend/app/services/oauth_todoist.py` 신규

`oauth_google.py` 패턴 미러:
- `SCOPES = "data:read_write"` (Todoist v2 OAuth)
- `TODOIST_AUTH_URL = "https://todoist.com/oauth/authorize"`
- `TODOIST_TOKEN_URL = "https://todoist.com/oauth/access_token"`
- `TodoistOAuthService` 클래스 with `build_auth_url(user_id) -> str` + `handle_callback(session, code, state) -> OAuthCallbackResult`
- callback 저장: `existing["todoist"] = {"access_token": token, "refresh_token": None, "scope": scope}` (3-key shape MA-1 strict)
- service.commit() 내부 (oauth_google 패턴)

### F. `backend/app/api/oauth.py` 확장

`/oauth/todoist/start` (302 redirect) + `/oauth/todoist/callback` (`oauth_google` 패턴 미러).

### G. `backend/app/api/todoist.py` 신규

```python
@router.post("/sync", response_model=TodoistSyncResponse)
async def sync_todoist(
    user_id: UUID, db: AsyncSession = Depends(get_session),
) -> TodoistSyncResponse:
    user = await db.get(User, user_id)
    token = user.external_tokens.get("todoist", {}).get("access_token")
    if not token:
        raise HTTPException(422, "Todoist token not configured. Re-authenticate at /oauth/todoist/start")
    async with TodoistClient(token) as client:
        try:
            result = await sync_user_todoist(db, user=user, client=client)
        except TodoistAuthError:
            user.external_tokens["todoist"] = None
            await db.commit()
            raise HTTPException(422, "Todoist token revoked. Re-authenticate.")
    return TodoistSyncResponse(**result)
```

`TodoistSyncResponse` schema: `{synced: int, pushed: int, tombstoned: int, errors: int, pending_task_ids: list[UUID]}`.

### H. `backend/app/core/config.py` 갱신

```python
todoist_client_id: str | None = None
todoist_client_secret: str | None = None
todoist_redirect_uri: str = "http://localhost:8000/oauth/todoist/callback"
```

### I. `backend/app/agents/todo_agent.py` 갱신

**5번째 tool 추가**: `todo.sync_todoist`
- description: "Pull tasks from Todoist + push pending local tasks. Returns sync result counts."
- input_schema: `{}` (parameters 없음 — user 자동)
- `handle_tool` intent "sync_todoist" → `POST /api/todoist/sync` (internal call) OR 직접 `sync_user_todoist` 호출

**`add_task` push 추가** (write-through):
- local create 후 `_fetch_todoist_token(user)` 으로 token 조회
- 있으면 `async with TodoistClient(token):` → `push_local_task(session, client, task=task)`
- 실패 시 task에 `sync_state="pending"` (push_local_task 내부에서 처리)
- 없으면 push skip (token 없이도 local 동작 유지)

**`complete_task` push 추가**:
- `svc.get_task(task_id)` (no commit, flush only) → check `task.source`
- source == "todoist" + token 존재 → `async with TodoistClient(token):` → `client.close_task(task.external_id)`
- 실패 → `task.sync_state = "pending"` (다음 sync에서 close 재시도)
- `svc.complete_task(task_id)` (local update, flush only)

**`set_priority` push 추가**: 동일 패턴 (source="todoist" + token → Todoist `update` API). Todoist priority 매핑 표 별도.

**`_serialize_task`** 갱신: `sync_state` 필드 포함 (Risk #2 surfacing).

### J. TodoService 무변동 (legacy flush 패턴 유지)

`backend/app/services/todo.py`는 그대로. `list_tasks` 반환 객체에 신규 `sync_state` 컬럼이 자동 포함됨 (SQLAlchemy ORM).

---

## 5. Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| a | `alembic upgrade head` exit 0 + 5 컬럼 (source, external_id, synced_at, sync_state, retry_count) + UniqueConstraint("source","external_id") + index ix_todo_tasks_sync_state | DB 검사 |
| b | `pytest backend/tests/ -q` 그린: 기존 회귀 0 + 신규 ≥13 enumerated tests (위 §3) | pytest exit 0 |
| c | E2E manual (4-step): chat에서 add → Todoist UI 노출 / Todoist add → /sync → local 노출 / Todoist delete → /sync → status="deferred" / 완료 (local + remote 양방향) | runbook + commit message 기록 (§6) |
| d | observability log: 매 sync마다 `todoist.sync` 1줄 with 5 keys `{synced, pushed, tombstoned, errors, duration_ms}` | dev stdout |
| e | dev deps 무변동 (httpx 이미 설치) | `git diff main backend/pyproject.toml` 빈 결과 |
| f | E2E runbook §6 spec에 명시 | spec 확인 |
| g | MA-1 token shape 3-key 유지 (`{access_token, refresh_token: None, scope}`) | `test_callback_persists_three_key_dict` 그린 |
| h | Risk #2 surfacing: `sync_state` 가 `_serialize_task` 반환 + `pending_task_ids` 가 `/sync` 응답에 포함 | `test_sync_endpoint_returns_pending_ids` 그린 (test_todoist_sync.py에 추가) |

---

## 6. E2E Runbook (수동)

**선결 조건**:
1. `backend/scripts/seed_dev.py` 실행으로 fixture user `00000000-0000-0000-0000-000000000001` 존재 확인
2. Todoist Developer console (developer.todoist.com) → Create App → Test → OAuth Client ID + Secret 발급
3. `.env`에 `TODOIST_CLIENT_ID`, `TODOIST_CLIENT_SECRET`, `TODOIST_REDIRECT_URI=http://localhost:8000/oauth/todoist/callback` 설정

**E2E 4-step**:
1. **Browser**: `http://localhost:8000/oauth/todoist/start?user_id=<UUID>` → Todoist 인증 동의 → `/oauth/todoist/callback` → `external_tokens["todoist"]` 저장 확인 (DB query)
2. **Chat add → Todoist UI 노출**: home_agent UI 또는 curl로 `POST /api/chat/todo` → message "장보기 task 추가" → TodoAgent.add_task 호출 + Todoist push → Todoist 웹/앱 UI에서 task 확인
3. **Todoist add → /sync → local**: Todoist 웹 UI 에서 "보고서 작성" task 추가 → `curl -X POST http://localhost:8000/api/todoist/sync?user_id=<UUID>` → 응답 `{synced: 1+, ...}` → DB `select * from todo.tasks where source='todoist'` 확인
4. **Todoist delete → /sync → deferred**: Todoist 웹 UI 에서 위 "보고서 작성" task 삭제 → `/sync` → 응답 `{tombstoned: 1, ...}` → DB 해당 task `status='deferred'` 확인
5. **완료 양방향**: home_agent UI 에서 source="todoist" task complete → Todoist 웹/앱에서 task closed 상태 확인 + local `status='done'`

console error 0, 각 step 결과 commit message 또는 PR 본문에 기록.

---

## 7. Out of Scope (Phase 5)

- **Conflict resolution machinery** (last-write-wins 외) — 본 phase는 last-write-wins by call order만. 의외 conflict 발생 시 Phase 5.5+ 별도 spec
- **Project 다중 매핑** — 단일 default project (Todoist Inbox)만. UI mapping 별도 phase
- **Webhook trigger** — HTTPS 인프라 부재. on-demand `/sync` endpoint + TodoAgent tool만
- **Frontend UI for sync** — TodoAgent.sync_todoist tool 통해 chat에서 호출. 별도 button UI는 Phase 4.6+ 또는 UX phase
- **다른 외부 backend** (Notion, Apple Reminders) — 본 phase scope 외
- **sync_state="failed" 자동 재활성화** (failed → pending 자동 전환) — 본 phase에서는 manual DB reset만 지원. 자동화는 별도 spec
- **source="todoist" task의 priority 매핑** (Todoist 1-4 ↔ home_agent 1-5) — `set_priority` push 시 별도 매핑 표 필요. 본 phase에서는 직접 1:1 대응 (1↔1, 2↔2, 3↔3, 4↔4, 5→Todoist 4)

---

## 8. Open Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Todoist API rate-limit (450 req / 15min) | 위 S1: exponential backoff + idempotent upsert |
| 2 | 사용자가 Todoist token 갱신 안 함 (S3) | TodoistAuthError → 422 + agent surface 메시지 |
| 3 | Push 실패 누적 (sync_state="failed") | retry_count cap 5, manual DB reset 필요 — 자동 재활성화는 별도 spec |
| 4 | E2E 수동 실행 cost (~10분/회) | runbook §6 명시. 추후 CI 자동화는 별도 spec (Todoist sandbox mocking 필요) |
| 5 | Todoist priority 매핑 5→4 lossy | `set_priority`에서 5 → Todoist 4 매핑 (lowest), 1-4는 1:1. 사용자가 5를 자주 사용하지 않는 환경 가정 |
| 6 | Mixed commit semantics 혼동 (TodoService flush vs todoist_sync commit vs push_local_task flush) | ADR Consequences (§9) 명시. **Call order**: ChatService.run_domain → TodoAgent.handle_tool ("add_task") → svc.create_task (flush) → push_local_task (flush) → ChatService.persist_turn → db.commit (router) |

---

## 9. ADR

### Decision
Option C-lite (write-through asymmetric sync). Local create/edit → Todoist push (동기). Todoist → local pull (on-demand `/sync` + agent tool). Tombstone soft-delete. Mixed commit semantics with explicit boundary.

### Drivers
- 메타-로드맵 acceptance "양방향 sync" strict 충족 (deviation 0)
- Architect synthesis: spec primacy + CLAUDE.md §1 push back + §4 verifiable goals
- 1인 환경 minimum (single project, on-demand trigger, retry cap 5)

### Alternatives considered
- **A. One-way pull** (v1) — acceptance "양방향" 직접 위반. Architect NOT-approved. **폐기**
- **B. Full bidirectional + conflict ML** — speculative ML, CLAUDE.md §2 위반

### Why chosen
Architect Option C-lite synthesis 그대로 적용. 메타-로드맵 mandate strict 충족 + spec primacy + 실제 양방향 capability + conflict resolution 회피.

### Consequences

- **~350 LOC 추가** (services 3 신규 + api/oauth 확장 + agent tool 1건 + 5 컬럼 migration + 14 tests)
- **Mixed commit semantics**:
  - `TodoService` (legacy todo.py): flush only — router commits (ChatService 패턴)
  - `todoist_sync.py::sync_user_todoist`, `upsert_todoist_task`, `tombstone_missing_todoist_tasks`: service commits (schedule_service precedent)
  - `todoist_sync.py::push_local_task`: flush only — caller (TodoAgent → ChatService.persist_turn → db.commit) 가 commit
  - **Call order locked**: ChatService.run_domain → TodoAgent.handle_tool ("add_task") → TodoService.create_task (flush) → push_local_task (flush, external_id 채움 또는 sync_state="pending") → ChatService.persist_turn (flush) → db.commit (router 단일 commit)
- **Tombstone soft-delete**: `status="deferred"` + `synced_at=now`. 다른 필드 immutable (re-pull도 deferred row 갱신 안 함)
- **MA-1 strict 3-key**: `existing["todoist"] = {access_token, refresh_token: None, scope}`. Todoist OAuth는 refresh_token 미발급 → None 저장으로 schema 무변동
- **retry_count max 5 → sync_state="failed"** 후 자동 재시도 안 함. Manual DB reset 필요 (자동화는 별도 spec)
- **MA-4 트리거 없음** — 메타-로드맵 wording 후처리 commit 불필요

### Follow-ups
- 본 plan approve 시: Step 1 (migration + Python implementations + tests) → Step 2 (E2E manual runbook 실행) → 별도 commit 없음 (MA-4 트리거 없음)
- **Phase 5.5 후보** (실 사용 후 판단):
  - sync_state="failed" → "pending" 자동 재활성화 (현재는 manual DB reset)
  - Todoist webhook (HTTPS 인프라 확보 후)
  - Project 다중 매핑 (default → 사용자 매핑 UI)
  - Priority 매핑 표 (Todoist 1-4 ↔ home_agent 1-5) refinement

---

## 10. Meta-Roadmap 정합

| 메타-로드맵 §Phase 5 항목 | v3 충족 여부 |
|---|---|
| `services/todoist.py` 신규 | ✓ §C |
| `services/todoist_sync.py` 신규 | ✓ §D |
| Todoist OAuth callback | ✓ §E + §F |
| todo 에이전트 tool이 Todoist API 호출 | ✓ §I (add_task/complete_task/set_priority push + 신규 sync_todoist tool) |
| alembic migration (tasks + source/external_id + UniqueConstraint) | ✓ §A (5 컬럼) |
| Acceptance e2e 4-step "양방향 sync" | ✓ §6 runbook |
| 기존 todo 라우터 contract 무변동 | ✓ `TodoService` 무변동, schema/todo.py 출력 dict에 `sync_state` 자동 추가 (in-place evolution) |
| secret 저장 (MA-1 JSON dict) | ✓ §E (`existing["todoist"]` 3-key strict) |
| Open Risks: project 매핑 (in-phase 결정) | ✓ §7 OOS — single default project (Inbox fallback for archived) |
| Open Risks: conflict resolution (in-phase 결정) | ✓ §1 Principle 2 — last-write-wins by call order, no ML |
| Open Risks: webhook vs polling (in-phase 결정) | ✓ §1 Principle (on-demand `/sync` endpoint + agent tool) |
| Risk #2 surfacing (sync_state 명시) | ✓ §I `_serialize_task` + `pending_task_ids` in `/sync` response |
| MA-1 strict | ✓ 3-key (access_token, refresh_token: None, scope) |
| MA-2 strict | ✓ source/external_id/UniqueConstraint(schedule.events 미러) |

**MA-4 트리거 없음** — deviation 0. 메타-로드맵 wording 후처리 commit 불필요. (Phase 1, Phase 4와 달리 strict 충족)

---

## 11. Verification References

본 spec 사실 주장 검증 (Architect/Critic verification log):

- `backend/app/services/oauth_google.py:13` — `SCOPES = "https://www.googleapis.com/auth/calendar.readonly"` 패턴 (Todoist `"data:read_write"` 미러)
- `backend/app/services/oauth_google.py:64-84` — `handle_callback` flow + `existing["google"] = {refresh_token, scope}` JSON dict 저장 (MA-1 precedent — Todoist는 3-key with `refresh_token: None`)
- `backend/app/services/oauth_google.py:82` — service.commit() 내부 (`oauth_todoist.py` 미러)
- `backend/app/services/google_calendar.py:11-72` — client + `exchange_refresh_token` 패턴
- `backend/app/services/calendar_sync.py:16-47` — one-way pull precedent (Todoist는 추가 push path 필요)
- `backend/app/services/schedule_service.py:50-84` — `upsert_google_event` + service.commit() 패턴 (`upsert_todoist_task` 미러)
- `backend/app/services/todo.py:31,49,75,124,157` — `TodoService` flush only (legacy 유지)
- `backend/app/api/todo.py:48,68-69,86,107,142,179,194,209` — router commits + `NotFoundError → HTTPException(404)` translation
- `backend/app/api/oauth.py:14-30` — OAuth router pattern (todoist endpoints 미러)
- `backend/app/db/models/todo.py:43-75` — Task model 현재 (source/external_id/synced_at/sync_state/retry_count 부재 — §A migration 대상)
- `backend/app/db/models/schedule.py:14,25-26` — UniqueConstraint("source","external_id") precedent (MA-2)
- `backend/alembic/versions/0003_schedule_events_and_external_tokens.py:24-46` — 0003 migration 패턴 미러 (0007 미러)
- `backend/alembic/versions/0006_files_attachments.py` — 마지막 revision (0007 next 확인)
- `backend/app/agents/todo_agent.py:13-141` — 현재 4 tools + `_serialize_task` (5번째 tool `sync_todoist` 추가 + sync_state 필드 추가)
- `backend/app/core/config.py:51-54` — Google OAuth env var 패턴 (Todoist 미러)

---

## 12. Status & Next Action

- **Status**: pending approval (Critic APPROVED v3 at iteration 2/5, deliberate mode)
- **Next action** (approve 시):
  1. Step 1 (atomic implementation PR) — `feat(todo): Todoist write-through sync (Phase 5)`
  2. Step 2 (수동 E2E runbook §6, ~10분)
  3. **Step 3 불필요** (MA-4 트리거 없음, 메타-로드맵 strict 충족)
- **Out of scope** (별도 spec/phase): conflict ML, webhook, multi-project, priority 5↔4 매핑 refinement, sync_state failed→pending 자동 재활성화
