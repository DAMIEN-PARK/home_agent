# Phase 4: Tailwind theme.extend.colors + Calendar 2-consumer + Sidebar 모바일 hide

**Status:** pending approval (RALPLAN-DR v3, Critic APPROVED at iteration 2/5)
**Date:** 2026-05-17
**Owner:** damien
**Parent roadmap:** `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` (§Phase 4 — wording correction required post-merge; 본 spec §10 참조)
**Scope:** `frontend/tailwind.config.ts` populate + `frontend/src/pages/Calendar.tsx` 토큰 적용 + `frontend/src/components/Sidebar.tsx` 모바일 hide. Border port + drawer = Phase 4.5로 deferred.

**Iteration history:**
- v1: Honest scope (Option X) — Tailwind + Calendar + Chat 무변경 + (d)(drawer) deferred
- Architect v1: 7 issues (2 HIGH, 3 MEDIUM, 2 LOW) + 4 principle violations. Synthesis = "Option X+" (Sidebar +1 LOC, Calendar 2-consumer proof, Phase 4.5 named successor)
- v2: Architect synthesis 채택
- Critic v2: ITERATE — 5 issues (2 MAJOR: Sidebar before/after ambiguous + hash check broken; 3 MINOR)
- v3: 5 fixes 적용 (Sidebar 정확한 className, grep + manual diff, MA-4 (ii) tighten, Risk fallback enumerated, sequence note)
- Critic v3: **APPROVE**

---

## 1. RALPLAN-DR Summary

### Principles

1. **Tailwind SSOT** — `tailwind.config.ts theme.extend.colors`만 갱신. `index.css`/`tokens.css` 변경 없음 (현재 비어있어 매핑 대상 부재).
2. **Honest scope reduction + named successor** — 도메인 페이지 부재로 border port deferred하되 **Phase 4.5 (Schedule.tsx 첫 도메인 페이지)** 명시. 불특정 "future" 회피.
3. **2-consumer end-to-end proof** — Calendar.tsx에서 border + text utility 둘 다 사용해 토큰 system이 React에서 실제 작동함을 증명. Synthetic UI fabrication 금지.
4. **Mid-gate mobile sanity** — Sidebar.tsx `hidden md:flex`로 모바일 viewport screenshot이 의미 있도록. drawer 자체는 Phase 4.5+로 deferred.
5. **CLAUDE.md §3 Surgical** — Chat.tsx 변경 0줄 (orchestrator entry, 도메인 context 부재; indigo-600 = mockup `--accent #4f46e5` 정확 일치).

### Decision Drivers

1. mockup spec §7 토큰을 React에 1:1 이식 + 실제 소비처에서 검증
2. CLAUDE.md §2 — 도메인 페이지/drawer 같은 absent feature는 만들지 않음 (single-consumer/no-consumer abstraction 회피)
3. 메타-로드맵 deferred 항목에 named successor phase (Phase 4.5)로 핀고정 → drift 방지

### Viable Options

| Option | 설명 | Pros | Cons |
|---|---|---|---|
| **X+. Honest scope + 2-consumer + named successor** (Architect synthesis, **Recommended**) | Tailwind + Calendar 2 utility + Sidebar 1 LOC + Phase 4.5 핀고정 | 토큰 end-to-end 입증, mobile screenshot 의미 있음, scope drift 방지 | 메타-로드맵 deviation (Phase 1과 동일 패턴) |
| **Y. 메타-로드맵 strict** | 도메인 페이지 6개 stub + drawer 구현 + .domain-chat border 적용 | acceptance 100% 충족 | CLAUDE.md §2 위반, 스코프 폭발 |
| **Z. 토큰만 (tsx 무변경)** | tailwind.config.ts만 갱신 | 가장 안전 | 토큰 system 검증 0, mid-gate visual 빈 결과 |

→ **Option X+ 채택**. MA-4 clause (ii) 정합 (missing prerequisite state explicitly named in prior approved phase + verifiably absent).

---

## 2. Implementation

### A. `frontend/tailwind.config.ts` — `theme.extend.colors` 채택

mockup spec §7 lines 286-309 byte-equal. nested `{ DEFAULT, soft }` 형식. 13 토큰 쌍 (6 도메인 + 7 카테고리). 모든 aliases resolved to hex.

