# 오케스트레이터 ↔ 도메인 서브에이전트 모델

**작성일**: 2026-05-16
**작성자**: damien (with Claude)
**상태**: draft (사용자 검토 대기)
**관련 문서**: [`planning/AGENTS.md`](../../../planning/AGENTS.md), [`planning/screens/chat.html`](../../../planning/screens/chat.html), [`planning/screens/schedule.html`](../../../planning/screens/schedule.html), [`docs/superpowers/specs/2026-05-15-mvp-v0.1-design.md`](2026-05-15-mvp-v0.1-design.md)

---

## 1. 목표

mockup에 그려진 두 가지 챗 인터페이스를 백엔드에서 일관되게 받친다:

1. **오케스트레이터 챗** (`chat.html`) — 자연어 한 줄로 모든 도메인을 부른다. 결과는 도구 호출(`schedule.create_event`, `ledger.sum_by_category` …) trace로 보여준다.
2. **도메인 챗** (`*.html`의 `domain-chat` 블록) — 그 도메인에만 묻고, 그 도메인의 도구만 쓰는 thin chat.

비목표:
- 오케스트레이터가 도메인 챗을 또 다른 LLM으로 재호출하는 sub-agent loop는 **하지 않는다**. (비용/지연이 2배 이상)
- 도메인 ↔ 도메인 직접 호출도 **안 한다**. (관심사 분리는 오케스트레이터가 책임)
- 도메인 챗의 파일첨부 동작은 #8 별도 spec.

## 2. 결정 사항 (사용자 답)

| 항목 | 결정 |
|---|---|
| todo 도메인 v1 수준 | 로컬 DB만. Todoist OAuth는 후속 작업 |
| 세션 격리 | 도메인 챗은 독립 스코프 세션. 단, 오케스트레이터는 **각 도메인 챗의 최근 N개 메시지를 읽기 가능** (느슨한 분리) |
| API 라우팅 | `POST /chat/{domain}` · `{domain}` 생략하면 orchestrator |

## 3. 도메인 에이전트 추상

신규: `backend/app/agents/base.py`

```python
class DomainAgent(Protocol):
    name: str                    # "schedule" | "todo" | ...
    tools: list[dict]            # Claude tool schema, name prefixed ("schedule.create_event")
    model: str                   # "claude-sonnet-4-6" 등 (settings의 모델 라우팅에서 주입)

    async def handle_tool(
        self, session, *, user, intent: str, params: dict
    ) -> dict:
        """오케스트레이터가 LLM tool_call을 받았을 때 부른다. LLM 호출 없음."""

    async def run_turn(
        self, session, *, user, session_id, user_message, recent_messages: list[dict]
    ) -> dict:
        """도메인 챗 단독 호출. 자체 LLM 호출 + 자기 tools만 사용."""
```

레지스트리:
```python
# backend/app/agents/registry.py
REGISTRY: dict[str, DomainAgent] = {
    "schedule": ScheduleAgent(),
    "todo":     TodoAgent(),
    "ledger":   LedgerAgent(),   # stub
    "finance":  FinanceAgent(),  # stub
    "ideas":    IdeasAgent(),    # stub
    "files":    FilesAgent(),    # stub
}
```

## 4. 오케스트레이터 동작

```python
# backend/app/agents/orchestrator.py
async def run_turn(session, *, user, session_id, user_message, device_id, device_name):
    all_tools = [t for a in REGISTRY.values() for t in a.tools]
    messages = await build_messages_with_cross_domain_context(session, user, session_id, ...)

    llm_resp = await call_llm(messages, tools=all_tools, system=ORCH_PROMPT, model=settings.routing["orchestrator"])

    results = []
    for call in llm_resp.tool_calls:
        domain_name = call.name.split(".", 1)[0]   # "schedule.create_event" → "schedule"
        intent     = call.name.split(".", 1)[1]
        agent = REGISTRY[domain_name]
        res = await agent.handle_tool(session, user=user, intent=intent, params=call.arguments)
        results.append({"name": call.name, "result": res})

    return {"assistant_message": llm_resp.final_text, "tool_calls": results}
```

**Cross-domain context** (사용자 결정: 느슨한 분리):
- `build_messages_with_cross_domain_context`가 마지막 N개의 도메인 챗 turn을 system context로 inject (요약 또는 raw 메시지).
- 구체적 N: **각 도메인 마지막 3 turn (user/assistant pair)**, system prompt에 짧은 블록으로.
- 토큰 예산: 도메인 6개 × 3 turn ≈ 충분. 길어지면 후속 spec에서 요약 추가.

## 5. 도메인 챗 동작

```python
# backend/app/api/chat.py
@router.post("/chat/{domain}")
async def post_domain_chat(domain: str, req: ChatRequest, ...):
    if domain not in REGISTRY:
        raise HTTPException(404, f"unknown domain: {domain}")
    agent = REGISTRY[domain]
    session_id = await get_or_create_scoped_session(db, user, device_id, scope=domain)
    recent = await load_recent_messages(db, session_id, limit=10)
    return await agent.run_turn(db, user=user, session_id=session_id, user_message=req.message, recent_messages=recent)
```

