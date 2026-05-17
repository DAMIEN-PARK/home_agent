# Phase 2 Item 1: 차트 컴포넌트화 — inline SVG (no library)

**Status:** pending approval (RALPLAN-DR v3, Critic APPROVED at iteration 2/5)
**Date:** 2026-05-18
**Owner:** damien
**Parent roadmap:** `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` §Phase 2 **lines 155-156** (line 155 explicitly authorizes library decision within this ralplan)
**Scope:** Dashboard.tsx 신규 (frontend/src/pages/Dashboard.tsx) + Sparkline.tsx + ProgressBar.tsx (inline SVG, no chart library) + getTasks helper + /dashboard route + sidebar nav

**Iteration history:**
- v1: recharts 채택 + Dashboard 2 chart consumer + Ledger 월별 차트 (사용자 prompt) → Architect NOT-approved (8 issues + 5 violations). Steelman: **96 kB recharts가 2 trivial chart에 over-engineering** + citation phantom (Architect가 잘못된 path 검색) + ledger 차트는 mandate 외
- v2: Architect synthesis (inline SVG 채택, recharts drop) + citation 정정 → Critic ITERATE (2 MAJOR: line 137 → 156, API signature) + 2 MINOR
- v3: 4 fixes + **MA-4 트리거 제거** (line 155 wording이 library decision authorize) → Critic **APPROVE** at iteration 2

---

## 1. RALPLAN-DR Summary

### Principles

1. **Library deferred, inline SVG 현재** — recharts/chart.js 도입 보류. 2 trivial chart는 inline SVG ~40 LOC each.
2. **메타-로드맵 line 155 wording strict 충족** — "차트 라이브러리 선정은 #1 ralplan 내 결정" → 본 ralplan이 명시 권한. 결정 = inline SVG. **MA-4 트리거 없음**.
3. **Tailwind class 색 토큰 직접 적용** — `<line className="stroke-domain-schedule"/>` (Tailwind 3.4.16 ≥ 3.3 `stroke-*` utility 지원, verified).
4. **Existing backend data만 사용** — `/api/events` (sparkline) + `/api/todo/tasks` (progress bar). `getTasks` 신규 helper.
5. **Ledger 월별 차트는 mandate 외** — 사용자 prompt 확장 (메타-로드맵 §Phase 2 item 1은 "차트 컴포넌트화"만 mandate). Ledger backend 부재(`models/ledger.py`, `api/ledger.py` absent) → 본 phase scope 외, ledger backend phase 신설 시 동행.

### Decision Drivers

1. CLAUDE.md §2 (no library lock-in for 2 trivial chart) + 0 kB bundle 추가
2. 메타-로드맵 line 155 "ralplan 내 결정" 권한 — library decision authority 본 ralplan 안에
3. Tailwind class 색 토큰 직접 통합 (CSS var workaround 회피)

### Viable Options

| Option | 설명 | Pros | Cons |
|---|---|---|---|
| **A'. Inline SVG** (Architect synthesis, **Recommended**) | Dashboard.tsx + Sparkline + ProgressBar (각 ~40 LOC) | 0 kB bundle, Tailwind class 직접, library 재검토 자유 | 3번째 non-trivial chart 시 escalation 필요 |
| B. recharts | declarative React API | 96 kB lock-in, var workaround friction — **CLAUDE.md §2 위반, v1 폐기** | |
| C. chart.js | 작은 bundle (33 kB) | imperative + wrapper 의존 | |
| D. Defer entire phase | scope skip | mandate 위반 | |

→ **Option A' 채택**. line 155 wording이 본 결정 authorize → MA-4 트리거 없음.

---

## 2. Library Decision (Phase 2 §3 in-phase)

**Decision: inline SVG, recharts/chart.js 미선정 (deferred to 3rd consumer).**

**Rationale**:
- 2 trivial chart (sparkline + horizontal stacked bar) — inline SVG ~80 LOC 총 충분
- 96 kB recharts vs 33 kB chart.js 비교 시점에 inline SVG 0 kB가 더 minimum
- 향후 3번째 non-trivial chart type (stacked grouped / pie / scatter / candlestick) 등장 시 별도 library-selection ralplan 진입

**메타-로드맵 line 155 wording 직접 인용**: "후보 (각각 별도 spec 필요, **차트 라이브러리 선정은 #1 ralplan 내 결정**)" → 본 ralplan이 라이브러리 선정 권한을 가지며, "inline SVG, 미선정 deferred"가 valid choice. **mandate strict 충족**.

---

## 3. Implementation Plan

