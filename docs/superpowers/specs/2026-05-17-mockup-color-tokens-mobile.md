# Mockup 디자인 토큰: 도메인/카테고리 색 일관 매핑 + 모바일 분기

**작성일**: 2026-05-17
**작성자**: damien (with Claude, ralplan consensus v3)
**상태**: pending approval
**선행**: planning/screens/ 전반의 mockup 디자인 정합성 평가
**연관 mockup**: `planning/screens/*.html` 11개 + `_shared/style.css` + `_shared/sidebar.html`
**후속 spec 후보**: 차트 컴포넌트화 · 대시보드 인사이트 위치 변경 · stat 드릴다운 링크 · 데이터 신선도 표시 (본 spec scope 밖)

---

## 1. 목표

블로그 글의 대시보드 원칙 검토 결과 사용자가 명시 채택한 두 항목을 mockup 단계에서 구현하고, React 구현 단계로의 이식 경로(Tailwind theme.extend)를 확정한다.

1. **도메인/카테고리 색 일관 매핑** — 같은 도메인·카테고리는 어느 화면에서 보든 같은 색.
2. **모바일 반응형 분기** — 1인 사용자의 데스크탑/모바일 양극단 사용을 단일 break-point로 커버.

## 2. 비목표 (Out of Scope)

다음 항목은 검토 단계에서 논의됐으나 본 spec에서 다루지 않는다. 각각 별도 follow-up spec 후보:

- stat 카드 미니 시각화 (sparkline / progress bar 추출)
- 대시보드 "오케스트레이터 인사이트" 카드 위치 변경
- 카드 → 도메인 화면 drill-down 링크 (`<a>` wrap)
- 데이터 신선도 timestamp (stat 카드별 "as of HH:MM")
- 다크 모드
- 태블릿(820~1100) 별도 최적화

## 3. 결정 사항

| 항목 | 결정 | 근거 |
|---|---|---|
| 색 토큰 ownership | `_shared/style.css :root` CSS 변수 단일 위치 | 의존성 0 원칙. Tailwind 이식 시 theme.extend로 1:1 매핑 가능 |
| 도메인/카테고리 적용 방식 | `.tag.dom-<name>` / `.tag.cat-<name>` modifier 클래스 | 기존 `.tag` 비파괴. 점진 도입 가능 |
| 시맨틱 색 충돌 처리 | 같은 hex일 경우 `var(--success)` 식 alias로 명시 | SSOT 보존, "다른 이름·같은 색"이 코드에 드러남 |
| 모바일 break-point | 단일 820px | 1인 MVP, 태블릿 데이터 없음. 후속에서 데이터 보고 결정 |
| 사이드바 토글 메커니즘 | **checkbox hack** (`<input type="checkbox">` + `+ .sidebar`) | URL hash 오염 없음(`:target` 단점 회피), JS 0, 브라우저 뒤로가기 영향 없음 |
| `.with-rail` 기존 1100px breakpoint | 820으로 통합 | 1100/820 두 단계 충돌 해소, "단일 의미 변곡점" 원칙 부합 |
| 11개 HTML 파일 편집 | 수동 일괄 치환 비용 수용 + PowerShell 스크립트 제공 | mockup은 임시(React가 대체). 자동화 인프라 도입 ROI 낮음 |
| Tailwind 이식 시 alias | CSS var 참조 대신 hex 직접 등록 | Tailwind `bg-color/10` opacity modifier가 `var(--x)` 비호환 |

## 4. 색 토큰 정의

### 4.1 추가 토큰 (`_shared/style.css :root`)