```ts
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        domain: {
          schedule: { DEFAULT: '#7c3aed', soft: '#f5f3ff' },
          todo:     { DEFAULT: '#0891b2', soft: '#ecfeff' },
          ledger:   { DEFAULT: '#16a34a', soft: '#ecfdf5' },
          finance:  { DEFAULT: '#854d0e', soft: '#fef3c7' },
          ideas:    { DEFAULT: '#a21caf', soft: '#fae8ff' },
          files:    { DEFAULT: '#475569', soft: '#f1f5f9' },
        },
        cat: {
          food:      { DEFAULT: '#9a3412', soft: '#ffedd5' },
          transport: { DEFAULT: '#0369a1', soft: '#e0f2fe' },
          living:    { DEFAULT: '#4d7c0f', soft: '#ecfccb' },
          leisure:   { DEFAULT: '#be185d', soft: '#fce7f3' },
          medical:   { DEFAULT: '#dc2626', soft: '#fef2f2' },
          fixed:     { DEFAULT: '#78716c', soft: '#f5f5f4' },
          misc:      { DEFAULT: '#a8a29e', soft: '#fafaf9' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
```

### B. `frontend/src/pages/Calendar.tsx` — 2-consumer 입증

- **border (local event)**: 현재 `border-indigo-500` → `border-domain-schedule`
- **text (월 헤더 `<h1>`)**: 현재 `text-xl mb-4` → `text-xl mb-4 text-domain-schedule`
- **google event border `border-emerald-500` 유지** (sync source 시각 구분 — sunset 2026-08-31)

변경 line 38: `<h1 className="text-xl mb-4 text-domain-schedule">`
변경 line 60 (ternary): `${e.source === "google" ? "border-emerald-500" : "border-domain-schedule"}`

### C. `frontend/src/pages/Chat.tsx` — 변경 0

- Orchestrator entry, 도메인 context 부재
- Tailwind `indigo-600` = mockup `--accent #4f46e5` 정확 일치 → 변경 무의미
- Hex 사용 0건 today (verified) — Phase 4 hex→utility 치환 작업이 Chat.tsx에 적용될 부분 없음

### D. `frontend/src/components/Sidebar.tsx` — 모바일 hide

**Before** (Sidebar.tsx:8):
```tsx
<aside className="w-60 h-screen border-r border-stone-200 bg-white p-4 flex flex-col gap-1 sticky top-0">
```

**After**:
```tsx
<aside className="hidden md:flex w-60 h-screen border-r border-stone-200 bg-white p-4 flex-col gap-1 sticky top-0">
```

- 변경: prepend `hidden md:flex`, remove bare `flex` (md:flex가 md+에서 re-add, mobile은 hidden). `flex-col gap-1` 유지.
- 모바일 (390px) screenshot이 main content 100% 차지하도록. drawer toggle은 Phase 4.5+ scope.

### E. Border port `.domain-chat.dom-*` — DEFERRED to Phase 4.5

- 메타-로드맵 §Phase 4 결과물의 "Chat.tsx 도메인 인라인 챗 영역 border 포팅" → 대상 컴포넌트 (도메인 페이지) 부재
- **Phase 4.5 명시 (신설)**: 첫 도메인 페이지 React 구현 (`frontend/src/pages/Schedule.tsx` 1개) — 본 페이지 내 도메인 챗 영역에 `border-l-4 border-domain-schedule` 적용이 그 phase의 acceptance gate
- Tailwind 토큰은 본 Phase 4에서 등록되어 있어 Phase 4.5에서 즉시 사용 가능

### F. Drawer — DEFERRED to Phase 4.5 (or 별도 UX phase)

- Sidebar.tsx → `hidden md:flex`로 모바일 hide만 (위 D)
- 모바일 햄버거 toggle + slide-in drawer = Phase 4.5+

