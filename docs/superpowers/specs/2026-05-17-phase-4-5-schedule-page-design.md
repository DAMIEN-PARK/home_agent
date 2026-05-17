# Phase 4.5: Functional Schedule.tsx 도메인 챗 + `.domain-chat` border 포팅

**Status:** pending approval (RALPLAN-DR v2, Critic APPROVED at iteration 1/5)
**Date:** 2026-05-17
**Owner:** damien
**Parent roadmap:** `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` (§Phase 4.5)
**Scope:** `frontend/src/pages/Schedule.tsx` 신규 (functional domain chat) + `frontend/src/lib/api.ts`에 `postDomainChat` 추가 + `App.tsx` 라우트 + `Sidebar.tsx` NavLink + 신규 test 2건+. **MA-4 트리거 없음 — deviation 0**.

**Iteration history:**
- v1 (Path X minimum): Schedule.tsx = Calendar embed + disabled placeholder chat region + border 1개. Static, no backend wiring.
- Architect v1: 8 issues (2 HIGH, 3 MEDIUM, 3 LOW) + 4 principle violations. Steelman: minimum scope이 'first domain page' 표현과 부합 안 함, tautological grep acceptance, disabled UX anti-pattern. Synthesis: **Path A** (border-only in Calendar.tsx) 또는 **Path B** (functional chat wiring).
- v2: **Path B 채택** — postDomainChat backend wiring + thread state + Calendar embed 폐기 + icon 충돌 해소 + RTL DOM assertion. All 8 issues 해결.
- Critic v2: **APPROVE** at iteration 1 + 3 MINOR advisory (non-blocking).

---

## 1. RALPLAN-DR Summary

### Principles

1. **Functional chat as headline** — Schedule.tsx는 `/api/chat/schedule` backend (Phase 1 ChatService.run_domain) 실제 호출. 정적 placeholder 폐기. 라우트가 실제 capability 가짐 = "first domain page" 표현 정합.
2. **정보 아키텍처 분리** — `/calendar` = visual events grid (Calendar.tsx 그대로 유지), `/schedule` = domain-scoped chat only. Calendar embed 폐기 → duplication 회피 (CLAUDE.md §2).
3. **mockup vision tree / timeline rail 영구 deferred** — fake static data를 React로 옮기는 의미 없음. Phase 4.5 scope 외.
4. **RTL-based acceptance** — `border-l-4 border-domain-schedule` 단순 grep 대신 DOM 셀렉터 + 의미 결합 assertion. tautology 회피.
5. **Sidebar 아이콘 충돌 회피** — `◆ 일정` for `/schedule`, `▣ 캘린더` 유지.

### Decision Drivers

1. 메타-로드맵 §Phase 4 acceptance (d) `border-l-4 border-domain-` in domain page — Path B는 functional UI의 자연스러운 일부로 충족
2. Backend `POST /chat/{domain}` 첫 frontend 소비처 확보 (otherwise unreachable from UI)
3. CLAUDE.md §2 + §4 — minimum scope + verifiable capability goal

### Viable Options

| Option | 설명 | Pros | Cons |
|---|---|---|---|
| **B. Functional Schedule.tsx** (Architect synthesis, **Recommended**) | postDomainChat + thread state + 도메인 챗 border | 라우트가 실제 capability, /chat/schedule 첫 소비처, UX 정직, ~80 LOC | thread 영속성 부재 (in-memory, Phase 4.6+) |
| **A. Border-only in Calendar.tsx** | Schedule.tsx 폐기, Calendar.tsx에 chat section 추가 | ~30 LOC, no route churn | 메타-로드맵 §Phase 4.5 mandate (Schedule.tsx 신규 + route)와 deviation → MA-4 또 트리거 |
| **X. Minimum static (v1)** | disabled UI + Calendar embed | acceptance grep만 충족 | UX anti-pattern, tautological, dual-mount, icon 충돌 — **Invalidated** |

→ **Option B 채택**. 메타-로드맵 §Phase 4.5 mandate 그대로 따름. MA-4 트리거 없음.

---

## 2. Implementation

### A. `frontend/src/lib/api.ts` — `postDomainChat` 추가

기존 `postChat`(orchestrator) 패턴 미러:

```ts
export async function postDomainChat(
  domain: string,
  message: string,
  userId: string,
): Promise<ChatResponse> {
  const r = await fetch(`/api/chat/${domain}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...deviceHeaders() },
    body: JSON.stringify({ message, user_id: userId }),
  });
  if (!r.ok) throw new Error(`domain chat failed: ${r.status}`);
  return r.json() as Promise<ChatResponse>;
}
```

### B. `frontend/src/pages/Schedule.tsx` 신규

```tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { postDomainChat } from "@/lib/api";

