# Phase 3: 시각 회귀 검증 보고서 V1~V11

**Status:** pending user manual verification (자동 검증 완료, 시각 검증 8개 항목 대기)
**Date:** 2026-05-18
**Owner:** damien
**Parent roadmap:** `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md` (§Phase 3)
**Mockup spec V1~V7 source:** `docs/superpowers/specs/2026-05-17-mockup-color-tokens-mobile.md` §8.2 (lines 330-340)

**Iteration history:**
- v1 (Hybrid 60min): manual visual sweep 전체 V1~V11. → Architect 7 issues + 3 principle violations. Steelman: mid-gate 결과 중복 + token regression carve-out 누락 + screenshot evidence 부재
- v2 (Architect synthesis): token-regression carve-out + carry-forward via git diff + screenshot. → Critic ITERATE 5 issues (mockup count "11" vs 10, per-V viewport scope expansion, V6 sampling list)
- v3 (spec §8.2 strict 회복 + MA-4 deviation note + screenshot in-repo 결정): → Critic **APPROVE** at iteration 2/5

---

## 1. Scope

### 1.1 Mockup count deviation (MA-4 (ii))

메타-로드맵 §Phase 3:169은 "11개 mockup"으로 명시하나, `planning/screens/` 실측은 **10 HTML 파일**. 차이 사유: `chat-v2.html`이 commit `cd1af51` ("promote chat-v2 (Pretext-native) to chat, retire legacy")에서 폐기됨. cd1af51는 Phase 4 spec(`2026-05-17-mockup-color-tokens-mobile.md`) §11 시점 이전 결정이며, Phase 3 acceptance 작성 당시에는 11개 가정이었으나 실제 폐기로 10개.

**MA-4 (ii) trigger**: "missing prerequisite state explicitly named in prior approved phase and verifiably absent in the codebase at the time of deviation."

**Verification**:
```bash
ls planning/screens/*.html | wc -l   # → 10
git log --oneline --follow planning/screens/chat.html | grep cd1af51   # → match
```

**후처리** (본 보고서 머지 직후): 메타-로드맵 §Phase 3 line 169 "11개 mockup" → "10개 mockup (chat-v2 폐기 cd1af51)" 정정 commit.

### 1.2 Scope items (총 13: mockup 10 + React 3)

