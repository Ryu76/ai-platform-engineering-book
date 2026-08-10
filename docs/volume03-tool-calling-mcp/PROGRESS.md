# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **Tool 실행 최소 감사 로그**
- 완료 선언: 아직 하지 않음. Volume 03의 MCP Server/Client, Resource/Prompt, STDIO, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: 원문 없는 구조화 감사 로그

- `src/ai_platform/tools/audit.py`
  - `ToolAuditEvent`는 요청 ID, Tool 이름, 위험도, 승인 ID, 결과만 가지는 최소 데이터 모델입니다. 원문 인자, Tool 결과, 예외 메시지, stack trace 필드가 없습니다.
  - `InMemoryToolAuditSink`는 외부 저장소·네트워크 없이 append-only 교육용 메모리에 이벤트를 기록하고, 호출자에게 수정 불가능한 tuple 스냅샷을 돌려줍니다.
  - `execute_audited()`는 handler를 직접 호출하지 않고 항상 기존 `execute_authorized()`를 통과합니다. allowlist·Schema·정책·승인 거부는 `DENIED`, 예상 밖 handler 오류는 `FAILED`, 정상 실행은 `SUCCEEDED`로 각각 한 번 기록합니다.
  - 거부 및 실패 이벤트도 원문 인자·결과·예외를 복사하지 않습니다. `approval_id`는 이 예제에서 인증 정보가 아닌 상관관계 식별자입니다.
- `src/ai_platform/tools/__init__.py`
  - 교육용 audit 경계의 공개 API를 export합니다.
- `examples/volume03/audited_tool_execution.py`
  - allowlist된 순수 `safe_text_case`를 고위험 Tool로 분류하고 고정 승인 기록으로 문자열 대문자 변환과 최소 감사 이벤트 하나만 시연합니다. 파일·셸·네트워크·환경 변수·실제 서비스에는 접근하지 않습니다.
- `tests/volume03/test_tool_audit.py`
  - 성공 이벤트의 최소 필드와 원문 비저장, 승인 누락의 handler 전 거부·기록, handler 실패와 권한 거부의 구분, immutable snapshot을 검증합니다.
- `docs/volume03-tool-calling-mcp/05-tool-audit-log.md`
  - 감사가 실행 권한이 아닌 이유, 최소 데이터 원칙, 오프라인 실습, 교육용 sink의 한계와 운영 환경의 변경 불가능·접근 제어 감사 저장소 요구사항을 문서화했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/audited_tool_execution.py
safe_text_case: AI PLATFORM
audit: request_id=audit-demo-request-001, tool=safe_text_case, risk=high, approval_id=audit-demo-approval-001, outcome=succeeded

$ uv run pytest tests/volume03/test_tool_audit.py -q
4 passed in 0.08s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 13 source files

$ uv run pytest -q
91 passed in 0.80s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv`는 Hermes 활성 가상환경과 프로젝트 `.venv`의 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 모든 명령을 정상 실행했습니다. 실제 LLM 호출, MCP 통신, 파일·시스템 변경, 외부 네트워크 요청은 수행하지 않았습니다.

## 다음 슬라이스

MCP 개념을 시작하기 위해 외부 MCP SDK나 실제 프로세스·네트워크 연결 없이, 명시적으로 등록된 순수 Tool 정의를 좁은 교육용 MCP Server catalog로 투영하는 첫 모델을 구현합니다. Tool allowlist와 JSON Schema를 유지하고 파일·셸·네트워크 도구는 등록하지 않습니다.
