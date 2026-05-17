---
created: 2026-05-16
tags: [architecture, lan, device, cors, frontend, backend]
aliases: [LAN 디바이스 아키텍처, 가정 내 멀티 디바이스]
---

# LAN & 디바이스 아키텍처

> 가정 LAN 안에서 여러 디바이스가 home_agent를 공유하되, 디바이스별로 채팅이 분리되도록 하는 결정과 구현 기록.

## 1. 문제 정의

home_agent는 "헤드리스인가?"라는 질문에서 출발.

- 결론: **헤드리스 아님.** React 프론트 + FastAPI 백엔드 + Postgres + APScheduler로 구성된 풀스택.
- 다만 일부 컴포넌트(스케줄러, 서브에이전트)는 헤드리스 성격(자체 UI 없음).

추가로 정리된 사용 시나리오:
- 집 안 LAN에서 여러 기기(데스크탑, 노트북 A, 노트북 B)가 같이 사용.
- 외부 노출 ❌. 외부에서는 Todoist / Google Calendar OAuth 연동으로만 다리.
- 외부 조회는 필요하면 **Claude Code 원격 컨트롤**로 집 컴퓨터에 붙어서 처리 (별도 API 노출 불필요).

## 2. 인증 & 식별 모델 결정

| 항목 | 결정 |
|---|---|
| 사용자 인증 | **없음.** 단일 사용자(나) 가정. 와이프는 가끔 옆에서 같이 보는 정도. |
| 외부 노출 | ❌ 안 함 |
| 디바이스 식별 | localStorage의 `device_id` (UUID, 자동 발급) + 사용자가 직접 입력하는 `device_name` |
| CORS | LAN IP/`*.local`까지 허용하는 정규식 |
| 채팅 분리 단위 | **디바이스별 분리.** 데스크탑에서 한 대화와 노트북 대화는 별개. |

### 외부 서비스 연동 방식

| 서비스 | 방식 |
|---|---|
| Anthropic Claude | API 키 (`ANTHROPIC_API_KEY`) |
| Google Calendar | OAuth 2.0 (client_id + secret + refresh_token) |
| Todoist | OAuth (예정 — schedule/Google Calendar와 동형 패턴) |

## 3. 데이터 모델 영향

`core.sessions` 테이블에 디바이스 추적 컬럼 추가.

```python
# backend/app/db/models/core.py
class Session(Base, TimestampMixin):
    ...
    device_id: Mapped[UUID | None]      # localStorage UUID
    device_name: Mapped[str | None]     # 사용자 설정 이름
```

Migration: `backend/alembic/versions/0004_session_device_columns.py`
- `device_id` (UUID, nullable), `device_name` (String(120), nullable)
- `ix_core_sessions_device_id` 인덱스

> 사용자 분리는 추가 안 함. 모두 같은 `user_id`(개인 어시스턴트 1인) 아래에서 `device_id`로 스레드만 가른다.

## 4. 백엔드 변경 요약

### `app/core/config.py`
```python
cors_origin_regex: str | None = Field(
    default=r"^http://(localhost|127\.0\.0\.1"
            r"|192\.168\.\d{1,3}\.\d{1,3}"
            r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|[a-zA-Z0-9-]+\.local):(5173|8000)$"
)
```

### `app/main.py`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### `app/api/chat.py`
- `X-Device-Id`, `X-Device-Name` 헤더 수용
- `run_turn(..., device_id=, device_name=)`로 orchestrator에 전달
- orchestrator는 키워드 인자 받아서 추후 Session 생성 시 사용

### 환경 변수
- `.env.example` / `docker-compose.yml`에 `CORS_ORIGIN_REGEX` 추가
- uvicorn은 docker에서 이미 `--host 0.0.0.0`
- vite도 Dockerfile에서 이미 `--host 0.0.0.0`

## 5. 프론트엔드 변경 요약