interface Turn {
  who: "user" | "assistant";
  text: string;
}

const TEMP_USER_ID =
  import.meta.env.VITE_USER_ID ?? "00000000-0000-0000-0000-000000000001";

export default function Schedule() {
  const [thread, setThread] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const send = useMutation({
    mutationFn: (msg: string) => postDomainChat("schedule", msg, TEMP_USER_ID),
    onSuccess: (data) =>
      setThread((t) => [...t, { who: "assistant", text: data.assistant_message }]),
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim()) return;
    setThread((t) => [...t, { who: "user", text: draft }]);
    send.mutate(draft);
    setDraft("");
  };

  return (
    <div className="p-6">
      <h1 className="text-xl mb-4 text-domain-schedule">일정 도메인 챗</h1>
      <section className="border-l-4 border-domain-schedule bg-white p-4 rounded">
        <div className="mb-3">
          <span className="inline-block px-2 py-0.5 text-xs rounded bg-domain-schedule-soft text-domain-schedule">
            schedule_agent
          </span>
          <span className="ml-2 text-sm">도메인 챗</span>
          <p className="text-xs text-stone-500 mt-1">
            scope: schedule.* · calendar MCP only
          </p>
        </div>
        <div className="space-y-2 mb-3 min-h-[120px]">
          {thread.map((t, i) => (
            <div
              key={i}
              className={t.who === "user" ? "text-indigo-600" : "text-stone-800"}
            >
              <span className="font-mono text-xs text-stone-400 mr-2">{t.who}</span>
              {t.text}
            </div>
          ))}
          {send.isPending && (
            <div className="text-stone-400 text-sm">생각 중…</div>
          )}
        </div>
        <form onSubmit={onSubmit} className="flex gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="이 도메인에만 묻기 — 일정·비전·목표"
            className="flex-1 border rounded px-3 py-2 text-sm"
            rows={2}
          />
          <button
            type="submit"
            className="px-4 bg-domain-schedule text-white rounded text-sm"
          >
            전송
          </button>
        </form>
      </section>
    </div>
  );
}
```

### C. `frontend/src/App.tsx` — `/schedule` 라우트 추가

```tsx
import Schedule from "@/pages/Schedule";
// inside <Routes>:
<Route path="/schedule" element={<Schedule />} />
```

기존 `/`, `/chat`, `/calendar` 유지.

### D. `frontend/src/components/Sidebar.tsx` — `/schedule` NavLink 추가

```tsx
<NavLink to="/schedule" className={navItemClass}>
  ◆ 일정