```css
/* 기존 시맨틱 유지: --accent #4f46e5, --success #16a34a, --warning #d97706, --danger #dc2626 */

/* ─── 도메인 액센트 ─────────────────────────────────────────── */
--domain-schedule: #7c3aed;          --domain-schedule-soft: #f5f3ff;  /* violet-600 — accent와 분리 */
--domain-todo:     #0891b2;          --domain-todo-soft:     #ecfeff;  /* cyan-600 */
--domain-ledger:   var(--success);   --domain-ledger-soft:   #ecfdf5;  /* alias: green-600 */
--domain-finance:  #854d0e;          --domain-finance-soft:  #fef3c7;  /* yellow-800, WCAG 6.16 (700 #a16207 4.51 bare → darken) */
--domain-ideas:    #a21caf;          --domain-ideas-soft:    #fae8ff;  /* fuchsia-700 */
--domain-files:    #475569;          --domain-files-soft:    #f1f5f9;  /* slate-600 */

/* ─── 가계부 카테고리 ──────────────────────────────────────── */
--cat-food:      #9a3412;            --cat-food-soft:    #ffedd5;  /* orange-800/50, WCAG 6.37 (finance yellow와 hue 분리) */
--cat-transport: #0369a1;            --cat-transport-soft:#e0f2fe;  /* sky-700 */
--cat-living:    #4d7c0f;            --cat-living-soft:  #ecfccb;  /* lime-700 */
--cat-leisure:   #be185d;            --cat-leisure-soft: #fce7f3;  /* pink-700 */
--cat-medical:   var(--danger);      --cat-medical-soft: #fef2f2;  /* alias: red-600 */
--cat-fixed:     var(--text-muted);  --cat-fixed-soft:   var(--surface-2);  /* alias: stone-500 */
--cat-misc:      var(--text-faint);  --cat-misc-soft:    var(--bg);  /* alias: stone-400 */
```

**카운트**: 실제 신규 hex 8개 (도메인 4 + 카테고리 4), alias 5개. 총 13쌍 토큰.

### 4.2 카테고리 한글 → class 매핑 표

기존 mockup에서 사용 중인 한국어 카테고리 라벨과 신규 class의 매핑. 일괄 치환 시 이 표만 따른다.

| 한글 라벨 | class modifier |
|---|---|
| 식비 | `cat-food` |
| 교통 | `cat-transport` |
| 생활 | `cat-living` |
| 문화/여가 | `cat-leisure` |
| 의료 | `cat-medical` |
| 고정비 | `cat-fixed` |
| 기타 | `cat-misc` |

도메인 라벨 → class:

| 도메인 | class modifier |
|---|---|
| schedule (일정·비전) | `dom-schedule` |
| todo (업무 TODO) | `dom-todo` |
| ledger (가계부) | `dom-ledger` |
| finance (재무·자산) | `dom-finance` |
| ideas (아이디어) | `dom-ideas` |
| files (파일·사진) | `dom-files` |

### 4.3 Modifier 클래스 정의

```css
/* style.css 끝부분 또는 ".tag.danger" 다음에 추가 */

.tag.dom-schedule { background: var(--domain-schedule-soft); color: var(--domain-schedule); }
.tag.dom-todo     { background: var(--domain-todo-soft);     color: var(--domain-todo); }
.tag.dom-ledger   { background: var(--domain-ledger-soft);   color: var(--domain-ledger); }
.tag.dom-finance  { background: var(--domain-finance-soft);  color: var(--domain-finance); }
.tag.dom-ideas    { background: var(--domain-ideas-soft);    color: var(--domain-ideas); }
.tag.dom-files    { background: var(--domain-files-soft);    color: var(--domain-files); }

.tag.cat-food      { background: var(--cat-food-soft);      color: var(--cat-food); }
.tag.cat-transport { background: var(--cat-transport-soft); color: var(--cat-transport); }
.tag.cat-living    { background: var(--cat-living-soft);    color: var(--cat-living); }
.tag.cat-leisure   { background: var(--cat-leisure-soft);   color: var(--cat-leisure); }
.tag.cat-medical   { background: var(--cat-medical-soft);   color: var(--cat-medical); }
.tag.cat-fixed     { background: var(--cat-fixed-soft);     color: var(--cat-fixed); }
.tag.cat-misc      { background: var(--cat-misc-soft);      color: var(--cat-misc); }
```

기존 `.tag` / `.tag.accent` / `.tag.success` / `.tag.warn` / `.tag.danger`는 **그대로 보존** (비파괴). 새 라벨 추가 시만 modifier 부여.

### 4.4 부가 적용 — stat 카드 좌측 보더

대시보드 4 stat 카드는 도메인 색 4px 좌측 보더로 시각 그룹화. 이건 본 spec의 "색 일관성"에 직접 속하므로 포함.

```html
<div class="card stat dom-schedule">  <!-- 이번 주 일정 -->
<div class="card stat dom-todo">      <!-- 활성 TODO -->
<div class="card stat dom-ledger">    <!-- 5월 지출 -->
<div class="card stat dom-finance">   <!-- 순자산 -->
```

