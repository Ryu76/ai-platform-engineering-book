# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO READY state의 read-only `tools/list` catalog projection**
- 완료 선언: 아직 하지 않음. 실제 STDIO process I/O wiring, error/EOF policy, `tools/call` transport adapter와 검토된 dispatcher 연결, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: handshake 뒤 allowlisted Tool catalog만 조회

- `src/ai_platform/mcp/stdio.py`
  - `McpStdioSession`은 기존 한 줄 JSON-RPC framing·고정 initialize lifecycle 뒤 `tools/list` request만 받습니다.
  - catalog는 `McpServerCatalog` snapshot만 response의 `result.tools`로 투영합니다. request ID는 필수이고 params는 없거나 빈 object여야 합니다.
  - `tools/call`, unknown method, `tools/list` notification, non-empty params는 거부합니다. handler, dispatcher, 승인, retry, audit, 실제 process I/O, 파일·셸·네트워크는 호출하지 않습니다.
- `examples/volume03/mcp_stdio_tools_list.py`
  - 코드에 명시한 `SAFE_CALCULATOR` 및 `SAFE_TEXT_CASE`로 만든 catalog를 메모리 JSON-RPC handshake와 `tools/list`로 확인하고 `safe_calculator, safe_text_case: listed`만 출력합니다.
- `tests/volume03/test_mcp_stdio.py`
  - fixed catalog response 및 READY state 유지, request ID 없는 notification, non-empty params, `tools/call` 거부를 검증합니다.
- `docs/volume03-tool-calling-mcp/12-mcp-stdio-tools-list.md`
  - 좁은 response 계약, catalog와 execution 분리, offline 실습, errors, 운영 시 pagination/auth/rate limits 및 dispatcher 재진입 경계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 열두 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_tools_list.py
safe_calculator, safe_text_case: listed

$ uv run pytest tests/volume03/test_mcp_stdio.py -q
17 passed in 0.20s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 20 source files

$ uv run pytest -q
131 passed in 1.09s

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

모든 `uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 정상 실행했습니다. `validate_docs.py`는 기존 validator가 보고한 Volume 11개를 출력했으나 새 문서의 링크·코드 블록 검증은 통과했습니다. 실제 표준 입출력, MCP 통신, 파일·시스템 변경, 외부 네트워크 요청, 실제 destructive Tool 실행은 수행하지 않았습니다.

## 다음 슬라이스

실제 process I/O는 계속 열지 않고, READY 뒤 고정 `resources/list` response를 별도 read-only adapter로 좁게 모델링합니다. JSON-RPC envelope와 `McpResourceCatalog` projection만 연결하며 `resources/read`, `tools/call`, dispatcher, handler, 파일·셸·네트워크 및 실제 destructive Tool은 계속 허용하지 않습니다.