### `lib/device.ts`
- `getDeviceId()` — localStorage `home-agent.device-id` 자동 발급 (없으면 `crypto.randomUUID()`)
- `getDeviceName()` / `setDeviceName()` / `clearDeviceName()` — `home-agent.device-name`

### `lib/api.ts`
- 모든 요청에 `X-Device-Id` + (있으면) `X-Device-Name` 헤더 자동 첨부
- `postChat`/`getEvents` 시그니처는 그대로 유지 → 기존 vitest 테스트 영향 없음

### `components/DeviceSetup.tsx`
- 첫 방문 시 이름 입력 모달
- "데스크탑", "노트북-거실" 같은 사람이 알아볼 이름 받음
- 하단에 디버그용 device_id 표시

### `App.tsx`
- `getDeviceName()`이 비어있으면 `<DeviceSetup>` 게이트 표시
- 이름 저장되면 라우터 정상 표시

## 6. 디바이스 접속 방법 (실사용)

```
[집 공유기]
   데스크탑 ──┐
   노트북 A ──┼──→ http://192.168.x.x:5173 (React)
   노트북 B ──┘                  ↓
                       http://192.168.x.x:8000 (FastAPI)
```

첫 접속 시:
1. 브라우저에서 LAN IP 또는 mDNS 호스트명(`http://home-agent.local:5173`)으로 접속
2. 기기 이름 입력 모달 → "노트북-거실" 등 입력
3. localStorage에 `device_id` 자동 생성, `device_name` 저장
4. 이후 모든 요청에 헤더 첨부되어 디바이스별 채팅 분리

## 7. 외부 다리 (집 밖에서)

- **Todoist / Google Calendar**: 외부에서 입력 → 집 백엔드 APScheduler 15분 동기화로 흡수
- **Claude Code 원격 컨트롤**: 집 PC에서 home_agent 폴더로 claude session 띄워두면, 외부에서 그 세션에 붙어 DB 조회 가능 (별도 API 노출 없이)

## 8. 향후 결정해야 할 것 (미해결)

- [ ] 채팅 세션 목록 API/UI (현재는 단일 세션, 디바이스별 히스토리 조회는 미구현)
- [ ] 디바이스 이름 변경 화면 (현재는 localStorage 직접 지우거나 코드로만 가능)
- [ ] Todoist OAuth 연동 (schedule 패턴 동형으로 진행 예정)
- [ ] 외부 접근 필요해지면 Tailscale 등 VPN 도입 검토

## 9. 관련 파일

```
backend/
  app/core/config.py              ← cors_origin_regex
  app/main.py                     ← CORSMiddleware
  app/db/models/core.py           ← Session.device_id, device_name
  app/api/chat.py                 ← X-Device-Id / X-Device-Name 헤더
  app/agents/orchestrator.py      ← run_turn에 device 인자
  alembic/versions/0004_session_device_columns.py
  .env.example                    ← CORS_ORIGIN_REGEX

frontend/
  src/lib/device.ts               ← localStorage 헬퍼
  src/lib/api.ts                  ← 헤더 자동 첨부
  src/components/DeviceSetup.tsx  ← 첫 방문 입력 모달
  src/App.tsx                     ← 게이트

docker-compose.yml                ← CORS_ORIGIN_REGEX 환경 변수
```

## 10. 미해결 검증

이 세션 종료 시점에 로컬 typecheck/test 실행을 시도했으나:
- 호스트에 `node_modules` / Python venv 없음 → 명령 자체가 실패 (`tsc not found`)
- 검증은 **docker-compose up** 또는 venv/node_modules 설치 후 다시 실행 필요

검증 명령:
```bash
# 도커로
docker compose up --build
docker compose exec backend alembic upgrade head

# 또는 로컬
cd backend && pip install -e . && python -c "from app.main import create_app; create_app()"
cd frontend && npm install && npm run typecheck && npm test -- --run
```