도메인 agent의 `run_turn`은:
- 자기 `tools`만 LLM에 노출
- 자기 `model` 사용 (settings의 모델 라우팅)
- system prompt는 그 도메인 한정 (`"너는 schedule 전문 sub-agent다. ..."`)
- tool_call이 오면 자기 `handle_tool`로 처리

## 6. 데이터 모델 변경

`core.sessions`에 `scope` 컬럼 추가:

```python
class Session(Base, TimestampMixin):
    ...
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="orchestrator")
    # values: orchestrator | schedule | todo | ledger | finance | ideas | files
```

Migration `0005_session_scope.py`:
- ALTER TABLE core.sessions ADD COLUMN scope VARCHAR(32) NOT NULL DEFAULT 'orchestrator'
- 인덱스: `ix_core_sessions_device_scope (device_id, scope)`

**세션 라우팅 규칙** (서버):
- 도메인 챗: (user_id, device_id, scope=domain) 조합당 1개 활성 세션 자동 생성/재사용
- 오케스트레이터 챗: (user_id, device_id, scope='orchestrator') 1개

## 7. API 변화

| 메소드 | 경로 | 변경 |
|---|---|---|
| POST | `/chat` | 그대로 — 오케스트레이터 (scope=orchestrator) |
| POST | `/chat/{domain}` | **신규** — domain ∈ schedule/todo/ledger/finance/ideas/files |
| GET | `/chat/sessions?device_id=&scope=` | 후속(이번 spec 범위 외) |

요청/응답 body는 `/chat`와 동일 (`ChatRequest` / `ChatResponse`).

## 8. v1 구현 범위

| 도메인 | `tools` 정의 | `handle_tool` | `run_turn` | 비고 |
|---|---|---|---|---|
| schedule | ✅ 기존 유지 + 약간 보강 | ✅ 기존 | ✅ 신규 | LLM 호출 1회 |
| todo | ✅ 신규 (add/list/complete/prioritize) | ✅ 신규 — 로컬 DB CRUD | ✅ 신규 | Todoist 동기화 제외 |
| ledger | ✅ 스키마만 | ❌ 501 not implemented | ❌ 501 | UI는 떠도 백엔드 nop |
| finance | ✅ 스키마만 | ❌ 501 | ❌ 501 | 같음 |
| ideas | ✅ 스키마만 | ❌ 501 | ❌ 501 | 같음 |
| files | ✅ 스키마만 | ❌ 501 | ❌ 501 | 같음 |

stub 도메인도 `tools`는 진짜로 정의한다 — 오케스트레이터 LLM에 도구 목록 노출 가능. 호출되면 `{"ok": False, "error": "not implemented"}` 응답.

## 9. 모델 라우팅 (settings와 연동)

`Settings.agent_models: dict[str, str]` 추가:

```python
agent_models: dict[str, str] = Field(default_factory=lambda: {
    "orchestrator": "claude-sonnet-4-6",
    "schedule":     "claude-haiku-4-5",
    "todo":         "claude-sonnet-4-6",
    "ledger":       "claude-haiku-4-5",
    "finance":      "claude-opus-4-7",
    "ideas":        "claude-sonnet-4-6",
    "files":        "claude-sonnet-4-6",
})
```

(settings.html mockup의 값과 일치)

## 10. 테스트 전략

- **단위**: 각 도메인 agent의 `handle_tool` (현재 schedule_agent 테스트 패턴 따름) — 실제 DB.
- **단위**: `run_turn` (LLM mock + 도구 호출 검증).
- **통합**: 오케스트레이터가 cross-domain context를 inject하는지 (도메인 챗 → 오케 챗 순서로 호출).
- **마이그레이션**: alembic upgrade head + downgrade -1 왕복 (기존 패턴).

## 11. 미해결

- cross-domain context inject 방식이 "raw 최근 3 turn"이지만 도메인이 6개 다 차면 토큰 비용 부담 → 후속 spec에서 요약 layer 도입.
- agent_models가 코드 hardcode인 상태. settings 화면에서 편집한 값을 어디에 저장할지 (`.env`? DB?) — 별도 spec.
- 도메인 챗 파일첨부는 #8.

## 12. 구현 순서 (plan으로 갈 때 분해)

1. `core.sessions.scope` 마이그레이션 (0005)
2. `agents/base.py` + `agents/registry.py`
3. `schedule_agent.py` 리팩터 (Protocol 준수, `run_turn` 추가)
4. `todo_agent.py` 신규 (로컬 DB CRUD + `run_turn`)
5. 4개 stub agent (ledger/finance/ideas/files)
6. `orchestrator.py` 리라이트 (REGISTRY 사용 + cross-domain context)
7. `api/chat.py`에 `/chat/{domain}` 추가 + 세션 라우팅
8. `core/config.py`에 `agent_models` 추가
9. 단위/통합 테스트