```css
.card.stat.dom-schedule { border-left: 4px solid var(--domain-schedule); }
.card.stat.dom-todo     { border-left: 4px solid var(--domain-todo); }
.card.stat.dom-ledger   { border-left: 4px solid var(--domain-ledger); }
.card.stat.dom-finance  { border-left: 4px solid var(--domain-finance); }
.card.stat.dom-ideas    { border-left: 4px solid var(--domain-ideas); }
.card.stat.dom-files    { border-left: 4px solid var(--domain-files); }
```

## 5. 모바일 분기

### 5.1 단일 breakpoint: `max-width: 820px`

기존 `_shared/style.css:704`의 `.with-rail` 1100px breakpoint는 **삭제**하고 820px로 통합한다. 이유: 820~1100 사이 어색한 중간 상태 제거.

### 5.2 Sidebar drawer — checkbox hack

기존 sidebar 구조는 `<aside class="sidebar">`. 모바일 진입 시 fixed slide-in drawer로 변환.

마크업 변경 (11개 mockup 모두 동일하게):

```html
<body>
<div class="app">
  <input type="checkbox" id="nav-toggle" class="nav-toggle" hidden>

  <label for="nav-toggle" class="topbar-mobile">
    <span class="topbar-burger">☰</span>
    <span class="topbar-brand">home·agent</span>
  </label>

  <aside class="sidebar">
    ... (기존 nav 그대로) ...
    <label for="nav-toggle" class="sidebar-close" aria-label="닫기">✕</label>
  </aside>

  <label for="nav-toggle" class="nav-backdrop"></label>

  <main class="main"> ... </main>
</div>
</body>
```

CSS (style.css 모바일 미디어쿼리 블록):

```css
/* 데스크탑 기본: 토글 관련 요소 숨김 */
.nav-toggle, .topbar-mobile, .sidebar-close, .nav-backdrop { display: none; }

@media (max-width: 820px) {
  /* 1. 레이아웃 단일 컬럼화 */
  .app {
    grid-template-columns: 1fr;
    grid-template-areas: "topbar" "main";
  }
  .topbar-mobile {
    display: flex; align-items: center; gap: 12px;
    grid-area: topbar;
    padding: 12px 16px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    font-family: var(--mono); font-size: 14px;
    cursor: pointer;
    position: sticky; top: 0; z-index: 25;
  }
  .topbar-burger { font-size: 18px; }
  .main { grid-area: main; padding: 16px; max-width: 100%; }

  /* 2. 사이드바 fixed drawer 변환 */
  .sidebar {
    position: fixed; top: 0; left: 0; bottom: 0;
    width: 260px;
    transform: translateX(-100%);
    transition: transform .18s ease;
    z-index: 40;
    box-shadow: var(--shadow);
  }
  .sidebar-close {
    display: block; position: absolute; top: 12px; right: 12px;
    font-size: 18px; color: var(--text-muted); cursor: pointer;
  }

  /* 3. 백드롭 */
  .nav-backdrop {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,.35); z-index: 35;
  }

  /* 4. 토글: checkbox checked일 때 열림 */
  .nav-toggle:checked ~ .sidebar { transform: translateX(0); }
  .nav-toggle:checked ~ .nav-backdrop { display: block; }

  /* 5. 카드 그리드 단일 컬럼화 */
  .grid.cols-2, .grid.cols-3, .grid.cols-4 { grid-template-columns: 1fr; }

  /* 6. 헤더 수직 정렬 */
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .page-header .actions { width: 100%; flex-wrap: wrap; }

  /* 7. 채팅/레일 단일 컬럼 (기존 1100px breakpoint 통합) */
  .chat-wrap, .with-rail { grid-template-columns: 1fr; height: auto; }
  .rail { position: static; max-height: none; }

  /* 8. 칸반 단일 컬럼 */
  .kanban { grid-template-columns: 1fr; }
}
```

### 5.3 백드롭 클릭 → 닫기

`<label for="nav-toggle" class="nav-backdrop">`이 backdrop 자체를 label로 만들기 때문에 클릭 시 checkbox 토글 → drawer 닫힘. JS 0.

## 6. 11개 mockup 파일 일괄 편집

### 6.1 영향 범위