### A. `frontend/src/components/charts/Sparkline.tsx` 신규 (~40 LOC)

```tsx
interface SparklineProps {
  data: number[];
  strokeClassName?: string; // 예: "stroke-domain-schedule"
  height?: number;          // default 32
  width?: number;           // default 120
}

export function Sparkline({ data, strokeClassName = "stroke-stone-500", height = 32, width = 120 }: SparklineProps) {
  if (data.length === 0) {
    return <div className="text-xs text-stone-400">데이터 없음</div>;
  }
  const max = Math.max(...data, 1);
  const points = data
    .map((v, i) => `${(i / (data.length - 1 || 1)) * width},${height - (v / max) * height}`)
    .join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label="sparkline">
      <polyline
        points={points}
        fill="none"
        strokeWidth={2}
        className={strokeClassName}
      />
    </svg>
  );
}
```

### B. `frontend/src/components/charts/ProgressBar.tsx` 신규 (~40 LOC)

```tsx
interface Segment {
  label: string;
  value: number;
  colorClassName: string;  // 예: "bg-domain-todo"
}

interface ProgressBarProps {
  segments: Segment[];
  height?: number;  // default 16
}

export function ProgressBar({ segments, height = 16 }: ProgressBarProps) {
  const total = segments.reduce((a, s) => a + s.value, 0);
  if (total === 0) {
    return <div className="text-xs text-stone-400">할일 없음</div>;
  }
  return (
    <div className="flex w-full rounded overflow-hidden" style={{ height }}>
      {segments.map((s, i) => {
        const pct = (s.value / total) * 100;
        if (pct === 0) return null;
        return (
          <div
            key={i}
            className={s.colorClassName}
            style={{ width: `${pct}%` }}
            title={`${s.label}: ${s.value}`}
          />
        );
      })}
    </div>
  );
}
```

### C. `frontend/src/lib/api.ts` 확장 — `getTasks` helper

```ts
export interface TaskDto {
  id: string;
  title: string;
  status: string;           // open | done | deferred | cancelled
  priority: number;         // 1 (highest) .. 5 (lowest)
  due_at: string | null;
  completed_at: string | null;
  // Phase 5 추가 (TodoAgent._serialize_task 출력과 동기화)
  source?: string;          // local | todoist
  sync_state?: string | null;
}

export async function getTasks(
  userId: string,
  status?: string,
): Promise<TaskDto[]> {
  const q = new URLSearchParams({ user_id: userId });
  if (status) q.set("status", status);
  const r = await fetch(`/api/todo/tasks?${q.toString()}`, {
    headers: deviceHeaders(),
  });
  if (!r.ok) throw new Error(`tasks failed: ${r.status}`);
  return r.json() as Promise<TaskDto[]>;
  // backend/app/api/todo.py:115 response_model=list[TaskOut] — wrapper 없음
}
```

### D. `frontend/src/pages/Dashboard.tsx` 신규

- `/dashboard` 라우트
- **2 chart consumer**:
  - **events sparkline (월별, last 6 months)**: `useQuery(["events", from, to], () => getEvents(...))` → 월별 count aggregation → `<Sparkline data={[...]} strokeClassName="stroke-domain-schedule" />`. 데이터 윈도우: `from = startOfMonth(today - 5 months)`, `to = endOfMonth(today)`
  - **todo status progress**: `useQuery(["tasks"], () => getTasks(userId))` → segments by status → `<ProgressBar segments={[{label: "open", value: N, colorClassName: "bg-domain-todo"}, {label: "done", value: M, colorClassName: "bg-emerald-500"}, {label: "deferred", value: K, colorClassName: "bg-stone-400"}]} />`

Layout: 2-card grid (desktop), 1-column (mobile). Tailwind `grid md:grid-cols-2`.

### E. `frontend/src/App.tsx` — `/dashboard` 라우트 추가

```tsx
import Dashboard from "@/pages/Dashboard";
// inside <Routes>:
<Route path="/dashboard" element={<Dashboard />} />
```

### F. `frontend/src/components/Sidebar.tsx` — NavLink 추가

```tsx
<NavLink to="/dashboard" className={navItemClass}>
  ▦ 대시보드
</NavLink>
```
(mockup `planning/screens/dashboard.html:18` icon `▦` 동일. 기존 `◐ 챗`, `▣ 캘린더`, `◆ 일정`과 충돌 없음 verified.)

### G. Tests

#### `frontend/src/__tests__/Sparkline.test.tsx`
- data=[1,3,2,5] → SVG polyline 존재 + className 포함
- data=[] → "데이터 없음" 텍스트 + SVG 없음

