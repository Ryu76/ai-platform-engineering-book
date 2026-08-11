# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO READY state의 고정 allowlisted `resources/read` text snapshot projection**
- 완료 선언: 아직 하지 않음. 실제 STDIO process I/O wiring, error/EOF policy, 검토된 `tools/call` dispatcher 연결, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: handshake 뒤 고정 Resource 하나만 경로 해석 없이 조회

- `src/ai_platform/mcp/stdio.py`
  - `McpStdioSession`은 기존 한 줄 JSON-RPC framing·고정 initialize lifecycle 뒤 `tools/list`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get` request만 받습니다.
  - `resources/read`는 request ID와 exact allowlisted `uri` 하나만 검증하고 `McpResourceCatalog.read_resource()`의 고정 `text/plain` snapshot을 MCP `contents` result envelope로 투영합니다.
  - notification, URI 누락·공백, alias, `file:///...`, extra params와 미등록 URI는 거부합니다. URI 정규화·path 해석, loader, dispatcher, 승인, retry, audit, 실제 process I/O, 파일·셸·네트워크는 호출하지 않습니다.
- `examples/volume03/mcp_stdio_resources_read.py`
  - 코드에 명시한 정적 `ai-platform://volume03/transport-boundary` Resource로 메모리 JSON-RPC handshake와 `resources/read`을 확인하고 `ai-platform://volume03/transport-boundary: fixed snapshot`만 출력합니다.
- `tests/volume03/test_mcp_stdio.py`
  - fixed Resource snapshot response와 READY state 유지, request ID 없는 notification, URI 누락, alias, file URI, extra param 거부를 검증합니다.
- `docs/volume03-tool-calling-mcp/16-mcp-stdio-resources-read.md`
  - 좁은 request/response 계약, `contents` envelope, static snapshot과 동적 loader를 분리하는 이유, offline 실습, rejection, 운영 loader 경계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 열여섯 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_resources_read.py
ai-platform://volume03/transport-boundary: fixed snapshot

$ uv run pytest tests/volume03/test_mcp_stdio.py -q
37 passed in 0.17s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 20 source files

$ uv run pytest -q
151 passed in 0.96s

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

실제 process I/O는 계속 열지 않고, READY 뒤 검토된 `tools/call` request를 기존 `McpToolCallRequest` parser와 dispatcher에 연결할 수 있는지 별도 adapter로 좁게 모델링합니다. request envelope, allowlist·Schema 재검증, 승인/timeout/retry/audit 결과 projection과 JSON-RPC error policy를 명시하며, handler가 실제 destructive action을 하지 않는 allowlisted pure Tool만 사용합니다.
