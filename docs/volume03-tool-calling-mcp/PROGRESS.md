# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO fake readiness snapshot 기반 bounded two-stream drain model**
- 완료 선언: 아직 하지 않음. 실제 concurrent pipe IO/backpressure, decode/redaction,
  stdin ownership, cancellation/disconnect, Windows/POSIX process-group/signal semantics, exit-code
  restart supervisor, durable audit/idempotency와 Hermes/Codex 연동 및 전체 운영 DoD를 구현·문서화·검증해야 합니다.

## 이번 슬라이스: 두 binary output stream을 fake seam에서 공정하게 bounded drain하기

- `src/ai_platform/mcp/fair_drain.py`
  - `drain_mcp_stdio_stream_pair_fairly()`는 trusted host가 이미 소유한 서로 다른 synchronous
    binary readable `stdout`/`stderr` fake stream만 받습니다. stdout부터 시작해 아직 EOF가 아닌
    각 channel에 round마다 최대 한 번씩만 `read()`를 요청하는 deterministic scheduling model입니다.
  - 각각 1,024–1,048,576 byte의 independent ceiling과 4 KiB-or-less read / one-byte overflow
    sentinel을 적용합니다. 두 channel 모두 EOF여야 immutable raw-byte pair capture를 반환합니다.
  - overflow, requested-size violation, non-bytes result, read failure 중 하나가 발생하면 partial
    capture를 반환하지 않고 generic error로 종료하며 이후 어느 stream도 더 읽지 않습니다. raw
    adapter detail, decode, logging, retry, child shutdown은 이 boundary의 책임이 아닙니다.
  - 동일 object를 stdout/stderr로 재사용하는 input도 시작 전에 거부합니다. 이 모델은 synchronous
    `read()`가 실제 OS pipe에서 block하지 않음을 보장하지 않고 concurrent IO/backpressure 해결책도 아닙니다.
- `src/ai_platform/mcp/__init__.py`
  - fair drain error, pair capture, scheduling function을 public export에 추가했습니다.
- `examples/volume03/mcp_stdio_fair_stream_pair_drain.py`
  - in-memory `OfflineScheduledStream` 두 개의 fixed chunk만 round-robin으로 drain하고 byte count와
    turn trace를 출력합니다. 실제 subprocess, OS pipe, shell, filesystem, network, MCP server, Tool 또는
    destructive action을 수행하지 않습니다.
- `tests/volume03/test_mcp_fair_drain.py`
  - fair interleaving, EOF stream skip, stdout overflow, stderr read failure/non-bytes, requested-size
    violation, invalid stream, duplicated stream identity와 invalid budget에서 no-further-read / no-partial
    capture behavior를 fake stream으로 검증합니다.
- `docs/volume03-tool-calling-mcp/25-mcp-stdio-fair-stream-pair-drain.md`
  - fake scheduling contract, independent budget/error ownership, safe offline exercise 및 actual OS-level
    concurrency와의 명시적 차이를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 스물다섯 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_fair_stream_pair_drain.py
stdout_bytes: 10
stderr_bytes: 10
turns: stdout,stderr,stdout,stderr,stdout,stderr

$ uv run ruff check src/ai_platform/mcp/fair_drain.py tests/volume03/test_mcp_fair_drain.py examples/volume03/mcp_stdio_fair_stream_pair_drain.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/fair_drain.py
Success: no issues found in 1 source file

$ uv run pytest tests/volume03/test_mcp_fair_drain.py -q
11 passed in 0.25s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 24 source files

$ uv run pytest -q
219 passed in 1.25s

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

## 이번 슬라이스: fake readiness snapshot에서만 bounded two-stream을 읽기

- `src/ai_platform/mcp/ready_drain.py`
  - `drain_mcp_stdio_ready_stream_pair()`는 trusted host가 주입한 별개의 synchronous binary
    `stdout`/`stderr` fake stream과 fake readiness scheduler만 받습니다. snapshot마다 ready인
    open channel을 fixed stdout-then-stderr 순서로 최대 한 번만 읽습니다.
  - EOF가 아닌 channel만 ready가 될 수 있고, no-progress snapshot 및 closed channel stale-ready
    signal은 read 전에 generic error로 거부합니다. scheduler/read failure, malformed result,
    non-bytes, read-bound violation, overflow 뒤에는 partial capture를 반환하지 않고 scheduler나
    어느 stream도 더 호출하지 않습니다.
  - independent 1,024–1,048,576 byte ceiling, 4 KiB-or-less read와 one-byte overflow sentinel을
    유지합니다. selector/thread/event loop/Popen, blocking wait, decode/redaction/logging, child
    shutdown은 이 boundary의 책임이 아닙니다.
- `src/ai_platform/mcp/__init__.py`
  - readiness channels, scheduler protocol, drain error/function을 public export에 추가했습니다.
- `examples/volume03/mcp_stdio_ready_drain.py`
  - in-memory fixed chunks와 fixed readiness snapshots만 사용해 deterministic turn trace와 raw
    byte count를 출력합니다. 실제 subprocess, OS pipe, selector, shell, filesystem, network, MCP
    server, Tool 또는 destructive action을 수행하지 않습니다.
- `tests/volume03/test_mcp_ready_drain.py`
  - ready-order, EOF/open-state, no-progress, stale closed readiness, overflow stop, scheduler failure
    detail hiding, malformed snapshot/flag 및 invalid input IO-before-reject behavior를 fake seam으로
    검증합니다.
- `docs/volume03-tool-calling-mcp/26-mcp-stdio-ready-drain.md`
  - fake readiness contract, safe offline exercise, ownership/error boundary와 real OS adapter와의
    명시적 차이를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 스물여섯 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: readiness drain slice

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_ready_drain.py
stdout_bytes: 10
stderr_bytes: 10
turns: stdout,stderr,stdout,stderr,stdout,stderr

$ uv run ruff check src/ai_platform/mcp/ready_drain.py src/ai_platform/mcp/__init__.py tests/volume03/test_mcp_ready_drain.py examples/volume03/mcp_stdio_ready_drain.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/ready_drain.py src/ai_platform/mcp/__init__.py
Success: no issues found in 2 source files

$ uv run pytest tests/volume03/test_mcp_ready_drain.py -q
10 passed in 0.17s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 25 source files

$ uv run pytest -q
229 passed in 2.05s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

`uv`는 Hermes 활성 가상환경과 프로젝트 `.venv` 경로 불일치 경고를 출력했지만 프로젝트
가상환경에서 모든 command가 정상 완료했습니다. 이 slice의 예제와 test는 in-memory fake stream과
fake scheduler만 사용했으며 실제 process, OS pipe, selector, shell, filesystem, network 또는 Tool을
호출하지 않았습니다.

## 다음 슬라이스

fake readiness model을 Popen child에 바로 결합하지 말고, OS-level concurrent pipe adapter의
ready/readability contract와 finite backpressure ownership을 OS-specific boundary로 작게 모델링해야
합니다. block·overflow·read failure에서 scheduler, child shutdown, partial capture와 host error를 누가
소유하는지 명확히 분리해 검증하세요. 그 뒤 decode/redaction, stdin framing/write,
cancellation/disconnect, Windows/POSIX process groups, exit-code restart/backoff, durable approval/audit/
idempotency, Hermes/Codex integration을 각각 별도 slice로 진행해야 합니다.
