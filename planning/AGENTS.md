# Agents — home_agent

오케스트레이터 1개 + 도메인 서브에이전트 N개. 각 에이전트는 **자기 도메인 스키마와 MCP 도구만** 접근한다.

---

## 설계 원칙

1. **단일 책임** — 각 서브에이전트는 한 도메인을 끝까지 책임. 도메인 경계가 흐려지면 신규 에이전트 분리 검토.
2. **도구는 MCP로** — 모든 데이터 조작은 도메인별 MCP 서버를 통해. 직접 SQL 호출 금지.
3. **데이터 격리** — Postgres `SCHEMA` 단위로 도메인 분리. 서브에이전트는 자기 스키마만 read/write.
4. **상태는 DB에** — 에이전트 인스턴스는 stateless. 모든 상태(대화·메모리·작업)는 `core.*` / `memory.*` 에 영속화.
5. **사용자 1명 가정 (MVP)** — 멀티유저는 별도 단계. 단, 데이터 모델에 `user_id` 컬럼은 처음부터 둔다.

---

## 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                    User (chat UI)                             │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              Orchestrator Agent                               │
│  - 의도 분류 (intent classification)                          │
│  - 서브에이전트 1개 또는 N개 호출 (병렬 가능)                 │
│  - 결과 통합 & 사용자에게 응답                                │
│  - 대화 컨텍스트 관리 (core.sessions, core.messages)          │
│  - 장기 메모리 추출/저장 (memory.entries)                     │
└────────┬────────┬────────┬────────┬────────┬────────┬────────┘
         ▼        ▼        ▼        ▼        ▼        ▼
     schedule  ledger  finance  ideas    files     todo
     agent    agent   agent    agent    agent     agent
         │        │        │        │        │        │
         ▼        ▼        ▼        ▼        ▼        ▼
     MCP      MCP     MCP      MCP      MCP       MCP
     calendar ledger  finance  notes    files     todo
         │        │        │        │        │        │
         └────────┴────────┴────────┴────────┴────────┘
                              │
                              ▼
                ┌────────────────────────────┐
                │  PostgreSQL (도메인 SCHEMA) │
                └────────────────────────────┘
