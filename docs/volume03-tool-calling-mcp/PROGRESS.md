# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **실제 표준 입출력 없는 MCP STDIO JSON-RPC framing·initialize lifecycle adapter**
- 완료 선언: 아직 하지 않음. Volume 03의 실제 MCP STDIO transport wiring 및 Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: 한 줄 JSON-RPC와 initialize lifecycle을 실행 경계 밖에서 검증

- `src/ai_platform/mcp/stdio.py`
  - `parse_stdio_jsonrpc_line()`은 LF-종료 단일 UTF-8 JSON object, byte 상한, JSON-RPC `2.0`, non-empty method, string/integer ID, object params를 검증합니다.
  - 중복 JSON key와 `NaN`/`Infinity`를 거부하며 CRLF, LF 없는 입력, multiple frame을 받지 않습니다.
  - `McpStdioSession`은 고정 `2025-03-26` protocol version의 `initialize` request와 뒤따르는 ID·params 없는 `notifications/initialized`만 lifecycle으로 허용합니다.
  - initialize response도 compact JSON + LF와 byte 상한으로 재검증합니다. 실제 `sys.stdin`/`sys.stdout`, subprocess, network, Tool handler, dispatcher, audit sink를 사용하지 않으며 READY 뒤 method도 의도적으로 모두 거부합니다.
- `examples/volume03/mcp_stdio_lifecycle.py`
  - 고정된 offline initialize handshake 두 줄을 메모리에서 검증하고 `2025-03-26: ready`만 출력합니다.
- `tests/volume03/test_mcp_stdio.py`
  - 정상 handshake와 framed response, Tool method 미실행, 순서 밖 lifecycle, CRLF/multiple frame/중복 key/비표준 JSON-RPC envelope, UTF-8 byte limit, protocol version 불일치, closed session을 검증합니다.
- `docs/volume03-tool-calling-mcp/11-mcp-stdio-lifecycle.md`
  - 의도적으로 좁은 transport profile, framing·크기·lifecycle 계약, offline 실습, STDIO logging/EOF/error mapping 및 이후 dispatcher 연결 시 운영 경계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 열한 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_lifecycle.py
2025-03-26: ready

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 20 source files

$ uv run pytest -q
127 passed in 1.03s

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

모든 `uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 정상 실행했습니다. 실제 표준 입출력, MCP 통신, 파일·시스템 변경, 외부 네트워크 요청, 실제 destructive Tool 실행은 수행하지 않았습니다.

## 다음 슬라이스

STDIO adapter의 실제 process I/O wiring은 아직 열지 않고, READY 뒤의 고정 `tools/list` response를 별도 read-only adapter로 좁게 모델링합니다. JSON-RPC envelope와 `McpServerCatalog` projection만 연결하며 `tools/call`, dispatcher, handler, 파일·셸·네트워크 및 실제 destructive Tool은 계속 허용하지 않습니다.