</NavLink>
```

기존 `▣ 캘린더` 유지 (다른 아이콘으로 시각 충돌 회피).

### E. `frontend/src/__tests__/Schedule.test.tsx` 신규

- RTL 셀렉터: `.border-l-4.border-domain-schedule` 컨테이너 + text `schedule_agent` + descendant `<textarea>` 동시 존재
- `bg-domain-schedule-soft` 셀렉터 존재 확인 (Tailwind compile smoke)
- mocked fetch: POST `/api/chat/schedule` 응답 `{ assistant_message: "ok", tool_calls: [] }` → 사용자 메시지 전송 후 응답 메시지 화면 표시

### F. `frontend/src/__tests__/Routing.test.tsx` — 보강

- `harness()` 함수의 `<Routes>` 블록에 `<Route path="/schedule" element={<Schedule />} />` 추가 (mocked fetch는 이미 `{ events: [] }` 응답하므로 기존 호환)
- 신규 test: NavLink `to="/schedule"` 클릭 → Schedule 페이지 콘텐츠 (text `schedule_agent`) 표시

---

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| a | **RTL DOM assertion**: `.border-l-4.border-domain-schedule` 컨테이너 + text `schedule_agent` + descendant `<textarea>` 동시 존재 | Schedule.test.tsx |
| b | `postDomainChat` in api.ts: `grep "export async function postDomainChat" frontend/src/lib/api.ts` ≥ 1 | 자동 |
| c | App.tsx `/schedule` 라우트: `grep "path=\"/schedule\"" frontend/src/App.tsx` ≥ 1 | 자동 |
| d | Sidebar `/schedule` NavLink with `◆ 일정`: `grep "◆ 일정" frontend/src/components/Sidebar.tsx` ≥ 1 | 자동 (Critic minor #3 반영) |
| e | 기존 test 4건 회귀 0 + 신규 test ≥ 2건 그린 | `cd frontend && npm run test` ≥ 6 pass |
| f | frontend build 통과 | `cd frontend && npm run build` exit 0 |
| g | 외부 의존성 무변동 | `git diff main frontend/package.json frontend/package-lock.json` 빈 결과 |
| h | **mid-verify**: Schedule × {desktop 1440, mobile 390} 스크린샷 + console error 0 + **실제 메시지 1건 전송 시 backend 응답 화면 표시** | 수동 (사용자 환경 dev 서버 + backend 띄운 후). **선결 조건**: `backend/scripts/seed_dev.py` (또는 동등) 실행으로 fixture user `00000000-0000-0000-0000-000000000001` 존재 확인 — Critic minor #1 반영 |

---

## 4. 실행 순서

**Step 1** — Atomic implementation PR (단일 commit)
- `frontend/src/lib/api.ts` — `postDomainChat` 추가
- `frontend/src/pages/Schedule.tsx` 신규
- `frontend/src/App.tsx` — `/schedule` 라우트 + import
- `frontend/src/components/Sidebar.tsx` — NavLink 추가
- `frontend/src/__tests__/Schedule.test.tsx` 신규
- `frontend/src/__tests__/Routing.test.tsx` — harness Routes 블록 + 신규 test case
- `cd frontend && npm run build && npm run test` 그린 확인
- Commit (예: `feat(frontend): Schedule.tsx functional domain chat + border port (Phase 4.5)`)
- main 머지

**Step 2** — Mid-gate verification (수동, 사용자 환경)
- 선결 조건: `backend/scripts/seed_dev.py` 실행으로 fixture user 존재
- `cd frontend && npm run dev` + `cd backend && uvicorn app.main:app --reload`
- Schedule × {desktop 1440, mobile 390} 스크린샷
- 실제 메시지 1건 전송 → backend 응답 화면 표시 확인
- console error 0 확인 (browse 도구 또는 Chrome DevTools)
- 결과 commit message 또는 별도 노트에 기록

**Step 3** — Meta-roadmap wording correction
- **불필요** — MA-4 트리거 없음 (메타-로드맵 §Phase 4.5 mandate strict 충족)

---

## 5. Out of Scope (Phase 4.5)

- **Vision tree** (mockup-only fake data) — 영구 deferred
- **Timeline rail** (mockup-only fake data) — 영구 deferred
- **챗 thread 영속성** (DB persistence는 backend ChatService.persist_turn에서 이미 처리; frontend 측 history 재로드) — Phase 4.6+
- **도메인 챗 suggestion chips** — Phase 4.6+
- **모바일 drawer toggle** — 별도 UX phase
- **`/calendar` 라우트 deprecation** — 사용 빈도 데이터 확보 후 별도 spec
- **5개 도메인 페이지** (todo/ledger/finance/ideas/files) — 별도 phase
- **registry.py:18-20 backend bug** (Critic 발견): `LedgerAgent`, `FinanceAgent`, `IdeasAgent`가 instance 아닌 class로 등록됨. Schedule.tsx와 무관 (schedule은 정상 instance). **별도 spec/issue 필요** — 본 Phase 4.5 scope 외, follow-ups 섹션 참조

---

## 6. Open Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | backend `POST /chat/schedule`가 1인 사용자 데이터로 의미 있는 응답 안 함 | Phase 1 ralplan에서 ChatService unit test 그린 확인됨. mid-verify에서 실제 응답 확인 |
| 2 | 첫 메시지 전송 시 fixture user_id (00000000-...001) 미존재 → backend 404 | **선결 조건 명시**: mid-verify 전 `backend/scripts/seed_dev.py` 실행 확인. Critic minor #1 반영 |
| 3 | thread state in-memory — 페이지 새로고침 시 사라짐 | 의도된 deferred (Phase 4.6+ history 재로드) |
| 4 | domain-chat visual이 mockup과 정확 일치 안 함 — Tailwind utility만 사용, mockup dc-thread/dc-input/dc-suggests 디테일 매핑 안 함 | 시각적 정합 거부 시 mid-verify에서 fix. 본 phase scope = border port + functional wiring 중심 |
| 5 | `◆ 일정` 아이콘 의미 약함 | mid-verify에서 사용자 시각 확인. 거부 시 `⊞`/`▦` 등 대체 검토 |

---

## 7. ADR

### Decision
Functional Schedule.tsx (postDomainChat + thread state) + `/schedule` route + Sidebar `◆ 일정` NavLink + 신규 test 2건+. Calendar embed 폐기, vision tree/timeline rail/suggestion 영구 deferred.

### Drivers
- 메타-로드맵 §Phase 4.5 mandate 정합 (Schedule.tsx + route + NavLink)
- `/chat/schedule` backend 첫 frontend 소비처 확보
- CLAUDE.md §2 (Calendar embed 폐기 — single-consumer duplication 회피) + §4 (verifiable capability goal)
- Architect Path B synthesis

### Alternatives considered
- **A. Border-only in Calendar.tsx**: ~30 LOC지만 메타-로드맵 §Phase 4.5 mandate와 deviation → MA-4 또 트리거. 거절.
- **X. Minimum static (v1)**: disabled UX anti-pattern + tautological acceptance + Calendar dual-mount + icon 충돌. **Invalidated**.

### Why chosen
메타-로드맵 mandate 그대로 + 실제 capability 추가 + UX 정직. v1의 8 Architect issues 모두 해소.

### Consequences
- `/calendar` + `/schedule` 정보 아키텍처 분리 (visual vs chat) — duplication 없음
- thread 영속성 없음 — Phase 4.6+ history 재로드
- mockup vision tree/timeline rail 영구 deferred — fake data React 이식 의미 없음
- `◆` icon 결정 — `▣` 충돌 회피, mid-verify 사용자 시각 확인 의존

### Follow-ups
- **Phase 4.6** (or named): thread 영속성 (history 재로드), suggestion chips, 5개 다른 도메인 페이지 (todo/ledger/finance/ideas/files)
- **별도 backend issue** (Critic 발견): `backend/app/agents/registry.py:18-20` — `LedgerAgent`, `FinanceAgent`, `IdeasAgent`가 instance 아닌 class로 등록됨. schedule/todo/files는 instance — 정상. 본 Phase 4.5 scope 외, **단순 수정 가능 (parens 추가)** — 별도 commit 권장

---

## 8. Meta-Roadmap 정합

본 v2는 메타-로드맵 `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` §Phase 4.5 mandate strict하게 따름:

- ✓ Schedule.tsx 신규 (frontend/src/pages/Schedule.tsx)
- ✓ 도메인 챗 영역에 `border-l-4 border-domain-schedule` 적용
- ✓ App.tsx 라우터 `/schedule` 추가, Sidebar.tsx NavLink 추가
- ✓ Schedule.tsx mid-verify scope (desktop + mobile, console error 0)
- ✓ 메타-로드맵 §Phase 4 acceptance (d) "border-l-4 border-domain- in Chat.tsx 도메인 인라인 챗 영역" 이관 충족

**MA-4 트리거 없음** — deviation 0. 메타-로드맵 wording 후처리 commit 불필요. (Phase 1/Phase 4와 달리 메타-로드맵과 정합)

---

## 9. Verification References

본 spec의 사실 주장은 다음 소스에서 확인됨 (Architect/Critic verification log):

- `backend/app/api/chat.py:32-52` — `POST /chat/{domain}` 라우터 + `UnknownDomainError → HTTPException(404)` (Phase 1 머지)
- `backend/app/services/chat_service.py` — `ChatService.run_domain` 구현 (Phase 1 머지)
- `backend/app/agents/registry.py:15-22` — `"schedule": ScheduleAgent()` instance 등록 (정상)
- `frontend/tailwind.config.ts:8-15` — `domain.schedule.{DEFAULT, soft}` → `domain-schedule` / `domain-schedule-soft` utility 자동 생성 (Phase 4 머지)
- `frontend/src/lib/api.ts:30-38` — `postChat` 패턴 (postDomainChat 미러 대상)
- `frontend/src/App.tsx:25-28` — 기존 2-route 구조 (`/chat`, `/calendar`)
- `frontend/src/components/Sidebar.tsx:13-15` — 기존 NavLink 패턴 + `▣ 캘린더` (icon 충돌 회피 대상)
- `frontend/src/pages/Chat.tsx` — useMutation + thread state 패턴 (Schedule.tsx 미러)
- `frontend/src/__tests__/Chat.test.tsx` — mock fetch + RTL pattern (Schedule.test.tsx 미러)
- `frontend/src/__tests__/Routing.test.tsx:22-25` — `<Routes>` 블록 (편집 대상)
- `planning/screens/_shared/style.css:440` — `.domain-chat.dom-schedule { border-left: 4px solid var(--domain-schedule); }` 캐논 (border port 대상)
- `planning/screens/schedule.html:133-168` — mockup domain-chat region 구조 (UI 참고)

---

## 10. Status & Next Action

- **Status**: pending approval (Critic APPROVED v2 at iteration 1/5)
- **Next action** (approve 시):
  1. Step 1 (atomic implementation PR) — `feat(frontend): Schedule.tsx functional domain chat + border port (Phase 4.5)`
  2. Step 2 (mid-verify — 사용자 환경에서 수동)
  3. **Step 3 불필요** (MA-4 트리거 없음)
- **Out of scope** (별도 spec/phase): Phase 4.6+ (thread 영속성, suggestion, 5개 도메인 페이지), `/calendar` deprecation, mobile drawer, registry.py backend bug
