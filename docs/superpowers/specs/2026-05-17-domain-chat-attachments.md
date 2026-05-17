# 도메인 챗 파일첨부 → files 파이프라인 routing

**작성일**: 2026-05-17
**작성자**: damien (with Claude)
**상태**: draft
**선행 spec**: [`docs/superpowers/specs/2026-05-16-orchestrator-domain-subagents.md`](2026-05-16-orchestrator-domain-subagents.md) (#7)
**관련 mockup**: `planning/screens/ledger.html`(+영수증), `ideas.html`(+노트), `finance.html`(+보유), `files.html`(⤴ 업로드)

---

## 1. 목표

도메인 챗의 `+ 영수증 / + 노트 / + 보유 / ⤴ 업로드` 버튼이 일관된 백엔드 경로로 동작.

흐름:
1. 사용자가 도메인 챗(e.g. `ledger`)에 메시지 + 영수증.jpg 첨부 전송
2. 백엔드는 files 파이프라인에 파일을 등록(`files.attachments` row + 디스크 저장) → 파일 ID 반환
3. 해당 도메인 agent의 `run_turn`이 메시지 + 첨부 파일 메타+raw bytes를 받음
4. 도메인 agent가 LLM 호출 시 Claude vision 입력으로 첨부 이미지를 inline 포함
5. LLM이 영수증 텍스트 인식 → `ledger.add_transaction` tool_call → 거래 생성
6. 사용자에게 응답 + tool trace

비목표 (v1 외):
- OCR pipeline 단독 단계 (LLM vision으로 흡수)
- 자동 태깅 / 의미검색 (`files_agent`는 여전히 저장만)
- 외부 스토리지 (MinIO/S3)
- 대용량(>20MB) 업로드 / 파일 청크 업로드
- 영상/음성 처리 (이미지 + PDF/text만)

## 2. 결정 사항 (사용자 답)

| 항목 | 결정 |
|---|---|
| files 도메인 v1 | 저장 + 메타 등록만. OCR/태깅은 도메인 agent가 LLM에 위임 |
| 저장 위치 | 로컬 디스크 `data/files/` |
| 업로드 API | `POST /chat/{domain}` multipart 확장 (text + files 한 요청) |
| OCR | Claude vision (도메인 agent의 LLM 호출에 이미지 inline) |

## 3. 데이터 모델

신규 `files.attachments`:

```python
class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"
    __table_args__ = {"schema": "files"}

    id: Mapped[UUID]                     # PK, uuid4
    user_id: Mapped[UUID]                 # FK core.users
    session_id: Mapped[UUID | None]      # FK core.sessions (업로드 컨텍스트)
    path: Mapped[str]                    # data/files/<sha256>.<ext>
    sha256: Mapped[str]                  # 64 hex chars (중복 dedup용)
    original_name: Mapped[str]
    mime_type: Mapped[str]               # image/jpeg, application/pdf, text/plain
    size_bytes: Mapped[int]
```

`files` 스키마는 0001에 이미 생성되어 있으면 그대로 사용, 없으면 0006에서 함께 추가.

Migration `0006_files_attachments.py`:
- CREATE SCHEMA IF NOT EXISTS files
- CREATE TABLE files.attachments
- INDEX ix_files_attachments_user (user_id)
- INDEX ix_files_attachments_sha256 (sha256) — dedup 조회용 (UNIQUE 아님: per-user dedup는 정책 결정 후)

## 4. 저장 레이어 / FilesAgent 풀구현

`files_agent.py`는 더 이상 StubAgent 인스턴스가 아니라 풀 클래스:

```python
class FilesAgent:
    name = "files"
    tools = FILES_TOOLS

    async def save_attachment(
        self, session, *, user, raw: bytes, original_name: str, mime: str,
        session_id: UUID | None = None,
    ) -> Attachment:
        """파일 디스크 저장 + 메타 row 생성. 이미 같은 sha256이 있으면 메타만 추가."""

    async def get_attachment_bytes(self, session, *, user, attachment_id: UUID) -> tuple[bytes, str]:
        """파일 ID → (raw, mime). 권한: user_id 일치 확인."""

    async def handle_tool(...):
        # tool 일부만 풀구현 — files.search_files는 stub 유지 (v1)
        # 새 tool: files.list_recent
```

저장 정책:
- 경로 `data/files/<sha256[:2]>/<sha256>.<ext>` (2자 디렉토리 fan-out)
- ext는 mime 기반 매핑 (없으면 `bin`)
- 같은 user + 같은 sha256은 dedup: 같은 path 재사용, 메타 row만 새로 추가 (history 보존)

## 5. API 변경

`POST /chat` 과 `POST /chat/{domain}`을 multipart 우선 + JSON 폴백:

```python
@router.post("/{domain}")
async def post_domain_chat(
    domain: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    ...
):
    ct = request.headers.get("content-type", "")
    if ct.startswith("multipart/"):
        form = await request.form()
        message = form["message"]
        user_id = UUID(form["user_id"])
        files = form.getlist("attachments")   # list of UploadFile
    else:
        body = await request.json()
        message = body["message"]
        user_id = UUID(body["user_id"])
        files = []
    ...
```

이유: 기존 테스트(application/json)와 호환 + 첨부가 없는 도메인 챗도 그대로.

## 6. 도메인 agent 인터페이스 변경

`DomainAgent.run_turn`에 `attachments: list[Attachment]` 추가:

```python
async def run_turn(
    self, session, *, user, session_id, user_message,
    recent_messages: list[dict],
    attachments: list[Attachment] = [],
) -> dict: ...
```

stub agent (`StubAgent.run_turn`)는 첨부 무시 + 동일 placeholder.

풀구현 agent (`ScheduleAgent`, `TodoAgent`, 그리고 v1에 추가될 `LedgerAgent` 일부)는 LLM 메시지 구성 시 첨부를 vision content block으로 변환:

```python
def _build_user_message(text: str, attachments: list[Attachment]) -> dict:
    if not attachments:
        return {"role": "user", "content": text}
    content = [{"type": "text", "text": text}]
    for att in attachments:
        if att.mime_type.startswith("image/"):
            raw = read_bytes(att.path)
            b64 = base64.b64encode(raw).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": att.mime_type, "data": b64},
            })
        else:
            # PDF/text는 텍스트 추출 라이브러리로 → text block
            content.append({"type": "text", "text": extract_text(att)})
    return {"role": "user", "content": content}
```

`call_llm` wrapper도 multimodal content를 그대로 통과시키도록 변경.

## 7. 메시지 영속화

`_persist_turn` 확장 — user 메시지의 `extra`에 `attachment_ids` 저장:

```python
db.add(Message(
    session_id=sess.id, role="user", content=user_message,
    extra={"attachment_ids": [str(a.id) for a in attachments]} if attachments else None,
))
```

이렇게 하면 후속 cross-domain context에서 사용자가 어떤 파일 보냈는지 추적 가능 (현재 stage는 그 파일 다시 첨부하진 않고 ID만 기록).

## 8. v1 구현 범위 — 도메인별 동작

| 도메인 | 첨부 동작 |
|---|---|
| `ledger` | **Stub 졸업** — vision으로 영수증 인식 + `ledger.add_transaction` 제안. 단 ledger CRUD 자체는 다음 spec |
| `ideas` | Stub 졸업 — 이미지/텍스트를 노트 본문으로 생성 (`ideas.create_note` 호출) |
| `files` | 자기 자신 — 단순 저장 + "n개 파일 등록됨" 응답 |
| `finance` | Stub 그대로 — 첨부 받아도 placeholder |
| `schedule` | 첨부 무시 — (캘린더 초대 .ics 같은 future) |
| `todo` | 첨부 무시 — (스크린샷에서 TODO 추출 같은 future) |

즉 ledger/ideas/files만 첨부를 의미 있게 처리하고, 나머지는 데이터만 받아두고 무시.

## 9. 테스트 전략

- **단위**: `FilesAgent.save_attachment` — 동일 sha256 dedup, mime ext 매핑, 경로 fan-out
- **단위**: `_build_user_message` — image/pdf/text → content blocks 변환
- **통합**: `POST /chat/ledger` multipart with 영수증 jpg → 저장 row 생성 + LLM mock에서 vision content 받았는지
- **통합**: `POST /chat/files` multipart with 2개 파일 → 2개 row + "2개 파일 등록됨" 응답
- **마이그레이션**: alembic 0006 upgrade/downgrade

## 10. 미해결

- 첨부 파일의 권한 모델 (현재 user_id 일치만). 가족 공유 시 별도.
- dedup 정책 — 동일 sha256 다른 user 간 공유? v1은 user_id 안에서만 dedup.
- 대용량 / 청크 업로드 — multipart 단일 요청 한계 (uvicorn 기본 4MB? FastAPI는 메모리에 다 올림). 20MB 이하만 받기로.
- PDF/문서 vision 처리 — Claude는 PDF 직접 지원하지만 raw bytes inline이 토큰 비용 큼. v1은 PDF는 텍스트 추출 후 text block.
- ideas 도메인 노트 생성을 위해서는 ideas의 데이터 모델/서비스 레이어가 선행. ideas 졸업은 별도 spec.

## 11. 구현 순서

1. **0006 migration** — files.attachments
2. **`Attachment` model + `__init__.py` export**
3. **`FilesAgent` 풀구현** — save_attachment, get_attachment_bytes, files.list_recent tool 추가, run_turn 풀구현 (단순 등록 응답)
4. **`DomainAgent.run_turn` 시그니처에 `attachments` 추가** — base.py StubAgent도 갱신
5. **`_build_user_message` 헬퍼** — base.py에 추가, PDF 추출은 pypdf 의존성 추가
6. **`ScheduleAgent.run_turn` / `TodoAgent.run_turn` / `LedgerAgent`(stub 졸업)에 attachments 처리** — schedule/todo는 그냥 첨부를 무시(empty list로 처리), ledger는 vision content 포함
7. **`api/chat.py` multipart 분기** — Request.headers content-type 검사 + 양쪽 입력 처리
8. **`_persist_turn` extra에 attachment_ids** 저장
9. **테스트 — 단위 + 통합**
10. **mockup 의 `+ 영수증/+ 노트/⤴ 업로드` 버튼 → 프론트 구현은 별도 작업** (이 spec은 backend만)

## 12. 후속 spec 후보

- `ledger` 도메인 풀구현 (categories, transactions, budget) — ledger agent의 vision 응답이 의미 있으려면 필수
- `ideas` 도메인 풀구현 (notes, tags, embedding) — note 생성을 backend가 진짜로 처리하려면
- `files.search_files` (의미 검색) — 임베딩 도입 spec