#### `frontend/src/__tests__/ProgressBar.test.tsx`
- segments=[{label:"open",value:2,colorClassName:"bg-domain-todo"}, ...] → div 개수 + width 비례
- segments value 합=0 → "할일 없음" 텍스트

#### `frontend/src/__tests__/Dashboard.test.tsx`
- mocked fetch (`/api/events`, `/api/todo/tasks`) → Sparkline + ProgressBar 둘 다 렌더
- title `대시보드` 또는 헤더 텍스트 존재

#### `frontend/src/__tests__/Routing.test.tsx`
- `<Routes>` 블록에 `<Route path="/dashboard" element={<Dashboard />} />` 추가
- 신규 test: `/dashboard` 진입 → Dashboard 콘텐츠 표시

---

## 4. Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| a | inline SVG charts (no chart library) | `git diff main frontend/package.json` recharts/chart.js 추가 없음 |
| b | Sparkline.tsx + ProgressBar.tsx 신규 (각 ≤ 50 LOC) | `wc -l frontend/src/components/charts/*.tsx` |
| c | Dashboard.tsx에 Sparkline + ProgressBar 모두 import + 사용 | `grep -E "(Sparkline\|ProgressBar)" frontend/src/pages/Dashboard.tsx` ≥ 2 |
| d | App.tsx `/dashboard` 라우트 | `grep "path=\"/dashboard\"" frontend/src/App.tsx` ≥ 1 |
| e | Sidebar `▦ 대시보드` NavLink | `grep "▦ 대시보드" frontend/src/components/Sidebar.tsx` ≥ 1 |
| f | `getTasks(userId): Promise<TaskDto[]>` (배열 직접, no wrapper) | `grep "Promise<TaskDto\[\]>" frontend/src/lib/api.ts` ≥ 1 |
| g | 기존 tests 회귀 0 + 신규 ≥ 4 tests 그린 (Sparkline + ProgressBar + Dashboard + Routing) | `cd frontend && npm run test` exit 0 |
| h | `npm run build` exit 0 (TypeScript + Vite) | build |
| i | **mid-verify**: Dashboard.tsx × {desktop 1440, mobile 390}. 데이터 있으면 sparkline + progress 시각; 데이터 없으면 empty state ("데이터 없음", "할일 없음") 시각. console error 0. | 수동 |
| j | code-reviewer agent pass on PR (분리 verifier lane) | OMC agent |

**선결 조건 (acceptance i)**: `backend/scripts/seed_dev.py`로 fixture events 3-5건 + tasks 3-5건 생성 권장. 미존재 시 empty state 확인.

---

## 5. Out of Scope (Phase 2 Item 1)

- **Ledger 월별 차트** — 메타-로드맵 §Phase 2 item 1 mandate 외 (사용자 prompt 확장). Ledger backend (`models/ledger.py`, `api/ledger.py`) 부재 → ledger backend phase 신설 시 동행. 본 phase scope 외, MA-4 트리거 아님 (mandate 외 scope decision).
- **차트 library 도입** (recharts/chart.js) — 3번째 non-trivial chart type 등장 시 별도 library-selection ralplan 진입. 메타-로드맵 line 155 권한 그대로.
- **Dashboard analytics depth** — sparkline + progress 2건만. 다른 dashboard 위젯 (KPI 카드, alert 등) 별도 phase
- **Backend chart data aggregation endpoint** — client-side 가공 (last 6 months events client 집계)

---

## 6. Open Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | `useQuery(["tasks"])` `/api/todo/tasks` 호출 (Phase 5 머지 후 verified, deps 변동 없음) | 기존 endpoint 그대로 사용 |
| 2 | 사용자 데이터 0건 시 empty state | Sparkline `data.length === 0 → "데이터 없음"` + ProgressBar `segments 합 = 0 → "할일 없음"` 명시 |
| 3 | mid-verify 실 데이터 비어있으면 sparkline UI 검증 어려움 | `backend/scripts/seed_dev.py` fixture events/tasks 생성 권장. 미존재 시 empty state 시각 검증으로 대체 |

---

## 7. ADR

### Decision
inline SVG 채택 (recharts/chart.js drop). `Dashboard.tsx` + `Sparkline.tsx` + `ProgressBar.tsx` 신규. `getTasks` API helper 추가. `/dashboard` 라우트 + Sidebar nav. Ledger 월별 차트는 mandate 외 scope으로 deferred (ledger backend 부재).