---

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| a-1 | **automated grep** (구조 게이트): | |
| | `grep -cE "^\s+(schedule\|todo\|ledger\|finance\|ideas\|files):\s*\{" frontend/tailwind.config.ts` == 6 | 자동 |
| | `grep -cE "^\s+(food\|transport\|living\|leisure\|medical\|fixed\|misc):\s*\{" frontend/tailwind.config.ts` == 7 | 자동 |
| | `grep -c "DEFAULT:" frontend/tailwind.config.ts` ≥ 13 | 자동 |
| | `grep -c "soft:" frontend/tailwind.config.ts` ≥ 13 | 자동 |
| a-2 | **수동 byte-equal diff**: 검토자가 mockup spec `2026-05-17-mockup-color-tokens-mobile.md` §7 (lines 286-309) 와 `tailwind.config.ts`의 `theme.extend.colors` 블록을 양쪽 열어 hex 26개 정확 일치 확인 | 수동 (단독 byte-equal 게이트) |
| b | (a-1과 합쳐서 처리) | — |
| c | **utility 소비처 ≥2** (Calendar.tsx 단독, real consumers only — fabricated UI 금지): `grep -cE "(bg\|text\|border)-(domain\|cat)-" frontend/src/pages/Calendar.tsx` ≥ 2 | 자동 |
| d | ~~border-l-4 border-domain- in Chat.tsx ≥1~~ — **DEFERRED to Phase 4.5: First domain page (Schedule.tsx)** | 메타-로드맵 §Phase 4 (d) amendment + follow-up phase 신설 |
| e | Calendar.tsx border 토큰: `grep "border-domain-schedule" frontend/src/pages/Calendar.tsx` ≥ 1 | 자동 |
| f | Sidebar.tsx 모바일 hide: `grep "hidden md:flex" frontend/src/components/Sidebar.tsx` ≥ 1 | 자동 |
| g | **비주얼 (mid-gate)**: Chat 색 무변동 (indigo), Calendar local event 보라색 (schedule), Calendar 월 헤더 보라색, 모바일 sidebar 미표시, console 0 | 4 스크린샷 (desktop 1440 + mobile 390, Chat + Calendar). **drawer 동작 항목은 Phase 4.5로 이관** |
| h | frontend 빌드 통과 | `cd frontend && npm run build` exit 0 |
| i | 기존 frontend test 그린 | `cd frontend && npm run test` exit 0 |
| j | 외부 의존성 무변동 | `git diff main frontend/package.json frontend/package-lock.json` 빈 결과 |

---

## 4. 실행 순서

**Step 1** — Atomic implementation PR (단일 commit)
- `frontend/tailwind.config.ts` 갱신 (theme.extend.colors)
- `frontend/src/pages/Calendar.tsx` 갱신 (월 헤더 + local event border)
- `frontend/src/components/Sidebar.tsx` 갱신 (`hidden md:flex` + bare `flex` 제거)
- `cd frontend && npm run build && npm run test` 그린 확인
- Commit (예: `feat(frontend): port mockup color tokens to Tailwind + Calendar consumers (Phase 4)`)
- main 머지

**Step 2** — Mid-gate verification (mandatory)
- 4 스크린샷: Chat × {desktop 1440, mobile 390} + Calendar × {desktop 1440, mobile 390}
- console error 0 확인 (browse 도구 `console.errors()` OR Chrome DevTools 수동)
- 결과 commit message 또는 별도 검증 노트에 기록
- Fail 시 → Risk #2 fallback (Calendar 월 헤더 색 거부) 적용 후 재시도

**Step 3** — Meta-roadmap wording correction (단일 commit)
- `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` §Phase 4 결과물 정정 + Mid-gate drawer 항목 보정 + Phase 4.5 신설 + MA-4 추가
- Commit message 예: `docs(planning): correct §Phase 4 + add Phase 4.5 + MA-4 deviation protocol`

---

