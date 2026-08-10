# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **Tool 권한·사람 승인 경계**
- 완료 선언: 아직 하지 않음. Volume 03의 실행 감사 로그, MCP Server/Client, Resource/Prompt, STDIO, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: 위험도와 사람 승인

- `src/ai_platform/tools/authorization.py`
  - `ToolAuthorizationPolicy`는 allowlisted Tool마다 `LOW` 또는 `HIGH` 위험도를 명시하게 하며, 미지정 Tool의 기본 허용을 거부합니다.
  - `execute_authorized()`는 승인 확인보다 먼저 `ToolRegistry.validate_request()`를 호출하고 마지막에도 `ToolRegistry.execute()`로만 실행합니다. 승인 기록은 allowlist·JSON Schema 검증 또는 handler 직접 호출을 우회할 수 없습니다.
  - `HIGH` Tool은 `ApprovalGrant`가 요청 ID, Tool 이름, 정규화된 JSON 인자에 모두 일치할 때만 실행합니다. 승인 누락·요청 ID 재사용·인자 변경은 handler 전에 거부됩니다.
  - `ApprovalGrant`는 신뢰된 승인 워크플로의 기록을 모사하는 순수 교육용 객체입니다. 자체적으로 사람 신원·서명·만료·단회 사용을 증명하지 않습니다.
- `src/ai_platform/tools/registry.py`
  - 실행하지 않는 `validate_request()`를 추가해 권한 경계도 같은 registry allowlist·Schema 계약을 handler 전에 재사용합니다.
- `examples/volume03/approved_tool_execution.py`
  - allowlist된 순수 `safe_text_case`를 교육용 `HIGH` Tool로 분류해 고정 승인 기록 뒤 문자열 소문자 변환만 시연합니다. 파일·셸·네트워크·환경 변수·실제 서비스에는 접근하지 않습니다.
- `tests/volume03/test_tool_authorization.py`
  - 일치한 고위험 승인 성공, 승인 누락, 요청 ID·인자 불일치, allowlist·Schema 우회 불가, 저위험 실행 및 정책 누락 거부를 검증합니다.
- `docs/volume03-tool-calling-mcp/04-tool-authorization-approval.md`
  - 검증과 승인의 순서, 오프라인 실습, 교육용 승인 객체의 보안 한계, 운영 환경에서 필요한 인증·감사·만료·단회 사용 조건을 문서화했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/approved_tool_execution.py
safe_text_case: ai platform (approved demo)

$ uv run pytest tests/volume03/test_tool_authorization.py -q
6 passed in 0.11s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 12 source files

$ uv run pytest -q
87 passed in 0.84s

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

Tool 실행의 구조화된 감사 로그를 순수한 in-memory sink로 구현합니다. 요청 ID·Tool 이름·위험도·승인 ID·성공/거부 결과를 최소 데이터로 남기되, 원문 인자나 비밀값을 로그에 기록하지 않고 allowlist·Schema·승인 경계를 우회하지 않게 합니다.