| 파일 | 편집 종류 |
|---|---|
| `_shared/style.css` | 토큰 추가 + modifier 클래스 + 모바일 미디어쿼리 (기존 1100px 삭제) |
| `dashboard.html` | 4개 stat 카드에 dom modifier · 에이전트 활동 tag 매핑 · 어제 지출 카테고리 매핑 · drawer 마크업 |
| `chat.html` | drawer 마크업 · 활성 컨텍스트 도메인 tag 매핑 |
| **`chat-v2.html` (제외)** | inline `<style>`이 `_shared/style.css`를 import하지 않고 자체 `@media (max-width: 768px)` 가짐. drawer 추가하면 충돌. 후속 spec(차트 추출 등)에서 일관 처리. |
| `schedule.html` | drawer 마크업 · `schedule_agent` 도메인 tag 매핑 |
| `ledger.html` | drawer 마크업 · `class="tag"` **15곳** 카테고리 매핑 치환 + `ledger_agent` 도메인 tag |
| `finance.html`, `ideas.html`, `files.html`, `todo.html` | drawer 마크업 · 도메인 agent tag 매핑 |
| `settings.html` | drawer 마크업 · MCP 서버 테이블 6개 도메인 tag 매핑 · 카테고리 색 swatch 7개 토큰 var 참조로 전환 |
| `index.html` | drawer 마크업 (단순 인덱스라 tag 매핑 없음) |

### 6.2 PowerShell 일괄 치환 스크립트 (참고용)

```powershell
# ledger.html 카테고리 매핑 — 한글 라벨 → modifier
$mappings = @{
  '<span class="tag">식비</span>'      = '<span class="tag cat-food">식비</span>'
  '<span class="tag">교통</span>'      = '<span class="tag cat-transport">교통</span>'
  '<span class="tag">생활</span>'      = '<span class="tag cat-living">생활</span>'
  '<span class="tag">문화/여가</span>' = '<span class="tag cat-leisure">문화/여가</span>'
  '<span class="tag">고정비</span>'    = '<span class="tag cat-fixed">고정비</span>'
  '<span class="tag">기타</span>'      = '<span class="tag cat-misc">기타</span>'
  '<span class="tag danger">의료</span>' = '<span class="tag cat-medical">의료</span>'
}
$path = "planning\screens\ledger.html"
$content = Get-Content $path -Raw -Encoding UTF8
$mappings.GetEnumerator() | ForEach-Object { $content = $content.Replace($_.Key, $_.Value) }
Set-Content $path -Value $content -Encoding UTF8 -NoNewline
```

Drawer 마크업 11파일 일괄 삽입은 sidebar.html 외부에 마크업이 inlined 되어 있어 단순 치환이 어렵다. 11파일 수동 편집(약 30~40분) 또는 작은 Python 스크립트로 `<aside class="sidebar">` 앞뒤 패턴 매칭 후 삽입. 본 spec은 수동 편집 권장 (mockup 임시성 + 검증 동시 수행).

## 7. Tailwind 이식 (후속 작업 단서)

`frontend/tailwind.config.ts`의 `theme.extend.colors`에 다음을 추가하면 React 컴포넌트에서 `bg-domain-schedule-soft text-domain-schedule` 식으로 동일 의미를 재사용할 수 있다.

```ts
theme: {
  extend: {
    colors: {
      domain: {
        schedule: { DEFAULT: '#7c3aed', soft: '#f5f3ff' },
        todo:     { DEFAULT: '#0891b2', soft: '#ecfeff' },
        ledger:   { DEFAULT: '#16a34a', soft: '#ecfdf5' },  // success alias hex 직접
        finance:  { DEFAULT: '#854d0e', soft: '#fef3c7' },  // yellow-800 (구현 시 contrast 측정 후 darken)
        ideas:    { DEFAULT: '#a21caf', soft: '#fae8ff' },
        files:    { DEFAULT: '#475569', soft: '#f1f5f9' },
      },
      cat: {
        food:      { DEFAULT: '#9a3412', soft: '#ffedd5' },  // orange-800/50 (finance yellow와 hue 분리)
        transport: { DEFAULT: '#0369a1', soft: '#e0f2fe' },
        living:    { DEFAULT: '#4d7c0f', soft: '#ecfccb' },
        leisure:   { DEFAULT: '#be185d', soft: '#fce7f3' },
        medical:   { DEFAULT: '#dc2626', soft: '#fef2f2' },  // danger alias hex 직접
        fixed:     { DEFAULT: '#78716c', soft: '#f5f5f4' },
        misc:      { DEFAULT: '#a8a29e', soft: '#fafaf9' },
      },
    },
  },
}
```