## 5. Open Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | 메타-로드맵 deviation 사용자 거부 | Phase 1에서 동일 패턴 승인됨 (MA-4 (ii) 정합) |
| 2 | Calendar.tsx 월 헤더 `text-domain-schedule` 시각적 변화 — mockup 명시 없음. 사용자 거부 가능 | **mid-gate 스크린샷에서 사용자 시각 확인 필수**. 거부 시 **fallback enumerated**: Calendar.tsx line 44 day-of-week header (`bg-stone-50 px-2 py-1 text-xs uppercase`)의 `bg-stone-50` → `bg-domain-schedule-soft`로 교체 → 2-consumer (border + bg) 유지하면서 보라색 영역 축소 |
| 3 | Phase 4.5 신설 — 메타-로드맵 phase 카운트 변동 | 사용자 명시 원안 시퀀스 1→4→5→2→3은 유지. 4.5는 4의 자연 연장 sub-phase로 표기 (5→2→3 시퀀스 의미 불변, phase 카운트만 +1) |
| 4 | `border-emerald-500` sunset 2026-08-31 — 미정리 시 source-marker taxonomy 누락 | Phase 5 (Todoist) 머지 후 source taxonomy 정리 spec 진입 필수. 본 phase ADR + Phase 5 ralplan 진입 시 reminder |
| 5 | `hidden md:flex` 적용 시 모바일에서 nav 접근 불가 | 1인 사용자 + 모바일은 chat-only 가정. drawer 부재 명시 → Phase 4.5+에서 해결. accepted, no mitigation |

---

## 6. Meta-Roadmap Reconciliation

메타-로드맵 (`docs/superpowers/specs/2026-05-17-execution-roadmap-design.md`) §Phase 4 결과물 + Mid-gate 일부가 본 v3 scope와 충돌. CLAUDE.md §2 + MA-4 clause (ii) 근거로 deviation. 후처리 commit (Step 3)으로 정정.

### 후처리 commit 내용

1. **§Phase 4 결과물 정정**:
   - "Chat.tsx의 도메인 인라인 챗 영역 border 포팅" → "**Phase 4.5 (Schedule.tsx 첫 도메인 페이지)** 신설 및 이관"
   - 이유: 도메인 페이지가 React에 부재하여 border 포팅 대상 컴포넌트 없음

2. **§Mid-gate 정정**:
   - "모바일 drawer 동작 정상" → "Sidebar 모바일 hide (`hidden md:flex`); drawer 자체는 **Phase 4.5+**"
   - 이유: Sidebar.tsx always-visible, drawer 미구현. 모바일 hide 1 LOC로 mid-gate screenshot 의미 확보

3. **신규 Phase 4.5 추가** (§Phase 4 직후):
   - 이름: First domain page (Schedule.tsx)
   - Entry: Phase 4 머지 + mid-verify pass
   - 결과물: `frontend/src/pages/Schedule.tsx` + 도메인 챗 영역 (`border-l-4 border-domain-schedule`) + 라우터 등록
   - Acceptance: (d) border port 그린, Schedule.tsx 1개 페이지 mid-verify pass

4. **시퀀스 보존 명시**:
   - "사용자 명시 원안 시퀀스 1→4→5→2→3은 유지. Phase 4.5는 4의 자연 연장 sub-phase (5→2→3 시퀀스 의미 불변, phase 카운트만 +1)"

5. **§6 Meta-ADR MA-4 추가** (일반 deviation protocol):

   **Decision**: Approved roadmap line items become advisory when subsequent verified state contradicts them; deviation requires (a) post-hoc amendment commit, (b) ADR entry naming the deviation + reason + successor phase.

   **Permitted only when**:
   - (i) deviation is forced by CLAUDE.md project rule (e.g., §2 abstraction violation, §3 surgical), OR
   - (ii) deviation is forced by missing prerequisite state **that was explicitly named in a prior approved phase and is verifiably absent in the codebase at the time of deviation** (e.g., `_chat_input.py` was absent in Phase 1, domain page React routes are absent in Phase 4)

   **Precedent commits**:
   - Phase 1: `60f6733 refactor(chat): extract ChatService + slim router (Phase 1)` + `74b31ad docs(planning): correct §Phase 1 — single ChatService`
   - Phase 4: (본 phase 머지 + 후처리 commit)

---

## 7. ADR

### Decision
Tailwind config (mockup spec §7 13 token pairs) + Calendar.tsx 2-consumer (border + 월 헤더 text) + Sidebar.tsx `hidden md:flex` 1 LOC. Border port + drawer = Phase 4.5로 deferred. 메타-로드맵 §Phase 4 wording 후처리 정정 + MA-4 (general deviation protocol) 신설.

