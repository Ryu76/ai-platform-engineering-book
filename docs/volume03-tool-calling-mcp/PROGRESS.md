# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO fake two-stream의 fair bounded drain scheduling model**
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

## 다음 슬라이스

fake round-robin model을 Popen child에 바로 결합하지 말고, 먼저 OS-level concurrent pipe adapter의
ready/readability contract와 finite backpressure ownership을 fake selector 또는 injected scheduler로 작게
모델링해야 합니다. block·overflow·read failure에서 scheduler, child shutdown, partial capture와 host
error를 누가 소유하는지 명확히 분리해 검증하세요. 그 뒤 decode/redaction, stdin framing/write,
cancellation/disconnect, Windows/POSIX process groups, exit-code restart/backoff, durable approval/audit/
idempotency, Hermes/Codex integration을 각각 별도 slice로 진행해야 합니다.
