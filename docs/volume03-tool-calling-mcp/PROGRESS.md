# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO READY state의 explicit boundary 기반 allowlisted `tools/call` projection**
- 완료 선언: 아직 하지 않음. 실제 STDIO process I/O wiring, EOF/error policy, Hermes/Codex 연동과 전체 운영 DoD를 구현·문서화·검증해야 합니다.

## 이번 슬라이스: explicit 실행 경계가 있을 때만 순수 Tool 하나를 dispatcher로 연결

- `src/ai_platform/mcp/stdio.py`
  - `McpToolCallBoundary`는 host가 구성한 `ToolRegistry`, 위험도 정책, timeout/retry 정책, 최소 audit sink와 선택적인 trusted approval만 묶습니다. caller JSON은 handler, policy, approval, timeout, audit sink를 공급할 수 없습니다.
  - `McpStdioSession`은 기존 handshake 뒤 `tools/call`을 기본적으로 거부하며, explicit boundary가 있을 때에만 transport `params`를 compact JSON으로 재구성해 기존 `parse_mcp_tool_call_request()`와 `dispatch_mcp_tool_call()`에 전달합니다.
  - string/integer JSON-RPC ID는 각각 `mcp-stdio:string:<id>` / `mcp-stdio:integer:<id>` audit ID가 되어 충돌하지 않습니다. success output은 최대 4,096 UTF-8 byte의 JSON text content로만 투영합니다.
  - Tool parser·allowlist·Schema·approval·timeout/retry·handler·output projection 실패는 원문 인자·예외·정책 detail을 포함하지 않는 고정 `isError: true` MCP Tool result로 반환합니다. malformed framing/lifecycle/notification/no-boundary는 실행 전에 `McpStdioError`로 거부합니다.
- `src/ai_platform/mcp/__init__.py`
  - `McpToolCallBoundary`를 Volume 03 MCP public export에 추가했습니다.
- `examples/volume03/mcp_stdio_tools_call.py`
  - in-memory handshake 뒤 코드에 allowlist한 순수 `SAFE_TEXT_CASE`의 고정 upper-case request 하나만 호출하고 `safe_text_case: MCP`를 출력합니다.
- `tests/volume03/test_mcp_stdio.py`
  - pure Tool success projection과 audit correlation, boundary 없는 default rejection, parser/allowlist 전 거부의 no-audit, handler error의 fixed result 및 failed audit을 검증합니다.
- `docs/volume03-tool-calling-mcp/17-mcp-stdio-tools-call.md`
  - explicit boundary 계약, success/error result policy, output size limit, offline exercise, rejection과 운영 transport 경계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 열일곱 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_tools_call.py
safe_text_case: MCP

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 20 source files

$ uv run pytest tests/volume03/test_mcp_stdio.py -q
41 passed in 0.23s

$ uv run pytest -q
155 passed in 1.16s

$ git diff --check
(exit 0)
```

모든 `uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 정상 실행했습니다. 실제 `sys.stdin`/`sys.stdout`, filesystem, shell, subprocess, network, 외부 MCP server, 실제 destructive Tool은 사용하지 않았습니다. 테스트의 failure handler는 외부 부작용 없이 예외만 발생시키고, 예제 Tool은 문자열 변환만 수행합니다.

## 다음 슬라이스

실제 외부 service나 destructive Tool을 열지 않고, 명시적 boundary의 JSON-RPC request ID와 approval correlation을 더 좁게 검증할 수 있는 standalone validation slice를 검토합니다. 실제 STDIO process I/O, EOF/error response, cancellation, durable audit, Hermes/Codex integration은 별도 설계·문서·테스트가 필요하며 이 교육용 in-memory adapter에 무분별하게 추가하지 않습니다.
