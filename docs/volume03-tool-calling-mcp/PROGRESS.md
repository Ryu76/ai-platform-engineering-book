# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO injected stream runner의 EOF·transport failure·안전한 JSON-RPC error 경계**
- 완료 선언: 아직 하지 않음. 실제 subprocess host lifecycle, OS pipe backpressure, cancellation/signal, durable audit/idempotency, Hermes/Codex 연동과 전체 운영 DoD를 구현·문서화·검증해야 합니다.

## 이번 슬라이스: injected stream으로 STDIO session을 EOF까지 안전하게 구동하기

- `src/ai_platform/mcp/stdio.py`
  - `run_mcp_stdio_session()`은 `sys.stdin`/`sys.stdout`을 직접 열지 않고 trusted host가 전달한 text input/output stream만 한 line씩 연결합니다.
  - EOF는 session close와 최소 aggregate `McpStdioRunStats` 반환으로 끝납니다. input read, output write/flush, partial write 실패는 `McpStdioTransportError`와 session close로 끝나며 같은 response/error를 재시도하지 않습니다.
  - session의 framing·lifecycle 오류는 raw input·예외 상세·Tool input을 노출하지 않는 고정 JSON-RPC `-32600` response로 분리합니다. duplicate key 없이 파싱되고 canonical string/integer ID인 경우에만 ID를 echo하며, 모호하거나 error envelope 크기를 넘기는 ID는 `null`로 fallback합니다.
- `src/ai_platform/mcp/__init__.py`
  - stream runner, transport error, aggregate stats를 Volume 03 MCP public export에 추가했습니다.
- `examples/volume03/mcp_stdio_injected_stream_runner.py`
  - `io.StringIO`에 고정 initialize/initialized/invalid request만 넣어 response count와 fixed error code를 출력합니다.
- `tests/volume03/test_mcp_stdio.py`
  - injected stream의 handshake·notification·invalid request·EOF, `null` ID fallback과 error-detail non-disclosure, write failure single-attempt, input read failure session close를 검증합니다.
- `docs/volume03-tool-calling-mcp/19-mcp-stdio-stream-runner.md`
  - stream ownership, EOF/read/write policy, safe error envelope, partial write 정책, offline exercise와 운영 한계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 열아홉 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_injected_stream_runner.py
responses_written: 2
invalid_request_code: -32600
invalid_request_id: invalid-001

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 20 source files

$ uv run pytest tests/volume03/test_mcp_stdio.py -q
51 passed in 0.37s

$ uv run pytest -q
165 passed in 1.15s

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

모든 `uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 정상 실행했습니다. 예제와 테스트는 `io.StringIO`만 사용했습니다. 실제 `sys.stdin`/`sys.stdout`, filesystem, shell, subprocess, network, 외부 MCP server, 실제 destructive Tool은 사용하지 않았습니다.

## 다음 슬라이스

injected stream runner를 실제 host process에 연결하기 전에 subprocess ownership, bounded stdout/stderr, EOF/disconnect, cancellation/signal, restart와 error propagation 정책을 별도 모델·문서·테스트로 좁게 정의합니다. durable approval/audit/idempotency와 Hermes/Codex integration은 계속 별도 설계·문서·테스트가 필요합니다.