| Item | Target | Viewport | Method |
|---|---|---|---|
| V1 | `dashboard.html` | 1280 | manual visual |
| V2 | `ledger.html` | 1280 | manual visual |
| V3 | `dashboard.html` | 800×600 | manual visual |
| V4 | `dashboard.html` | 390 (mobile, ☰ tap → drawer open) | manual visual |
| V5 | `dashboard.html` | 390 (mobile, backdrop click → drawer close) | manual visual |
| V6 | `ledger.html`, `schedule.html`, `chat.html` (sampling 3) | 390 | manual visual |
| V7 | `schedule.html` | 390 (rail 하단 이동) | manual visual |
| V8 | `Chat.tsx` | 1440 + 390 | **carry-forward `abef6c8`** (git diff empty 검증됨) |
| V9 | `Calendar.tsx` | 1440 + 390 | **carry-forward `abef6c8`** (git diff empty 검증됨) |
| V10 | `Schedule.tsx` | 1440 + 390 | **carry-forward `9878236`** (git diff empty 검증됨) |
| V11 | `Sidebar.tsx` NavLink active state (3개 라우트 클릭) | desktop only | manual visual; mobile = N/A (Phase 4 §Risk #5 known constraint) |

---

## 2. 자동 검증 (실행 완료, 2026-05-18)

### 2.1 Token integrity (Phase 4 token gate carry-forward)

**Command**:
```bash
git diff abef6c8..HEAD -- frontend/tailwind.config.ts planning/screens/_shared/style.css
```

**Result**: ✅ **EMPTY DIFF** → Phase 4 acceptance (a-1) grep 결과 reference로 충족. token 회귀 0.

### 2.2 Drawer integrity (10 mockup × 4 nav-toggle)

**Command**:
```bash
for f in planning/screens/{dashboard,chat,schedule,todo,ledger,finance,ideas,files,settings,index}.html; do
  grep -c "nav-toggle" "$f"
done
```

**Result**: ✅ 10 / 10 mockup × **4 each** (input + 3 label) = 40 instances.

### 2.3 V8/V9/V10 carry-forward git diff

| V | Path | Since SHA | Diff lines | Decision |
|---|---|---|---|---|
| V8 | `frontend/src/pages/Chat.tsx`, `frontend/src/index.css` | `abef6c8` | 0 | ✅ carry-forward |
| V9 | `frontend/src/pages/Calendar.tsx`, `frontend/src/index.css` | `abef6c8` | 0 | ✅ carry-forward |
| V10 | `frontend/src/pages/Schedule.tsx`, `frontend/src/components/Sidebar.tsx` | `9878236` | 0 | ✅ carry-forward |

**Conclusion**: V8, V9, V10은 mid-gate sha 이후 변경 없음 → 재검증 불필요. mid-gate pass 결과 그대로 reference.

---

## 3. 수동 검증 (사용자 환경, ~20-25min)

### 3.1 환경 셋업

```powershell
# Terminal 1 — Mockup HTTP server
cd planning/screens
python -m http.server 8001

# Terminal 2 — React dev server
cd frontend
npm run dev

# Browser: Chrome DevTools responsive mode
# Viewports: 1280 (desktop), 800x600, 390 (mobile)
```

### 3.2 Mockup V1~V7 + V11 결과 (사용자 기입)

각 항목 PASS/FAIL/N/A 기입. FAIL 시 screenshot 필수 + 회귀 분류 (Token / Markup-only). PASS 항목은 V당 1 sample screenshot.

| V | Target | Expected (spec §8.2) | Result | Screenshot | 회귀 분류 (FAIL 시) |
|---|---|---|---|---|---|
| V1 | dashboard.html @ 1280 | 기존 화면과 동일 (회귀 없음) | ⬜ TBD | `planning/verify/phase-3/v1-dashboard-1280.png` | — |
| V2 | ledger.html @ 1280 | 카테고리 색 도메인 액센트와 시각 구분 (식비 amber, 교통 sky 등) | ⬜ TBD | `planning/verify/phase-3/v2-ledger-1280.png` | — |
| V3 | dashboard.html @ 800×600 | 사이드바 가려짐, ☰ topbar 노출, 카드 1열 | ⬜ TBD | `planning/verify/phase-3/v3-dashboard-800.png` | — |
| V4 | dashboard.html @ 390 ☰ tap | 사이드바 좌측에서 슬라이드 인 + 백드롭 표시 | ⬜ TBD | `planning/verify/phase-3/v4-dashboard-390-open.png` | — |
| V5 | dashboard.html @ 390 backdrop click | drawer 닫힘 | ⬜ TBD | `planning/verify/phase-3/v5-dashboard-390-close.png` | — |
| V6a | ledger.html @ 390 | drawer 동작 동일 | ⬜ TBD | `planning/verify/phase-3/v6a-ledger-390.png` | — |
| V6b | schedule.html @ 390 | drawer 동작 동일 | ⬜ TBD | `planning/verify/phase-3/v6b-schedule-390.png` | — |
| V6c | chat.html @ 390 | drawer 동작 동일 | ⬜ TBD | `planning/verify/phase-3/v6c-chat-390.png` | — |
| V7 | schedule.html @ 390 | rail이 하단으로 이동 (with-rail 1열화) | ⬜ TBD | `planning/verify/phase-3/v7-schedule-390.png` | — |
| V11 | Sidebar NavLink desktop /chat /calendar /schedule 클릭 | 각 페이지 전환 + active state (bg-indigo-50 text-indigo-600). mobile = N/A 알려진 제약 | ⬜ TBD | `planning/verify/phase-3/v11-sidebar-nav.png` | — |

### 3.3 Screenshot 디렉토리 정책

- **위치**: `planning/verify/phase-3/` (in-repo)
- **명명**: `v{N}-{file-stem}-{viewport}.png` (예: `v1-dashboard-1280.png`)
- **포함 기준**:
  - 각 V-item PASS 1 sample (V1~V7+V11 = 8 sample)
  - FAIL 항목은 **모두** screenshot 필수
- **사이즈 가이드라인**: 총 < 1MB. 각 PNG < 100KB 예상 (mockup 정적 + viewport 제약).
- **commit**: 보고서 머지와 동일 PR에 binary 포함 OR 별도 commit으로 분리 (편한 쪽).

---

## 4. Failure Handling

### 4.1 Token-regression (CARRY-FORWARD: fix-forward in this phase)

회귀 원인이 `_shared/style.css`의 `--domain-*`/`--cat-*` 토큰 또는 `frontend/tailwind.config.ts`의 token block에 있으면 **fix-forward** — 본 phase 내 commit으로 수정. 이유: 토큰은 React + mockup 양쪽에서 공유 — 회귀는 production-affecting bug.

**Trigger**: V1~V11 어디든 FAIL이고 원인이 shared token이면.

### 4.2 Mockup markup-only regression (BACKLOG)

회귀가 개별 mockup HTML의 markup (drawer 마크업 누락, class 오타, 등)에 국한되고 token과 무관하면 **fail-backlog** — 별도 spec issue로 등록, 본 phase 외 처리. 이유: mockup은 React에 의해 영원히 대체될 예정 — markup-only fix ROI 낮음.

**Trigger**: V1~V7 mockup만 FAIL이고 원인이 token 아님.

### 4.3 React-only regression (FIX-FORWARD)

V8~V11 React 페이지 FAIL은 모두 fix-forward (production 영향).

---

## 5. Acceptance Criteria

| # | Criterion | Status |
|---|---|---|
| a | Token integrity (git diff `abef6c8..HEAD` 빈 결과) | ✅ PASS (§2.1) |
| b | Drawer integrity (10 mockup × 4 nav-toggle) | ✅ PASS (§2.2) |
| c | V1~V7 manual visual + screenshot per spec §8.2 per-row viewport | ⬜ TBD |
| d | V8/V9/V10 carry-forward decision (git diff empty → reference) | ✅ PASS (§2.3) |
| e | V11 desktop NavLink 3개 click + active state | ⬜ TBD |
| f | Token regression 발견 시 fix-forward commit (mockup/React 무관) | N/A (token 회귀 없음 §2.1) |
| g | Mockup markup-only regression 발견 시 fail-backlog (별도 spec issue) | ⬜ TBD |
| h | Screenshot in-repo at `planning/verify/phase-3/` (총 < 1MB) | ⬜ TBD |
| i | 보고서 commit | ⬜ TBD (본 spec) |
| j | 후처리 commit: 메타-로드맵 §Phase 3 line 169 mockup count 정정 | ⬜ TBD |

---

## 6. 사용자 액션 체크리스트

자동 검증 모두 PASS. 다음 8 manual items + screenshot + commits만 남음:

- [ ] Mockup HTTP server + React dev server 띄우기 (§3.1)
- [ ] V1: dashboard.html @ 1280 — 기존 화면 회귀 없음 확인 + screenshot
- [ ] V2: ledger.html @ 1280 — 카테고리 색 시각 구분 확인 + screenshot
- [ ] V3: dashboard.html @ 800 — sidebar 가려짐 + ☰ + 카드 1열 확인 + screenshot
- [ ] V4: dashboard.html @ 390 ☰ tap → drawer open + backdrop 확인 + screenshot
- [ ] V5: dashboard.html @ 390 backdrop click → drawer close 확인 + screenshot
- [ ] V6: ledger/schedule/chat.html @ 390 drawer 동작 확인 (3 sample) + screenshot
- [ ] V7: schedule.html @ 390 rail 하단 이동 확인 + screenshot
- [ ] V11: desktop sidebar NavLink 3개 클릭 + active state 확인 + screenshot
- [ ] 본 보고서 §3.2 표에 PASS/FAIL 기입 + screenshot 경로 채우기
- [ ] Token-regression 발견 시 fix-forward commit (§4.1)
- [ ] Mockup markup-only regression 발견 시 별도 fail-backlog spec 작성 (§4.2)
- [ ] 본 보고서 commit (acceptance i)
- [ ] 후처리: 메타-로드맵 §Phase 3 line 169 "11개" → "10개 (chat-v2 폐기 cd1af51)" 정정 commit (acceptance j)

---

## 7. Out of Scope

- **Playwright/Cypress 자동화** — 본 phase 외, Phase 6+ 검토
- **mockup markup-only regression fix** — fail-backlog (별도 spec)
- **모바일 drawer toggle in React** — Phase 4.5+ deferred (MA-4)
- **다크 모드 / 다국어 / 태블릿 최적화** — mockup spec §2 deferred 그대로

---

## 8. Open Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | User-availability gating (sole-operator) — manual 시각 검증 시간 | ~20-25min 압축 (자동 검증 + carry-forward로 V8/V9/V10 면제) |
| 2 | mockup markup-only 회귀 fix ROI 낮음 | fail-backlog 정당화 (mockup React 대체 예정) |
| 3 | Screenshot in-repo size 누적 | V-item당 1 PASS sample + FAIL만 제한, < 1MB 가이드라인 |

---

## 9. ADR

### Decision
Hybrid report (자동 검증 grep + git diff carry-forward + 사용자 수동 시각) + token-regression carve-out (fix-forward) + mockup markup-only carve-out (fail-backlog) + screenshot in-repo at `planning/verify/phase-3/` + MA-4 (ii) deviation note for mockup count 10 vs "11".

### Drivers
- 메타-로드맵 §Phase 3 acceptance strict (token-regression carve-out으로 mini loop 정합)
- Architect synthesis (carry-forward via git diff 중복 제거)
- 1인 환경 minimum (~20-25min vs Playwright 3-4hr)
- Audit gap 해소 (screenshot in-repo)

### Alternatives considered
- **B. Playwright full automation** — over-engineering, mockup 임시성 ROI 낮음
- **C. Manual-only no doc** — acceptance "보고서" 위반
- **v1 X. 60min full manual sweep** — mid-gate 중복, screenshot 부재

### Why chosen
Architect synthesis 적용 + spec §8.2 per-V viewport strict 회복 + MA-4 deviation note 명시.

### Consequences
- User time ~20-25min (8 manual items + screenshot)
- Screenshot 디렉토리 `planning/verify/phase-3/` 신규 (in-repo, < 1MB)
- 후처리 메타-로드맵 §Phase 3 line 169 mockup count 정정 commit 1건
- 자동 검증 모두 PASS (§2) — V8/V9/V10는 carry-forward로 면제

### Follow-ups
- fail-backlog 발생 시 별도 mockup-fix spec 진입
- Phase 6+ 시 Playwright 자동화 검토 (실 사용 회귀 빈도 데이터 보고 결정)

---

## 10. Meta-Roadmap 정합

| 메타-로드맵 §Phase 3 항목 | v3 충족 여부 |
|---|---|
| 11 mockup + React 페이지 전부 통과 | 10 mockup (cd1af51 폐기) + 3 React = **13 항목**. MA-4 (ii) deviation note 명시 + 후처리 정정 commit |
| V1~V7 desktop+mobile 보고서 | ✓ §3.2 per-V row + screenshot 경로 |
| 회귀 발견 시 fix → 재검증 mini loop | ✓ token-regression carve-out (fix-forward) + React fix-forward. mockup markup-only는 backlog (carve-out 정당화) |

**MA-4 트리거 (mockup count)**: ✓ (ii) prerequisite chat-v2 retirement explicitly named in `2026-05-17-mockup-color-tokens-mobile.md` §11 + verifiably absent (cd1af51). 후처리 commit으로 정정.

---

## 11. Verification References

본 spec 사실 주장 검증:

- `docs/superpowers/specs/2026-05-17-execution-roadmap-design.md:164-171` — Phase 3 mandate ("11개 mockup", "회귀 mini loop")
- `docs/superpowers/specs/2026-05-17-mockup-color-tokens-mobile.md:330-340` — V1~V7 source per-row
- `planning/screens/` — 10 HTML 파일 실측 (`dashboard, chat, schedule, todo, ledger, finance, ideas, files, settings, index`)
- commit `cd1af51` "promote chat-v2 (Pretext-native) to chat, retire legacy" — mockup count 10 사유
- commit `abef6c8` "port mockup color tokens to Tailwind + Calendar consumers (Phase 4)" — V8/V9 carry-forward 기준
- commit `9878236` "Schedule.tsx functional domain chat + border port (Phase 4.5)" — V10 carry-forward 기준
- `git diff abef6c8..HEAD -- frontend/tailwind.config.ts planning/screens/_shared/style.css` → empty
- `git diff abef6c8..HEAD -- frontend/src/pages/Chat.tsx frontend/src/pages/Calendar.tsx frontend/src/index.css` → empty (0 lines)
- `git diff 9878236..HEAD -- frontend/src/pages/Schedule.tsx frontend/src/components/Sidebar.tsx` → empty (0 lines)
- 10 mockup × `grep -c "nav-toggle"` = 4 each = 40 instances ✓

---

## 12. Status & Next Action

- **Status**: 자동 검증 PASS (§2). manual section §3 + 후처리 §1.1 사용자 액션 대기.
- **Next action (사용자)**:
  1. §3.1 환경 셋업
  2. §6 체크리스트 8개 manual items 수행 + screenshot
  3. §3.2 표 결과 기입
  4. 본 보고서 commit (acceptance i)
  5. 메타-로드맵 §Phase 3 line 169 정정 commit (acceptance j)
- **Token regression 발견 시**: fix-forward commit (§4.1)
- **Mockup markup-only regression 발견 시**: 별도 fail-backlog spec 작성 후 본 phase 종료