```

---

## Orchestrator

**책임**
- 자연어 입력을 받아 의도(intent)를 분류한다 (예: "내일 일정 뭐였지?" → schedule).
- 단일 의도면 해당 서브에이전트 1개 호출, 복합 의도면 N개 병렬 호출 후 결과 통합.
- 대화 기록(`core.messages`)에 모든 turn 영속화.
- 매 턴 종료 시 장기 보존 가치가 있는 사실(선호·결정·관계)을 `memory.entries`에 추출 저장.
- 자기 자신은 도메인 데이터에 직접 접근하지 않는다 (도구 호출만).

**입력 / 출력**
- 입력: `{ session_id, user_message, attachments? }`
- 출력: `{ assistant_message, tool_calls[], updated_memory[] }`

**호출 가능 도구**
- 각 서브에이전트의 invoke 인터페이스 (`schedule.query`, `ledger.add_transaction`, …)
- `memory.write`, `memory.search`
- 직접적인 도메인 MCP 서버 호출 금지 (반드시 서브에이전트 경유)

---

## Subagents

각 서브에이전트는 동일한 형태의 인터페이스를 갖는다:

```
invoke(intent: str, params: dict, context: { user_id, session_id }) -> dict
```

내부적으로 자기 도메인 MCP 서버의 도구만 사용한다.

### 1. schedule_agent

**도메인**: 일정 · 비전 · 목표 (계획성 있는 시간 단위의 모든 것)
**스키마**: `schedule.*` — `events`, `goals`, `visions`, `recurrences`
**MCP 도구 (calendar)**:
- `list_events(from, to)`
- `create_event(title, start, end, …)`
- `update_event(id, …)` / `delete_event(id)`
- `link_event_to_goal(event_id, goal_id)`
- `list_goals(period)` / `create_goal(...)` / `link_goal_to_vision(...)`

**대표 의도**: "이번 주 일정", "내일 10시에 회의 추가", "올해 목표 진척도"

### 2. ledger_agent

**도메인**: 가계부 (일상 수입·지출)
**스키마**: `ledger.*` — `transactions`, `categories`, `budgets`, `accounts`
**MCP 도구 (ledger)**:
- `add_transaction(date, amount, category, account, memo)`
- `list_transactions(from, to, filter?)`
- `summarize_period(from, to, group_by)`
- `set_budget(category, amount, period)`
- `category_inference(memo)` — LLM 호출로 카테고리 자동 추정

**대표 의도**: "어제 점심 만원 썼어", "이번 달 식비 얼마 썼지?"

### 3. finance_agent

**도메인**: 자산·투자·순자산 (장기 재무 상태)
**스키마**: `finance.*` — `accounts`, `holdings`, `valuations`, `net_worth_snapshots`
**MCP 도구 (finance)**:
- `record_holding(account, symbol, quantity, cost_basis)`
- `update_valuation(holding_id, price, as_of)`
- `net_worth_snapshot(as_of)`
- `list_holdings(account?)`

**대표 의도**: "내 총 자산", "주식 평가액 갱신해줘"
**ledger와의 경계**: 거래 = ledger, 잔액·시가평가 = finance. 둘 다 필요한 경우 orchestrator가 양쪽 모두 호출.

### 4. ideas_agent

**도메인**: 아이디어 · 전략 · 노트
**스키마**: `ideas.*` — `notes`, `threads`, `tags`, `embeddings`
**MCP 도구 (notes)**:
- `add_note(title, content, tags?)`
- `search_notes(query)` — 키워드 + 벡터 검색
- `summarize_thread(thread_id)`
- `link_notes(a, b, relation)`
- `extract_action_items(note_id)` — todo_agent에 push할 후보 추출

**대표 의도**: "이 아이디어 정리해서 저장", "지난번에 메모한 사업 아이디어"

### 5. files_agent

**도메인**: 문서 · 사진 정리
**스키마**: `files.*` — `file_meta`, `photo_meta`, `embeddings`, `albums`
**MCP 도구 (files)**:
- `index_path(root_path)` — 파일 시스템 스캔, 메타 추출, 임베딩
- `search_files(query, type?)` — 텍스트/이미지 시맨틱 검색
- `tag_photo(photo_id, tags)`
- `find_duplicates(scope)`
- `organize_by_date(root, target)` — 사진 날짜별 폴더 재배치 제안

**대표 의도**: "작년 제주도 사진", "이 폴더 정리해줘"
**비고**: 실제 파일 이동은 사용자 확인 후 실행. 기본은 dry-run.

### 6. todo_agent

**도메인**: 업무 TODO (프로젝트·태스크)
**스키마**: `todo.*` — `tasks`, `projects`, `contexts`, `priorities`
**MCP 도구 (todo)**:
- `add_task(title, project?, due?, context?)`
- `list_tasks(filter?)` — by project / context / priority / due
- `complete_task(id)` / `defer_task(id, until)`
- `prioritize()` — 휴리스틱(due + importance) 기반 추천

**대표 의도**: "이거 할 일 추가", "오늘 할 일 보여줘"
**ideas_agent와의 경계**: 액션 아이템 = todo, 사고/메모 = ideas.

---

## 공유 영역

### core 스키마
- `users` — 사용자 (MVP에서는 1행)
- `sessions` — 대화 세션
- `messages` — 모든 user/assistant/tool 메시지
- `agent_runs` — 서브에이전트 호출 트레이스 (intent, params, result, duration)
- `audit_log` — 데이터 변경 이력

### memory 스키마
- `entries(id, user_id, kind, content, embedding vector, importance, created_at, last_used_at)`
  - `kind`: `preference` / `fact` / `relationship` / `routine`
- 오케스트레이터만 write, 모든 에이전트가 read.

---

## 통신 패턴

**의도 라우팅 — 1단계 LLM 분류**

오케스트레이터는 각 서브에이전트의 description을 모아 LLM에게 "어느 에이전트를 어떤 파라미터로 호출할지" 결정하게 한다 (Claude Agent SDK의 tool use). 복수 호출이 가능.

**병렬 vs 직렬**

| 케이스 | 패턴 |
|---|---|
| 독립적 의도 (일정 + 가계부 동시 조회) | 병렬 |
| 한 결과가 다음 입력 (메모 → todo 변환) | 직렬 |
| 사용자 확인 필요 (파일 이동) | 일시정지 → 사용자 응답 → 재개 |

**에러 처리**
- 서브에이전트 실패 시 orchestrator가 사용자에게 자연어로 설명. 자동 재시도 금지 (멱등성 보장 어려움).
- MCP 도구 호출 실패는 `agent_runs.error` 컬럼에 기록.

---

## 데이터 흐름 예시

> "어제 점심 만원 썼고, 오늘 저녁에 친구 만나기로 한 약속 추가해줘"

1. Orchestrator: 두 의도 감지 → `ledger_agent` + `schedule_agent` 병렬 호출
2. `ledger_agent.invoke("add_transaction", { date: 2026-05-15, amount: 10000, memo: "점심" })`
   - 내부: category_inference → "식비" 추정 → `ledger.transactions` INSERT
3. `schedule_agent.invoke("create_event", { title: "친구와 저녁", start: 2026-05-16T18:00, … })`
   - 내부: `schedule.events` INSERT
4. Orchestrator: 두 결과 통합 → "가계부에 식비 1만원 기록했고, 오늘 저녁 6시 약속 추가했어요."
5. Orchestrator: 장기 메모리 후보 추출 → 이번에는 없음.

---

## 확장 시나리오 (지금은 안 함)

- **health_agent** — 운동·수면·식단 추적 (`health.*` 스키마)
- **travel_agent** — 여행 계획 (schedule와의 경계 정의 필요)
- **family_agent** — 가족 공유 캘린더/지출 (멀티유저 도입 시)

새 에이전트 추가 기준: 기존 에이전트 도메인을 50% 이상 침해하지 않아야 분리.

---

## 미정 / 결정 필요

- [ ] 의도 분류: orchestrator를 LLM 1개로 vs 분류기 + 실행기 2단계로?
- [ ] 서브에이전트 모델: 모두 동일 모델 vs 작업 복잡도에 따라 차등 (sonnet/haiku)?
- [ ] 사용자 확인 UX: 인라인 확인 vs 별도 승인 큐?
- [ ] 백그라운드 작업 트리거: 사용자 발화만 vs 일정/리마인더로 자동 실행?
- [ ] 멀티유저 도입 시점 — 1인용으로 충분히 검증된 후 진행?