### Drivers
- mockup spec §7 토큰 React 이식 + 실제 소비처에서 end-to-end 입증
- CLAUDE.md §2 — 도메인 페이지/drawer 같은 absent feature는 만들지 않음
- 메타-로드맵 deferred 항목 named successor (Phase 4.5)로 핀고정

### Alternatives considered
- **Y. 메타-로드맵 strict** — 도메인 페이지 6개 stub + drawer 구현 → CLAUDE.md §2 위반, 스코프 폭발
- **Z. 토큰만, tsx 무변경** — 토큰 system end-to-end 검증 0 + mid-gate visual 빈 결과

### Why chosen
Architect Option X+ synthesis 적용. 메타-로드맵 deviation은 MA-4 (ii) 조건 (missing prerequisite state explicitly named in prior approved phase + verifiably absent) 충족. Phase 1과 동일 패턴.

### Consequences
- 메타-로드맵에 Phase 4.5 신설 (시퀀스 의미 1→4→5→2→3 불변, phase 카운트 +1)
- MA-4 일반 deviation protocol 등록 → 후속 phase에서 동일 패턴 합법화
- **Calendar.tsx local event 색 의미 shift**: "manually entered (indigo accent)" → "schedule-domain-typed (violet)" — backend events source-of-truth와 정합
- `border-emerald-500` sunset 2026-08-31 — Phase 5 (Todoist) 머지 후 source-marker taxonomy 정리 spec 진입 필수

### Follow-ups
- 본 plan approve → Step 1 → Step 2 (mid-gate) → Step 3 (메타-로드맵 정정 + Phase 4.5 신설 + MA-4 추가)
- Phase 4.5 ralplan은 Phase 4 머지 + mid-gate pass 후 즉시 호출 (Schedule.tsx + 도메인 챗 영역 border port)

---

## 8. Verification References

본 spec의 사실 주장은 다음 소스에서 확인됨 (Architect/Critic verification log):

- `frontend/tailwind.config.ts:1-9` — `theme: { extend: {} }` 비어있음 (Phase 4 작업 대상, current empty state)
- `frontend/src/index.css:1-13` — `--domain-*`/`--cat-*` 변수 0개, hex 0개 (Tailwind SSOT 채택 근거)
- `frontend/src/pages/Chat.tsx:37,57` — `text-indigo-600`, `bg-indigo-600` (mockup `--accent #4f46e5` 정확 일치 → 변경 0)
- `frontend/src/pages/Calendar.tsx:38` — `<h1 className="text-xl mb-4">` (월 헤더 text-domain-schedule 추가 위치)
- `frontend/src/pages/Calendar.tsx:44` — `<div className="bg-stone-50 px-2 py-1 text-xs uppercase">` (Risk #2 fallback 위치)
- `frontend/src/pages/Calendar.tsx:60` — `border-emerald-500`/`border-indigo-500` ternary (local event border 토큰 교체 위치)
- `frontend/src/components/Sidebar.tsx:8` — `<aside className="w-60 h-screen border-r border-stone-200 bg-white p-4 flex flex-col gap-1 sticky top-0">` (정확한 before string)
- `planning/screens/_shared/style.css:439-445` — commit `890825f` `.domain-chat.dom-*` 6 border rules (Phase 4.5 포팅 대상)
- `docs/superpowers/specs/2026-05-17-mockup-color-tokens-mobile.md:286-309` — Tailwind theme.extend.colors 캐논 (Acceptance (a-2) byte-equal diff 기준)

---

## 9. Status & Next Action

- **Status**: pending approval (Critic APPROVED v3 at iteration 2/5)
- **Next action** (approve 시):
  1. Step 1 (atomic implementation PR) — `feat(frontend): port mockup color tokens to Tailwind + Calendar consumers (Phase 4)`
  2. Step 2 (mid-gate 4 스크린샷 + console error 0)
  3. Step 3 (메타-로드맵 wording correction + Phase 4.5 신설 + MA-4 추가) — `docs(planning): correct §Phase 4 + add Phase 4.5 + MA-4 deviation protocol`
- **Out of scope** (별도 spec): Phase 4.5 (Schedule.tsx + border port + drawer toggle), source-marker taxonomy 정리 (Phase 5+ sunset 2026-08-31)
