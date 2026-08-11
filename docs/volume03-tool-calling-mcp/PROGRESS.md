# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO `tools/call`의 typed JSON-RPC ID 기반 high-risk approval correlation**
- 완료 선언: 아직 하지 않음. 실제 STDIO process I/O wiring, EOF/error policy, Hermes/Codex 연동과 전체 운영 DoD를 구현·문서화·검증해야 합니다.

## 이번 슬라이스: trusted approval을 typed JSON-RPC request ID까지 묶기

- `src/ai_platform/mcp/stdio.py`
  - public `mcp_stdio_request_correlation_id()`는 trusted host가 `ApprovalGrant`와 dispatcher에서 같은 typed correlation ID를 사용하게 합니다. string ID `"7"`과 integer ID `7`은 서로 다른 request binding입니다.
  - parser와 helper는 빈 string, boolean, float, ASCII control character를 ID로 거부합니다. 제어 문자가 audit/approval 기록의 줄 경계를 바꾸지 못합니다.
  - `McpToolCallBoundary`는 caller JSON이 아닌 host가 제공한 policy·approval만 사용합니다. HIGH Tool은 ID·Tool·canonical arguments가 모두 일치할 때만 기존 allowlist·Schema·timeout/retry·audit dispatcher에 도달합니다.
- `src/ai_platform/tools/authorization.py`
  - approval canonicalization은 immutable `Mapping` snapshot도 plain JSON object로 복사해 비교하므로 MCP parser의 immutable arguments가 valid approval match를 막지 않습니다.
- `src/ai_platform/mcp/__init__.py`
  - public correlation helper를 Volume 03 MCP export에 추가했습니다.
- `examples/volume03/mcp_stdio_approved_tools_call.py`
  - host 코드가 fixed string JSON-RPC ID, pure Tool, fixed arguments로 교육용 approval을 만들고 in-memory `HIGH` Tool request 한 번만 실행해 `approved_safe_text_case: MCP`를 출력합니다.
- `tests/volume03/test_mcp_stdio.py`
  - typed ID에 바인딩된 HIGH pure Tool success, same-looking integer/string ID mismatch denial, non-canonical ID helper rejection을 검증합니다.
- `docs/volume03-tool-calling-mcp/18-mcp-stdio-approval-correlation.md`
  - trusted host approval correlation, typed ID separation, immutable arguments canonicalization, offline exercise와 운영 approval 한계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 열여덟 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_approved_tools_call.py
approved_safe_text_case: MCP

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 20 source files

$ uv run pytest tests/volume03/test_mcp_stdio.py tests/volume03/test_tool_authorization.py -q
53 passed in 0.23s

$ uv run pytest -q
161 passed in 1.20s

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

모든 `uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 정상 실행했습니다. 실제 `sys.stdin`/`sys.stdout`, filesystem, shell, subprocess, network, 외부 MCP server, 실제 destructive Tool은 사용하지 않았습니다.

## 다음 슬라이스

실제 STDIO process loop를 열지 않고, `receive_line()` adapter를 process I/O wiring으로 옮길 때 EOF·write failure·JSON-RPC error response를 어떻게 안전하게 분리할지 다음 작은 slice에서 모델링합니다. 실제 external Tool, cancellation, durable audit, Hermes/Codex integration은 계속 별도 설계·문서·테스트가 필요합니다.