**왜 hex 직접인가**: Tailwind의 `bg-domain-schedule/30` opacity modifier는 `<alpha-value>` 토큰 형식 또는 hex 문자열일 때만 동작. CSS `var(--x)` 참조는 opacity 신택스를 깬다.

## 8. 검증 (Acceptance Criteria)

### 8.1 Grep-able (자동 확인)

```powershell
# 토큰 정의 존재
Select-String -Path planning\screens\_shared\style.css -Pattern '--domain-schedule:|--cat-food:' | Measure-Object

# ledger.html 카테고리 미치환 0건 (도메인 카테고리는 모두 cat-* modifier 보유)
# "<span class="tag">식비</span>" 같은 식별자 패턴이 0
Select-String -Path planning\screens\ledger.html -Pattern '<span class="tag">(식비|교통|생활|문화/여가|의료|고정비|기타)</span>' | Measure-Object

# 기존 1100px breakpoint 제거됨
Select-String -Path planning\screens\_shared\style.css -Pattern 'max-width:\s*1100px'  # 0건
```

### 8.2 시각 (수동 확인)

| # | 단계 | 기대 |
|---|---|---|
| V1 | 데스크탑 1280 폭에서 `dashboard.html` | 기존 화면과 동일 (회귀 없음) |
| V2 | 데스크탑에서 `ledger.html` 카테고리 색이 도메인 액센트와 시각 구분 | "식비" amber, "교통" sky 등 |
| V3 | 800x600 폭으로 `dashboard.html` | 사이드바 가려짐, ☰ topbar 노출, 카드 1열 |
| V4 | 모바일 폭에서 ☰ 탭 | 사이드바 좌측에서 슬라이드 인 + 백드롭 |
| V5 | 모바일 폭에서 백드롭 클릭 | drawer 닫힘 |
| V6 | 다른 mockup(`ledger.html`, `schedule.html`, `chat.html`) 모바일 폭 | 동일 동작 |
| V7 | `schedule.html` 모바일 폭 | rail이 하단으로 이동 (with-rail 1열화) |

### 8.3 색 대비 (사전 측정)

구현 시점에 측정 완료 (W3C contrast formula). 결과:

| FG | BG | WCAG | 판정 |
|---|---|---|---|
| `#7c3aed` schedule | `#f5f3ff` | **5.19:1** | AA ✓ |
| `#854d0e` finance | `#fef3c7` | **6.16:1** | AA ✓ (700 #a16207은 4.51 bare → 800으로 darken) |
| `#a21caf` ideas | `#fae8ff` | **5.34:1** | AA ✓ |
| `#0369a1` transport | `#e0f2fe` | ~5 | AA ✓ |
| `#4d7c0f` living | `#ecfccb` | **4.60:1** | AA ✓ |
| `#be185d` leisure | `#fce7f3` | **5.09:1** | AA ✓ |
| `#9a3412` food | `#ffedd5` | **6.37:1** | AA ✓ (amber-700 #b45309 4.51은 finance와 색·대비 둘 다 충돌 → orange-800로 hue 분리) |

`--domain-finance`와 `--cat-food`는 ralplan 단계 안에서 bare AA(4.51)였던 yellow-700/amber-700 후보를 yellow-800/orange-800으로 교체하고 background도 amber-50 → orange-50로 분리해 finance(yellow)와 food(orange)가 시각적으로 구분되도록 확정.

## 9. 구현 순서

1. **`_shared/style.css` 토큰 추가** — `:root` 안에 13쌍 + alias.
2. **modifier 클래스 정의** — `.tag.dom-*` / `.tag.cat-*` 13개 + `.card.stat.dom-*` border-left 6개.
3. **색 대비 측정** — 8.3 표 4쌍 측정. 실패 색만 darken 후 토큰 갱신.
4. **기존 1100px breakpoint 삭제 + 820 미디어쿼리 추가** — style.css `:704-707` 블록 교체.
5. **drawer 관련 토글 요소 default-hidden 추가** — 데스크탑에서 보이지 않게.
6. **`dashboard.html` 적용** — stat 4카드 dom modifier · 에이전트 활동 tag · drawer 마크업.
7. **`ledger.html` 적용** — 15곳 카테고리 매핑 (PowerShell 스크립트) · drawer 마크업.
8. **나머지 9개 mockup drawer 마크업** — chat·chat-v2·schedule·finance·ideas·files·todo·settings·index.
9. **시각 회귀 확인** — V1~V7 수동.
10. **commit** — `feat(mockup): domain/category color tokens + mobile drawer`.

## 10. Open Risks (Critic 잔여 우려)

다음은 spec 진행 가능하나 user/리뷰어가 인지해야 할 잔여 리스크.

| 리스크 | 영향 | 완화 |
|---|---|---|
| **11파일 sidebar 마크업 중복 편집** | mockup 임시성으로 ROI 낮음 | 수동 편집 시 1파일 후 시각 확인 → 패턴 확정 → 나머지 일괄. React 단계에 Sidebar 컴포넌트로 자연 해소 |
| **820~1100 태블릿 UX 미최적화** | 1인 MVP 영향 작음 | follow-up: 실사용 데이터 보고 β(2단 break) 도입 결정 |
| **checkbox hack 접근성** | 키보드 포커스 순서 확인 필요 | label `for=` 연결로 스크린리더 호환. React 이식 시 `<Dialog>` 패턴으로 교체 |
| **알맞은 카테고리 추가 시 토큰 수정 필요** | CSS와 라벨의 결합도 | 카테고리 추가는 데이터 모델 변경이므로 spec 자체가 함께 갱신되는 게 자연스러움 |
| **`.with-rail`을 단일 break로 통합 시 schedule 화면의 데스크탑-narrow(820~1100) 사용성 미검증** | 중 | 9.단계에서 schedule.html 1024 폭 시각 확인 항목 추가 |

## 11. 구현 결과 (2026-05-17)

본 spec은 같은 날 `team` 모드(native team primitives 부재로 단일 lead 직접 실행 fallback)로 즉시 구현됨. §9 1~9 모두 통과.

검증 (grep, §8.1):

| 확인 | 결과 |
|---|---|
| `_shared/style.css`에 도메인/카테고리 토큰 32회 사용 | ✓ |
| `_shared/style.css`에 `.tag.(dom\|cat)-` modifier 13개 | ✓ |
| `_shared/style.css`에 `max-width: 1100px` | 0건 ✓ |
| 10개 mockup에 `nav-toggle` 4회씩 (input + 3 label) | ✓ |
| `<span class="tag">CATEGORY</span>` 미치환 | 0건 ✓ |

chat-v2.html은 위에 명시한 사유로 제외 (10개 mockup 처리).

## 12. ADR (Architectural Decision Record)

**Decision**: planning mockup의 도메인/카테고리 색을 `_shared/style.css :root`의 13쌍 CSS 변수로 정의하고, `.tag.dom-*`/`.tag.cat-*` modifier 클래스로 적용. 모바일은 단일 820px breakpoint + checkbox hack drawer.

**Drivers**:
- React 이식 시 Tailwind theme.extend로 1:1 매핑
- 의존성 0 원칙 유지
- 기존 mockup 비파괴

**Alternatives considered**:
- (색) data-attribute selector → Tailwind 이식 비용↑
- (색) JSON catalog + JS 주입 → 의존성 0 위배
- (모바일) `:target` hack → URL hash 오염
- (모바일) `<details>/<summary>` → drawer 스타일링 제약
- (모바일) 1100/820 2단계 break → 충돌 + MVP에 과함

**Why chosen**:
- modifier class + alias가 SSOT + 비파괴 + 이식성 3원칙 모두 만족
- checkbox hack은 URL/뒤로가기 부작용 없는 유일한 JS-0 옵션
- 단일 break는 검증 단순성과 mockup 임시성에 부합

**Consequences**:
- 새 카테고리 추가 시 토큰 + modifier 둘 다 수정 필요 (수용 가능, 빈도 낮음)
- 11파일 sidebar 중복 → React 단계까지 감내
- 태블릿 폭 UX 별도 검증 미수행

**Follow-ups**:
- 차트 컴포넌트 추출 spec
- 대시보드 인사이트 카드 위치/우선순위 spec
- stat 카드 drill-down + 데이터 신선도 spec
- (선택) 다크 모드 토큰 spec

---

## 변경 이력

- 2026-05-17: 초안 작성 (ralplan consensus v3, Architect+Critic 피드백 반영)
