# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **전송 계층 없는 MCP Tool dispatcher (parser·allowlist·승인·timeout/retry·감사 결합)**
- 완료 선언: 아직 하지 않음. Volume 03의 MCP STDIO transport와 Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: 검증된 MCP Tool 호출을 제한된 실행 경계로 dispatch

- `src/ai_platform/mcp/dispatcher.py`
  - `dispatch_mcp_tool_call()`은 공백이 아닌 caller `request_id`와 raw JSON을 받고, parser와 `McpToolCallRequest.validate_against()`를 handler 전에 반드시 통과시킵니다.
  - 전송 framing·STDIO·HTTP·외부 MCP server를 구현하지 않으며 Resource/Prompt API를 Tool 실행에 연결하지 않습니다.
- `src/ai_platform/tools/authorization.py`
  - `authorize_request()`가 실행 없이 allowlist·Schema·위험도·request-bound 승인을 확인합니다.
  - `execute_authorized_with_policy()`는 승인 뒤에도 `execute_with_policy()`만 사용하므로 retry 시마다 registry 실행 경계로 다시 진입합니다.
- `src/ai_platform/tools/audit.py`
  - `execute_audited_with_policy()`가 원문 인자·결과·예외를 저장하지 않고 성공·거부·실패 한 건만 기록합니다.
  - 승인/allowlist/Schema 거부는 `denied`, timeout·retry 소진·handler 예외는 `failed`입니다.
- `examples/volume03/mcp_tool_dispatcher.py`
  - allowlisted `safe_text_case`의 고정 JSON 요청 하나만 offline dispatch합니다. 파일·셸·네트워크·외부 server·파괴적 Tool을 사용하지 않습니다.
- `tests/volume03/test_mcp_dispatcher.py`
  - retry 성공의 단일 감사 기록, 고위험 승인 거부의 handler 미호출, timeout의 `failed` 감사 기록, 불완전 transport intent의 handler/audit 미진입을 검증합니다.
- `docs/volume03-tool-calling-mcp/10-mcp-tool-dispatcher.md`
  - 순서화된 dispatcher 계약, 오프라인 실습, Python thread timeout 한계와 운영 transport 경계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 열 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_tool_dispatcher.py
safe_text_case: MCP (succeeded)

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 19 source files

$ uv run pytest -q
114 passed in 0.88s

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

`uv`는 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 모든 명령을 정상 실행했습니다. 실제 LLM 호출, MCP 통신, 파일·시스템 변경, 외부 네트워크 요청은 수행하지 않았습니다.

## 다음 슬라이스

MCP STDIO transport를 별도 adapter로 좁게 모델링합니다. dispatcher에 임의 transport metadata를 섞지 않고, JSON-RPC framing·메시지 크기·protocol version·입출력 lifecycle을 검증합니다. 파일·셸·네트워크 및 실제 destructive Tool은 계속 허용하지 않습니다.
