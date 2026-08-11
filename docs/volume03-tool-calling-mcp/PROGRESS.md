# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO single binary output의 bounded EOF collector**
- 완료 선언: 아직 하지 않음. stdout/stderr concurrent drain·backpressure, decode/redaction,
  stdin ownership, cancellation/disconnect, Windows/POSIX process-group/signal semantics, exit-code
  restart supervisor, durable audit/idempotency와 Hermes/Codex 연동 및 전체 운영 DoD를 구현·문서화·검증해야 합니다.

## 이번 슬라이스: 한 binary output stream을 overflow sentinel까지 bounded drain하기

- `src/ai_platform/mcp/stream_drain.py`
  - `McpStdioReadableBinaryStream`은 trusted host가 이미 소유한 한 binary readable stream의
    최소 synchronous `read(size) -> bytes` contract입니다. subprocess, pipe 생성, Tool 실행,
    decode, logging, retry, child shutdown을 하지 않습니다.
  - `drain_mcp_stdio_binary_stream()`은 exact `stdout` 또는 `stderr`와 launch-plan-compatible
    1,024–1,048,576 byte budget만 받습니다. fixed 4 KiB-or-less read와 한 byte overflow sentinel로
    EOF까지 raw bytes를 수집합니다.
  - ceiling을 넘는 첫 byte, requested size보다 큰 반환, non-bytes 반환, stream read failure는
    partial capture를 반환하거나 raw adapter detail을 노출하지 않고 generic error로 끝납니다.
    overflow/failure 뒤 추가 read 또는 retry도 하지 않습니다.
  - `McpStdioStreamCapture`는 successful EOF capture의 immutable raw-byte snapshot만
    제공합니다. UTF-8/JSON decode와 redaction policy는 의도적으로 아직 연결하지 않았습니다.
- `src/ai_platform/mcp/__init__.py`
  - binary readable protocol, capture/error type, bounded drain function을 public export에
    추가했습니다.
- `examples/volume03/mcp_stdio_bounded_stream_drain.py`
  - in-memory `OfflineReadableStream`의 fixed byte chunks만 drain하고 channel, capture byte
    count, read count를 출력합니다. 실제 subprocess, OS pipe, shell, signal, filesystem,
    network, external MCP server, Tool 또는 destructive action을 수행하지 않습니다.
- `tests/volume03/test_mcp_stream_drain.py`
  - fake stream으로 success EOF capture, one-byte overflow에서 no further read, read-bound
    violation, non-bytes, raw failure narrowing, invalid channel/budget 및 invalid stream을
    검증합니다.
- `docs/volume03-tool-calling-mcp/24-mcp-stdio-bounded-output-drain.md`
  - single-stream ownership, sentinel overflow policy, offline exercise, deliberate non-goals를
    문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 스물네 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_bounded_stream_drain.py
channel: stdout
captured_bytes: 18
read_calls: 3

$ uv run ruff check src/ai_platform/mcp tests/volume03/test_mcp_stream_drain.py examples/volume03/mcp_stdio_bounded_stream_drain.py
All checks passed!

$ uv run mypy src
Success: no issues found in 23 source files

$ uv run pytest tests/volume03/test_mcp_stream_drain.py tests/volume03/test_mcp_subprocess_factory.py tests/volume03/test_mcp_host.py -q
43 passed in 0.21s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 23 source files

$ uv run pytest -q
208 passed in 1.40s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

`uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만
프로젝트 가상환경에서 정상 실행했습니다. 예제와 테스트는 in-memory fake stream만 사용했으며
실제 Popen default path, process, OS pipe, filesystem, shell, network 또는 Tool을 호출하지
않았습니다.

## 다음 슬라이스

single-stream collector를 Popen child에 바로 결합하지 말고, 먼저 stdout과 stderr를 동시에
공정하게 소비할 trusted scheduling adapter를 fake schedulable streams로 작게 모델링해야 합니다.
두 independent per-stream ceiling의 overflow/failure가 발생할 때 추가 read, child shutdown,
partial capture와 host error를 누가 소유하는지 명확히 분리해 검증하세요. 그 뒤 decode/redaction,
stdin framing/write, cancellation/disconnect, Windows/POSIX process groups, exit-code
restart/backoff, durable approval/audit/idempotency, Hermes/Codex integration을 각각 별도 slice로
진행해야 합니다.
