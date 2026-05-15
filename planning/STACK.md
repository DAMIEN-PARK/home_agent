# Tech Stack — home_agent

개인용 홈 어시스턴트. 메인 오케스트레이터 + 도메인별 서브에이전트 구조.
원칙: **로컬-퍼스트 · 개인 데이터 보호 · Claude 생태계 정합성 · 단순성 우선**.

---

## 레이어별 선택

| 레이어 | 선택 | 비고 |
|---|---|---|
| 에이전트 런타임 | **Claude Agent SDK (Python)** | 오케스트레이터·서브에이전트 모두 SDK로 구현. MCP·tool use 성숙 |
| 백엔드 API | **FastAPI** (Python 3.12+) | 에이전트와 동일 언어. async, OpenAPI 자동 생성 |
| **프론트엔드** | **React 18 + Vite + TypeScript** | 가볍게 시작. Tailwind + shadcn/ui · React Router · TanStack Query |
| **데이터베이스** | **PostgreSQL 16** | 관계형 우선. 벡터 검색은 `pgvector` 확장으로 같은 DB 안에서 처리 |
| ORM / 마이그레이션 | **SQLAlchemy 2.x + Alembic** | |
| 도메인 도구 연결 | **MCP 서버 per 도메인** | calendar / ledger / finance / notes / files / todo 각각 분리 |
| 인증 | (MVP) 로컬 토큰 | 가족 공유 시 OAuth 또는 Authelia로 확장 |
| 파일/사진 저장 | 로컬 파일시스템 (메타데이터만 Postgres) | 추후 객체 스토리지(S3 호환) 옵션 |
| 백그라운드 작업 | **APScheduler** → 규모 커지면 Celery+Redis | 일정 알림·정기 정산 등 |
| 로깅/관측성 | **structlog + OpenTelemetry** | 에이전트 호출 트레이싱 |

---

## 아키텍처 개요

```
┌──────────────────────────────────────────────────────────┐
│              React (Vite) SPA Frontend                    │
│         (chat UI, dashboards, settings)                   │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTPS / SSE (or WebSocket)
                         ▼
┌──────────────────────────────────────────────────────────┐
│                   FastAPI Backend                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │      Orchestrator Agent (Claude Agent SDK)         │  │
│  │   - routes user intent to subagents                │  │
│  │   - aggregates results                             │  │
│  └─────┬────────┬────────┬────────┬────────┬────────┘   │
│        ▼        ▼        ▼        ▼        ▼             │
│   schedule   ledger  finance  ideas    files   todo      │
│   agent     agent    agent   agent    agent   agent      │
│        │        │        │        │        │        │    │
│        ▼        ▼        ▼        ▼        ▼        ▼    │
│   MCP server per domain (calendar, ledger, …)            │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  PostgreSQL 16 +    │
              │  pgvector           │
              └─────────────────────┘
```

---

## 데이터 스키마 초안 (도메인별 스키마 분리)

PostgreSQL `SCHEMA` 단위로 도메인 격리:

- `schedule.*` — events, goals, visions
- `ledger.*` — transactions, categories, budgets
- `finance.*` — accounts, holdings, valuations
- `ideas.*` — notes, threads, tags
- `files.*` — file_meta, photo_meta, embeddings (`vector(1536)` 등)
- `todo.*` — tasks, projects, contexts
- `core.*` — users, sessions, agent_runs, audit_log
- `memory.*` — long-term agent memory (with `vector` column)

---

## 디렉터리 구조 (제안)

```
home_agent/
├── planning/          # 설계 문서
├── backend/
│   ├── app/
│   │   ├── api/       # FastAPI routers
│   │   ├── agents/    # orchestrator + subagents
│   │   ├── mcp/       # domain MCP servers
│   │   ├── db/        # SQLAlchemy models
│   │   └── core/      # config, logging, auth
│   ├── alembic/
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── pages/
    │   ├── components/
    │   ├── hooks/
    │   └── lib/
    ├── index.html
    ├── vite.config.ts
    └── package.json
```

---

## MVP 범위 후보 (다음 단계에서 확정)

1순위 후보 — **일정 + TODO** (가장 자주 쓰는 도메인, 외부 통합 없이 자체 데이터로 가치 입증)
2순위 — **가계부** (수기 입력만으로도 유용)
3순위 — **아이디어/문서 정리** (검색·요약이 핵심 가치)

---

## 미정 / 결정 필요

- [ ] 데스크톱 래핑 필요 여부 (Tauri / Electron)
- [ ] 인증: 1인용으로 시작 vs 처음부터 가족 공유
- [ ] 외부 캘린더(Google) 연동: MVP 포함 여부
- [ ] 배포: 로컬 머신 상주 vs 홈서버(Docker Compose) vs VPS
- [ ] 모바일 접근: PWA / 별도 RN 앱