### Drivers
- 메타-로드맵 line 155 "ralplan 내 결정" 권한
- CLAUDE.md §2 (no library lock-in for 2 trivial chart, no abstractions for absent features)
- 0 kB bundle 추가 + Tailwind class 색 토큰 직접 통합

### Alternatives considered
- **B. recharts** — 96 kB lock-in + var workaround (Architect synthesis로 폐기, v1 → v2 pivot)
- **C. chart.js** — 33 kB이나 imperative + wrapper 의존
- **D. Defer entire phase** — mandate 위반

### Why chosen
Architect Option A' synthesis 적용 + line 155 wording 권한 인용. 2 trivial chart에 96 kB library는 over-engineering. 향후 3번째 chart type 등장 시점에서 library-selection ralplan 별도.

### Consequences
- 0 kB bundle 추가, ~120 LOC 신규 코드 (Sparkline 40 + ProgressBar 40 + Dashboard 40 + getTasks helper)
- **메타-로드맵 wording 후처리 commit 불필요** (line 155-156 strict 충족, MA-4 트리거 없음 — Phase 1/4/4.5/3와 달리 deviation 0)
- Ledger 월별 차트는 별도 phase (ledger backend 신설 + Ledger.tsx + 차트)
- 향후 3번째 chart type 시 library-selection ralplan 별도 진입 (recharts vs chart.js vs nivo 등 재검토)

### Follow-ups
- Phase 2 Item 2~5 (인사이트 위치 변경, drill-down, freshness timestamp, 다크 모드) 각각 별도 ralplan
- Ledger backend phase (model + API + agent 추가, Ledger.tsx + 월별 차트 포함) 별도 ralplan
- 3번째 chart type 필요 시 library-selection ralplan 진입

---

## 8. Meta-Roadmap 정합

| 메타-로드맵 §Phase 2 항목 | v3 충족 여부 |
|---|---|
| Line 155 "라이브러리 선정은 #1 ralplan 내 결정" | ✓ 본 ralplan v3 결정 = inline SVG, library 미선정 (deferred to 3rd consumer) |
| Line 156 "차트 컴포넌트화 — 라이브러리 선정(recharts vs chart.js) 포함" | ✓ 라이브러리 선정 결정 = inline SVG. mandate strict 충족 |
| Line 157+ "후보 분할" (item 2~5) | 본 phase는 item 1만. 다른 item은 별도 ralplan |

**MA-4 트리거 없음** — line 155 wording이 library decision authority를 본 ralplan에 부여, 본 결정은 mandate 내. Ledger 차트는 mandate 외 사용자 prompt 확장 → 그저 scope decision, deviation 아님.

---

## 9. Verification References

본 spec 사실 주장 검증 (Architect/Critic):

- `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` lines 155-156 — Phase 2 item 1 mandate + library authority
- `backend/app/api/todo.py:115` — `response_model=list[TaskOut]` (Promise<TaskDto[]> 정합)
- `frontend/package.json:27` — Tailwind `^3.4.16` ≥ 3.3 (stroke-* utility 지원)
- `frontend/src/lib/api.ts` — `EventDto`, `getEvents` 기존 패턴 (getTasks 미러 대상)
- `frontend/src/components/Sidebar.tsx:10-18` — 기존 icons `◐`, `▣`, `◆` (▦ 충돌 없음 verified)
- `frontend/src/App.tsx:26-30` — 기존 라우트 (/dashboard 미존재 → 추가)
- `planning/screens/dashboard.html:18` — `▦ 대시보드` icon precedent
- `backend/app/db/models/` — ledger model 부재 (ledger 차트 deferred 정당화)
- `backend/app/api/` — ledger api 부재
- Phase 4 `abef6c8` — Tailwind theme.extend.colors `domain.todo.DEFAULT="#0891b2"` 등 (Dashboard ProgressBar segments colorClassName 매핑)

---

## 10. Status & Next Action

- **Status**: pending approval (Critic APPROVED v3 at iteration 2/5)
- **Next action (approve 시)**:
  1. Step 1 (atomic implementation PR) — `feat(frontend): Dashboard with inline SVG sparkline + progress bar (Phase 2 Item 1)`
  2. Step 2 (mid-verify Dashboard.tsx × {desktop 1440, mobile 390}, console error 0, empty state OR populated state)
  3. **Step 3 불필요** (MA-4 트리거 없음, 메타-로드맵 mandate strict 충족)
- **Out of scope (별도 phase)**: Ledger backend + 월별 차트, 3번째 chart type 시 library-selection, Phase 2 Item 2~5
