# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **attested·healthy MCP client configuration 뒤 exact Tool capability receipt를 fake seam으로 분리하는 model**
- 완료 선언: 아직 하지 않음. actual OS pipe worker/cancellation·disconnect semantics, Windows/POSIX
  process-group/signal semantics, exit-code restart supervisor, durable audit/idempotency와 Hermes/Codex
  연동 및 전체 운영 DoD를 구현·문서화·검증해야 합니다.

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

## 이번 슬라이스: 성공한 raw MCP output을 strict decode하고 fixed literal만 redaction하기

- `src/ai_platform/mcp/output_decode.py`
  - `decode_and_redact_mcp_stdio_output()`은 이미 EOF까지 bounded drain된 immutable
    `McpStdioStreamPairCapture`와 typed, deployment-owned
    `McpStdioOutputRedactionPolicy`만 받아 stdout/stderr를 strict UTF-8로 decode합니다.
  - valid bytes와 correct `stdout`/`stderr` channel identity를 decode 전에 재검증합니다. invalid
    UTF-8, malformed capture, invalid policy에는 raw bytes, secret literal, decoder detail 또는 partial
    text를 반환하지 않는 generic error로 종료합니다.
  - policy는 최대 16개의 non-empty, deduplicated, 256-character 이하 literal tuple만 받으며
    NUL/LF/CR을 거부합니다. 긴 literal부터 deterministic하게 `[REDACTED]`로 치환해 overlap의
    partial masking을 피합니다.
  - subprocess, pipe, selector, logging sink, JSON-RPC framing, child shutdown, retry 또는 external
    I/O를 수행하지 않습니다.
- `src/ai_platform/mcp/__init__.py`
  - output decode/redaction policy, snapshot, error와 public function을 export했습니다.
- `examples/volume03/mcp_stdio_output_decode_redaction.py`
  - memory-only fixed byte pair와 교육용 `demo-secret` literal만 decode/redact해 결과 text를
    출력합니다. 실제 process, shell, filesystem, network, MCP server, Tool 또는 destructive action을
    수행하지 않습니다.
- `tests/volume03/test_mcp_output_decode.py`
  - both-channel redaction, overlap ordering, empty policy, invalid UTF-8 detail hiding,
    mutable/ambiguous/oversize policy, invalid policy/capture 및 swapped/non-bytes capture의 decode 전
    거부를 검증합니다.
- `docs/volume03-tool-calling-mcp/27-mcp-stdio-output-decode-redaction.md`
  - strict decode/redaction contract, safe offline exercise, literal-only limitation 및 production
    observability/DLP responsibility를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 스물일곱 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: output decode/redaction slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_output_decode_redaction.py
stdout: result=ok; token=[REDACTED]
stderr: diagnostic=[REDACTED]

$ uv run ruff check src/ai_platform/mcp/output_decode.py src/ai_platform/mcp/__init__.py tests/volume03/test_mcp_output_decode.py examples/volume03/mcp_stdio_output_decode_redaction.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/output_decode.py src/ai_platform/mcp/__init__.py
Success: no issues found in 2 source files

$ uv run pytest tests/volume03/test_mcp_output_decode.py -q
13 passed in 0.16s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 26 source files

$ uv run pytest -q
242 passed in 1.59s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

## 이번 슬라이스: immutable stdin JSON-RPC frame을 bounded binary writer로 전송하기

- `src/ai_platform/mcp/input_write.py`
  - `build_mcp_stdio_input_frame()`은 dict request/notification을 existing strict JSON-RPC
    encoder/parser로 round-trip 검증해 immutable UTF-8/LF bytes snapshot만 만듭니다. malformed
    envelope, raw incomplete frame, invalid UTF-8, 16 KiB 초과 payload는 writer I/O 전에 거부합니다.
  - `write_mcp_stdio_input_frame()`은 trusted host가 주입한 binary `write`/`flush` seam만 사용합니다.
    한 write는 최대 4 KiB이고 positive short write에는 unsent suffix만 계속 보내며, complete frame
    뒤 flush를 정확히 한 번 호출합니다.
  - write exception, zero/negative/boolean/non-int/oversized write count와 flush failure는 raw adapter
    detail·partial receipt·retry 없이 `frame_may_be_partial=True` error로 끝납니다. receiver가 prefix
    또는 complete frame을 이미 받았을 수 있으므로 child shutdown, Tool execution, audit/logging은
    caller의 별도 ownership입니다.
- `src/ai_platform/mcp/__init__.py`
  - input frame, writer protocol, error/receipt와 builder/writer public APIs를 export했습니다.
- `examples/volume03/mcp_stdio_bounded_input_write.py`
  - memory-only `OfflineBinaryWriter`와 fixed initialized notification만 사용해 frame byte count,
    write count, flush count를 출력합니다. actual process, OS pipe, shell, filesystem, network, MCP
    server, Tool 또는 destructive action은 수행하지 않습니다.
- `tests/volume03/test_mcp_input_write.py`
  - complete write/one flush, short-write suffix continuation, 4 KiB chunk ceiling, malformed write count,
    write/flush failure에서 no retry/no extra flush/ambiguity, invalid raw/oversized frame 및 invalid writer의
    I/O-before-reject behavior를 fake seam으로 검증합니다.
- `docs/volume03-tool-calling-mcp/28-mcp-stdio-bounded-input-write.md`
  - strict frame construction, partial delivery semantics, safe offline exercise, exactly-once/idempotency와
    production Popen ownership의 명시적 차이를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 스물여덟 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: bounded stdin write slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_bounded_input_write.py
frame_bytes: 55
write_calls: 1
flush_calls: 1

$ uv run ruff check src/ai_platform/mcp/input_write.py src/ai_platform/mcp/__init__.py tests/volume03/test_mcp_input_write.py examples/volume03/mcp_stdio_bounded_input_write.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/input_write.py src/ai_platform/mcp/__init__.py
Success: no issues found in 2 source files

$ uv run pytest tests/volume03/test_mcp_input_write.py -q
13 passed in 0.79s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 27 source files

$ uv run pytest -q
255 passed in 3.49s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 warning을 출력했지만
project environment에서 정상 완료했습니다. example/test는 in-memory fixed bytes와 fake binary writer만
사용했으며 actual process, OS pipe, shell, filesystem, network, external MCP server, Tool 또는 destructive
action을 호출하지 않았습니다.

## 다음 슬라이스

actual Popen stdin handle을 직접 결합하지 말고, cancellation/disconnect를 typed request ID와
partial-frame ambiguity에 묶는 small injected policy seam을 모델링해야 합니다. disconnected writer에
새 frame을 쓰지 않고, in-flight partial frame failure와 caller-owned child shutdown request를 분리해
검증하세요. 그 뒤 Windows/POSIX process groups, exit-code restart/backoff, durable approval/audit/
idempotency, Hermes/Codex integration을 각각 별도 slice로 진행해야 합니다.

## 이번 슬라이스: typed cancellation·disconnect와 partial-frame shutdown signal을 delivery gate로 분리하기

- `src/ai_platform/mcp/input_delivery.py`
  - `McpStdioInputDeliveryGate`는 typed JSON-RPC request ID의 아직 시작하지 않은 frame을 취소하고,
    explicit disconnect 뒤 새 frame을 writer I/O 전에 막습니다. string ID와 integer ID는 기존
    correlation contract에 따라 서로 다른 cancellation state입니다.
  - bounded writer가 partial frame 가능성을 알리면 gate는 `SHUTDOWN_REQUIRED`로 전이하고 이후 모든
    새 frame을 차단합니다. error의 `child_shutdown_requested=True`는 host가 별도의 shutdown boundary를
    검토해야 한다는 signal이며, 이 module은 child/pipe/Popen을 직접 종료하지 않습니다.
  - blind retry, Tool execution, durable idempotency, audit, network 및 actual process I/O는 이
    policy seam의 책임이 아닙니다.
- `src/ai_platform/mcp/__init__.py`
  - delivery gate state, receipt, error를 public export에 추가했습니다.
- `examples/volume03/mcp_stdio_input_delivery_gate.py`
  - in-memory writer로 typed ID의 성공 frame 전달을 출력합니다. actual child process, OS pipe,
    shell, filesystem, network, MCP server, Tool 또는 destructive action을 수행하지 않습니다.
- `tests/volume03/test_mcp_input_delivery.py`
  - cancel pre-I/O, string/integer ID 분리, disconnect pre-I/O, partial failure의 caller-owned shutdown
    signal과 subsequent write block, invalid ID pre-I/O를 fake writer로 검증합니다.
- `docs/volume03-tool-calling-mcp/29-mcp-stdio-input-delivery-gate.md`
  - cancellation/disconnect/partial ambiguity ownership, safe offline exercise와 production limit을
    문서화했습니다.

## 검증 기록: input delivery gate slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_input_delivery_gate.py
correlation_id: mcp-stdio:string:delivery-demo-001
frame_bytes: 64
flush_calls: 1
state: open

$ uv run ruff format --check src/ai_platform/mcp/input_delivery.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_stdio_input_delivery_gate.py tests/volume03/test_mcp_input_delivery.py
4 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 28 source files

$ uv run pytest tests/volume03/test_mcp_input_delivery.py -q
5 passed in 0.24s

$ uv run pytest -q
260 passed in 2.07s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

`uv`는 Hermes 활성 가상환경과 프로젝트 `.venv` 경로 불일치 warning을 출력했지만, 모든 command는
project environment에서 정상 완료했습니다. example/test는 fixed JSON-RPC object와 in-memory fake
writer만 사용했고 actual process, OS pipe, shell, filesystem, network, external MCP server, Tool 또는
destructive action을 호출하지 않았습니다.

## 다음 슬라이스

actual Popen stdin ownership와 OS pipe backpressure는 별도 adapter로 분리해야 합니다. 그 뒤
Windows/POSIX process group·signal, exit-code restart/backoff, durable approval/audit/idempotency,
Hermes/Codex integration을 각각 독립적인 fixture·검증 경계로 진행합니다.

## 이번 슬라이스: Popen stdin snapshot·liveness를 delivery gate에 좁게 결합하기

- `src/ai_platform/mcp/popen_input.py`
  - `McpStdioPopenInputOwner`는 trusted Popen-like process에서 binary stdin handle을 construction
    시점에 정확히 한 번 snapshot합니다. open state의 live `poll() is None`일 때만 existing bounded
    delivery gate에 immutable frame을 넘깁니다.
  - cancelled/disconnected/shutdown-required request는 process poll과 writer I/O 전에 차단합니다.
    typed string/integer ID semantics와 partial write failure의 caller-owned shutdown signal을 기존
    gate contract 그대로 유지합니다.
  - child exit는 stdin writer I/O 없이 `DISCONNECTED`로 전이하고 generic unavailable error로 끝납니다.
    poll exception/malformed status도 raw detail을 숨기며 writer에 도달하지 않습니다. process stdin
    replacement도 construction-time snapshot을 바꾸지 않습니다.
  - actual Popen start, pipe close, child signal/shutdown, worker/thread/event loop, non-blocking I/O,
    backpressure timeout, retry, stdout/stderr drain과 Tool 실행은 이 adapter의 책임이 아닙니다.
- `src/ai_platform/mcp/input_delivery.py`
  - `is_cancelled()` read-only query를 추가하여 Popen owner가 cancelled frame을 `poll()` 전에
    writer-free로 reject하게 했습니다.
- `src/ai_platform/mcp/__init__.py`
  - Popen stdin process protocol, owner, generic error를 public export에 추가했습니다.
- `examples/volume03/mcp_stdio_popen_input_owner.py`
  - fixed JSON-RPC `safe/test` frame, `OfflinePopen`, memory-only `OfflineBinaryWriter`만 사용하여
    one-time poll, byte count, flush와 open state를 출력합니다. real Popen, OS pipe, shell,
    filesystem, network, external MCP server, Tool 또는 destructive action을 수행하지 않습니다.
- `tests/volume03/test_mcp_popen_input.py`
  - live delivery, cancellation before poll/I/O, exited-child disconnect/no future poll, hidden poll
    failure, partial write shutdown signal, immutable stdin snapshot, missing/invalid stdin pre-poll
    rejection을 fake seam으로 검증합니다.
- `docs/volume03-tool-calling-mcp/30-mcp-stdio-popen-input-owner.md`
  - captured handle ownership, liveness/error boundary, bounded write와 blocking OS-pipe backpressure의
    차이, safe offline exercise와 production follow-up을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: Popen stdin owner slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_popen_input_owner.py
correlation_id: mcp-stdio:string:popen-input-demo-001
frame_bytes: 67
poll_calls: 1
flush_calls: 1
state: open

$ uv run ruff format --check src/ai_platform/mcp/popen_input.py src/ai_platform/mcp/input_delivery.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_stdio_popen_input_owner.py tests/volume03/test_mcp_popen_input.py
5 files already formatted

$ uv run ruff check src/ai_platform/mcp/popen_input.py src/ai_platform/mcp/input_delivery.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_stdio_popen_input_owner.py tests/volume03/test_mcp_popen_input.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/popen_input.py src/ai_platform/mcp/input_delivery.py src/ai_platform/mcp/__init__.py
Success: no issues found in 3 source files

$ uv run pytest tests/volume03/test_mcp_popen_input.py tests/volume03/test_mcp_input_delivery.py -q
13 passed in 0.19s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 29 source files

$ uv run pytest -q
268 passed in 1.64s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만,
project environment에서 정상 완료했습니다. example/tests는 in-memory fake만 사용했고 actual process,
OS pipe, shell, filesystem, network, external MCP server, Tool 또는 destructive action을 호출하지 않았습니다.

## 이번 슬라이스: bounded pending-input queue와 single-worker result policy를 fake model로 분리하기

- `src/ai_platform/mcp/input_queue.py`
  - `McpStdioInputQueue`는 typed JSON-RPC correlation ID와 existing immutable input frame만 받아
    1–128 pending-frame budget 안에서 FIFO admission을 모델링합니다. process, pipe, thread, event
    loop, actual writer 또는 Tool을 호출하지 않습니다.
  - queue는 한 번에 하나의 exact claimed object만 worker ownership으로 넘깁니다. `DELIVERED`,
    `NOT_DELIVERED`, `AMBIGUOUS` enum outcome만 raw adapter detail 없이 한 번 기록할 수 있습니다.
  - cancel은 아직 claim되지 않은 typed frame만 제거하고 future admission을 막으며, disconnect는 pending을
    버리고 future admission/claim을 막되 in-flight worker를 interrupt하지 않습니다.
  - ambiguous worker outcome은 pending frame을 버리고 `SHUTDOWN_REQUIRED`와 caller-owned
    `child_shutdown_requested=True` signal로 전이합니다. child signal/close/retry를 직접 실행하지 않습니다.
- `src/ai_platform/mcp/__init__.py`
  - queue state, outcome, queued item, resolution과 generic error를 public export에 추가했습니다.
- `examples/volume03/mcp_stdio_bounded_input_queue.py`
  - fixed `safe/test` JSON-RPC object 두 개를 in-memory immutable queue에 offer/claim/resolve하고
    correlation ID, outcome, pending count, state를 출력합니다. actual process, OS pipe, worker, shell,
    filesystem, network, MCP server, Tool 또는 destructive action은 수행하지 않습니다.
- `tests/volume03/test_mcp_input_queue.py`
  - bounded FIFO/single claim, typed cancellation, in-flight no-interrupt, disconnect discard/block,
    ambiguous shutdown latch, forged/stale result, invalid outcome/capacity/ID/frame의 no-mutation behavior를
    process-free fake policy seam으로 검증합니다.
- `docs/volume03-tool-calling-mcp/31-mcp-stdio-bounded-input-queue.md`
  - admission budget, single-worker ownership, disconnect/ambiguity signal, safe offline exercise와
    actual platform worker adapter의 명시적 차이를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른한 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: bounded input queue slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_bounded_input_queue.py
correlation_id: mcp-stdio:string:queue-demo-001
outcome: delivered
pending_frames: 1
state: open

$ uv run ruff format --check src/ai_platform/mcp/input_queue.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_stdio_bounded_input_queue.py tests/volume03/test_mcp_input_queue.py
4 files already formatted

$ uv run ruff check src/ai_platform/mcp/input_queue.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_stdio_bounded_input_queue.py tests/volume03/test_mcp_input_queue.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/input_queue.py src/ai_platform/mcp/__init__.py
Success: no issues found in 2 source files

$ uv run pytest tests/volume03/test_mcp_input_queue.py -q
11 passed in 0.19s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 30 source files

$ uv run pytest -q
279 passed in 1.29s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만,
project environment에서 정상 완료했습니다. example/test는 immutable in-memory queue와 fixed enum
outcome만 사용했으며 actual process, OS pipe, thread, shell, filesystem, network, external MCP server,
Tool 또는 destructive action을 호출하지 않았습니다.

## 다음 슬라이스

Windows/POSIX actual signal API를 직접 호출하지 말고, allowlisted child launch plan에서 process-group
isolation intent와 graceful/force shutdown target을 typed platform fixture로 먼저 모델링해야 합니다.
Group leader/foreign process protection, unsupported platform/invalid plan의 no-signal behavior를 fake seam으로
검증하세요. 이어 exit-code restart/backoff, durable approval/audit/idempotency, Hermes/Codex integration을
각각 독립적인 fixture·검증 경계로 진행해야 합니다.

## 이번 슬라이스: claimed queue input을 fake delivery owner에 한 번 전달해 보수적으로 resolve하기

- `src/ai_platform/mcp/queued_delivery.py`
  - `deliver_next_mcp_stdio_queued_input()`은 open queue에서 FIFO item 하나만 claim하여 trusted injected
    delivery owner에 정확히 한 번 전달하고 terminal queue resolution을 반환합니다. empty queue는 owner I/O를
    호출하지 않고 `None`을 반환합니다.
  - matching local delivery receipt만 `DELIVERED`로 map합니다. typed non-partial delivery failure는
    `NOT_DELIVERED`이며 partial failure, unknown exception, malformed/mismatched receipt은 raw adapter detail
    없이 conservative `AMBIGUOUS`로 map해 existing queue의 caller-owned shutdown signal을 latch합니다.
  - claim 뒤 disconnect는 in-flight item을 interrupt하지 않고 result를 한 번 resolve하게 남깁니다. worker,
    thread, event loop, Popen, pipe, child signal/close/restart, retry, Tool 또는 external I/O는 소유하지 않습니다.
- `src/ai_platform/mcp/__init__.py`
  - queued delivery protocol, result, error와 one-item delivery function을 public export에 추가했습니다.
- `examples/volume03/mcp_stdio_queued_input_delivery.py`
  - fixed `safe/test` frame과 memory-only receipt owner로 one delivery result만 출력합니다. actual subprocess,
    pipe, shell, filesystem, network, MCP server, Tool 또는 destructive action은 수행하지 않습니다.
- `tests/volume03/test_mcp_queued_delivery.py`
  - one-call FIFO delivery, empty queue no-call, non-partial failure, partial/unknown/malformed ambiguity,
    in-flight disconnect ownership, invalid owner pre-claim rejection과 receipt mismatch를 fake seam으로 검증합니다.
- `docs/volume03-tool-calling-mcp/32-mcp-stdio-queued-input-delivery.md`
  - result mapping contract, shutdown/disconnect ownership, safe offline exercise와 actual worker boundary를
    문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른두 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: queued input delivery slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_queued_input_delivery.py
correlation_id: mcp-stdio:string:queued-delivery-demo-001
outcome: delivered
write_calls: 1
state: open

$ uv run ruff format --check src/ai_platform/mcp/queued_delivery.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_stdio_queued_input_delivery.py tests/volume03/test_mcp_queued_delivery.py
4 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 31 source files

$ uv run pytest tests/volume03/test_mcp_queued_delivery.py -q
10 passed in 0.14s

$ uv run pytest -q
289 passed in 1.38s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만,
project environment에서 정상 완료했습니다. example/tests는 in-memory frame·receipt·fake delivery owner만
사용했으며 actual process, OS pipe, thread, shell, filesystem, network, external MCP server, Tool 또는
destructive action을 호출하지 않았습니다.

## 이번 슬라이스: child-owned process-group shutdown target을 fake sender seam으로 분리하기

- `src/ai_platform/mcp/process_group.py`
  - `McpStdioIsolatedChildGroup`은 trusted platform adapter가 확인한 POSIX direct-child process
    group 또는 Windows child-owned Job scope snapshot만 받습니다. POSIX는 child PID, group owner,
    group ID가 모두 일치해야 하며 foreign/shared group을 sender 전에 거부합니다.
  - `prepare_mcp_stdio_group_shutdown_target()`은 allowlisted launch plan, platform fixture,
    typed graceful/force phase를 immutable target으로 바꿀 뿐 I/O를 수행하지 않습니다.
  - `send_mcp_stdio_group_shutdown_target()`은 fully validated target 하나만 injected sender에 한 번
    전달합니다. invalid plan/group/platform/phase/sender에는 no-send, sender failure에는 raw detail,
    retry, escalation 없이 generic error로 끝납니다.
  - subprocess, POSIX signal/process group, Windows Job Object, pipe, child reap/wait, restart,
    Tool 또는 destructive action을 직접 호출하지 않습니다.
- `src/ai_platform/mcp/__init__.py`
  - process-platform, fixture, target, phase, sender protocol, prepare/send public API를 export했습니다.
- `examples/volume03/mcp_stdio_process_group_shutdown_target.py`
  - fixed safe launch plan, child-owned POSIX fixture, memory-only sender로 graceful intent 한 번만
    출력합니다. actual child, group, Job Object, signal, shell, filesystem, network, MCP server, Tool 또는
    destructive action을 수행하지 않습니다.
- `tests/volume03/test_mcp_process_group.py`
  - POSIX/Windows typed target, foreign owner, POSIX leader mismatch, unsupported platform, invalid
    plan/phase의 no-send behavior, invalid PID, hidden sender exception/no retry, immutable target과
    platform-kind mismatch를 fake seam으로 검증합니다.
- `docs/volume03-tool-calling-mcp/33-mcp-stdio-process-group-shutdown-target.md`
  - isolation ownership, one-shot graceful/force intent, fake offline exercise와 actual platform adapter의
    production follow-up을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른세 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: process-group shutdown target slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_process_group_shutdown_target.py
server_name: safe-echo
platform: posix
target_kind: posix_process_group
phase: graceful
offline_sender_calls: 1

$ uv run ruff format --check src/ai_platform/mcp/process_group.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_stdio_process_group_shutdown_target.py tests/volume03/test_mcp_process_group.py
4 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 32 source files

$ uv run pytest tests/volume03/test_mcp_process_group.py -q
13 passed in 0.64s

$ uv run pytest -q
302 passed in 5.47s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만,
project environment에서 정상 완료했습니다. example/tests는 fixed in-memory plan·fixture·sender만
사용했으며 actual process, OS group/Job Object, signal, pipe, shell, filesystem, network, external MCP
server, Tool 또는 destructive action을 호출하지 않았습니다.

## 이번 슬라이스: finite restart budget과 monotonic backoff를 fake seam으로 분리하기

- `src/ai_platform/mcp/restart_policy.py`
  - `McpStdioRestartSupervisor`는 allowlisted immutable launch plan의 0–3 replacement budget만
    소유합니다. clean exit `0`은 restart하지 않고 bounded `1..255` non-zero exit만 `UNEXPECTED`로
    분류합니다.
  - `None`, bool, negative/oversized exit code는 unknown terminal state로 clock/sleeper/factory 전에
    거부합니다. exhausted budget도 해당 seam을 전혀 호출하지 않습니다.
  - successful replacement마다 0.25초부터 두 배가 되는 finite delay를 injected monotonic clock과
    sleeper로 검증한 뒤 기존 shell-free child factory를 정확히 한 번 호출합니다. sleeper 뒤 clock이
    deadline에 못 미치거나 뒤로 가면 new start하지 않습니다.
  - clock/sleeper/start raw exception detail을 숨기며 start failure는 budget을 소비하거나 자동 재시도하지
    않습니다. actual process monitoring/reaping, OS clock/sleep, group signal, pipe, thread, network,
    Tool 또는 destructive action은 호출하지 않습니다.
- `src/ai_platform/mcp/__init__.py`
  - exit classification, restart error/result/supervisor public API를 export했습니다.
- `examples/volume03/mcp_stdio_restart_backoff_policy.py`
  - fixed safe plan, memory-only fake child/factory/clock/sleeper와 fake nonzero exit 하나로 delay와 start
    count를 출력합니다. actual Popen, OS time wait, process, shell, filesystem, network, MCP server, Tool
    또는 destructive action을 수행하지 않습니다.
- `tests/volume03/test_mcp_restart_policy.py`
  - exponential finite delay, clean no-call, budget exhaustion, unknown exit pre-start rejection,
    clock/sleeper failure detail hiding, early deadline 및 invalid plan을 fake seam으로 검증합니다.
- `docs/volume03-tool-calling-mcp/34-mcp-stdio-finite-restart-backoff.md`
  - exit taxonomy, finite monotonic backoff ownership, safe offline exercise와 production crash-loop/durable
    execution follow-up을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른네 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: finite restart/backoff slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_restart_backoff_policy.py
exit_classification: unexpected
backoff_seconds: 0.25
restart_count: 1
offline_start_calls: 1

$ uv run ruff format --check src/ai_platform/mcp/restart_policy.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_stdio_restart_backoff_policy.py tests/volume03/test_mcp_restart_policy.py
4 files already formatted

$ uv run ruff check src/ai_platform/mcp/restart_policy.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_stdio_restart_backoff_policy.py tests/volume03/test_mcp_restart_policy.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/restart_policy.py src/ai_platform/mcp/__init__.py
Success: no issues found in 2 source files

$ uv run pytest tests/volume03/test_mcp_restart_policy.py -q
12 passed in 0.19s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 33 source files

$ uv run pytest -q
314 passed in 1.63s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만,
project environment에서 정상 완료했습니다. example/tests는 fixed in-memory plan·child·factory·clock·sleeper만
사용했으며 actual process, OS clock/sleep, group signal, pipe, shell, filesystem, network, external MCP server,
Tool 또는 destructive action을 호출하지 않았습니다.

## 다음 슬라이스

actual durable store를 열지 말고, allowlisted Tool execution의 idempotency key와 typed approval/audit
record의 exact request binding을 immutable in-memory fixture로 먼저 모델링해야 합니다. duplicate request,
approval expiry/replay, audit append failure와 ambiguous Tool result가 execution 전에 또는 caller-owned
reconciliation signal로 안전하게 멈추는지 fake seams에서 검증하세요. 그 뒤 Hermes/Codex integration을
독립적인 fixture·검증 경계로 진행해야 합니다.

## 이번 슬라이스: idempotency·expiring approval·audit completion을 memory fixture로 묶기

- `src/ai_platform/tools/idempotency.py`
  - `McpToolExecutionBinding`은 allowlisted Tool request의 idempotency key, request ID, Tool name과
    canonical finite JSON argument의 SHA-256 digest만 immutable하게 묶으며 raw arguments를 보관하지 않습니다.
  - `InMemoryMcpToolExecutionLedger.reserve()`는 expired/replayed approval, duplicate key, conflicting
    binding을 Tool execution 전에 거부하고 `AUTHORIZED` audit append 성공 뒤에만 one-time claim을 발급합니다.
    pre-execution audit append failure는 key/approval을 소비하지 않으며 raw adapter detail도 숨깁니다.
  - `resolve()`는 confirmed success의 completion audit을 남기거나 ambiguous result/audit failure를
    `RECONCILIATION_REQUIRED` latch와 caller-owned signal로 바꿉니다. Tool handler, durable store, OS clock,
    process, network, retry 또는 destructive action을 직접 호출하지 않습니다.
- `src/ai_platform/tools/__init__.py`
  - idempotency binding, approval, audit sink/event, ledger, claim/resolution/state public API를 export했습니다.
- `examples/volume03/mcp_tool_idempotency_approval_audit.py`
  - fixed `safe_calculator` intent와 in-memory approval/audit/ledger만 reserve/resolve하고 audit phase 및 final
    state를 출력합니다. handler나 actual database, filesystem, process, shell, network, MCP server, Tool 또는
    destructive action을 수행하지 않습니다.
- `tests/volume03/test_tool_idempotency.py`
  - exact digest/no raw argument, duplicate/collision, expiry/replay, pre-execution audit failure no-consume,
    success completion, ambiguous/audit-failure reconciliation latch, forged claim, invalid time의 pre-execution
    behavior를 memory fake seam으로 검증합니다.
- `docs/volume03-tool-calling-mcp/35-mcp-tool-idempotency-approval-audit.md`
  - exact binding, one-time expiry, audit ordering, ambiguity ownership, safe offline exercise와 durable production
    transaction/outbox·reconciliation follow-up을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른다섯 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: idempotency·approval·audit fixture slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_tool_idempotency_approval_audit.py
idempotency_key: idem-demo-001
audit_phases: authorized,succeeded
state: completed
reconciliation_required: False

$ uv run ruff format --check src/ai_platform/tools/idempotency.py src/ai_platform/tools/__init__.py examples/volume03/mcp_tool_idempotency_approval_audit.py tests/volume03/test_tool_idempotency.py
4 files already formatted

$ uv run ruff check src/ai_platform/tools/idempotency.py src/ai_platform/tools/__init__.py examples/volume03/mcp_tool_idempotency_approval_audit.py tests/volume03/test_tool_idempotency.py
All checks passed!

$ uv run mypy src/ai_platform/tools/idempotency.py src/ai_platform/tools/__init__.py
Success: no issues found in 2 source files

$ uv run pytest tests/volume03/test_tool_idempotency.py -q
13 passed

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 34 source files

$ uv run pytest -q
327 passed in 2.27s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

`uv`는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만 targeted command는
project environment에서 정상 완료했습니다. Example/test는 fixed in-memory data와 fake audit seam만 사용했으며
actual Tool handler, database, filesystem, process, shell, network, external MCP server 또는 destructive action을
호출하지 않았습니다.

## 다음 슬라이스

Hermes/Codex integration은 real external service를 열지 않는 allowlisted configuration fixture와 typed
request/audit binding으로 별도 모델링해야 합니다. 그 뒤 전체 Volume 03 DoD를 다시 점검하고, production
integration의 credential·durable approval/audit/idempotency ownership은 explicitly out of scope로 검증하세요.

## 이번 슬라이스: Hermes·Codex client에 exact Tool visibility handoff만 만들기

- `src/ai_platform/mcp/client_handoff.py`
  - `McpClientToolVisibilityPolicy`는 `hermes-agent`/`codex-cli` consumer label과 1–16개의 immutable
    exact Tool name tuple만 받습니다. wildcard, newline, duplicate, empty/mutable list는 client config writer
    전에 거부합니다.
  - `prepare_mcp_client_integration_handoff()`은 trusted allowlisted launch plan과 static catalog에 policy의
    모든 Tool이 존재할 때만 client/server/tool-name immutable snapshot을 반환합니다. missing Tool, catalog
    failure, invalid input은 catalog metadata나 adapter detail을 반사하지 않습니다.
  - actual Hermes/Codex configuration file write/reload, client launch/connect, subprocess, network, Tool
    execution, approval, audit/idempotency는 이 in-memory handoff model의 책임이 아닙니다.
- `src/ai_platform/mcp/__init__.py`
  - client handoff error, kind, policy, result와 builder를 public export에 추가했습니다.
- `examples/volume03/mcp_client_integration_handoff.py`
  - `safe_calculator`/`safe_text_case` static definition, memory-only launch plan/catalog/policy만 조합하고
    `safe_calculator` visibility snapshot을 출력합니다. actual client, MCP server, process, shell, filesystem,
    network, Tool 또는 destructive action을 호출하지 않습니다.
- `tests/volume03/test_mcp_client_handoff.py`
  - Hermes/Codex labels의 exact handoff, invalid/mutable/duplicate/wildcard policy, catalog 밖 Tool의
    metadata-hidden rejection, invalid plan/catalog의 client handoff 전 rejection을 검증합니다.
- `docs/volume03-tool-calling-mcp/36-mcp-client-integration-handoff.md`
  - client-neutral policy boundary와 Hermes 공식 MCP guide link, safe offline exercise, actual client-specific
    config/reload/credential ownership 한계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른여섯 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: client integration handoff slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_client_integration_handoff.py
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator

$ uv run ruff format --check src/ai_platform/mcp/client_handoff.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_client_integration_handoff.py tests/volume03/test_mcp_client_handoff.py
4 files already formatted

$ uv run ruff check src/ai_platform/mcp/client_handoff.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_client_integration_handoff.py tests/volume03/test_mcp_client_handoff.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/client_handoff.py src/ai_platform/mcp/__init__.py
Success: no issues found in 2 source files

$ uv run pytest tests/volume03/test_mcp_client_handoff.py -q
10 passed in 0.20s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 35 source files

$ uv run pytest -q
337 passed in 1.68s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만 project
environment에서 정상 완료했습니다. 이 slice의 example/test는 in-memory data만 사용했으며 actual
Hermes/Codex client, process, MCP server, network, Tool 또는 destructive action을 호출하지 않았습니다.

## 다음 슬라이스

client-neutral handoff은 actual client configuration의 완료 선언이 아닙니다. Hermes 공식 MCP 설정과
Codex의 해당 공식 configuration schema/version을 별도 read-only fixture로 대조하고, credential/file
permission/reload acknowledgement를 실제 client 실행 없이 검증할 safe adapter boundary가 남아 있습니다.
그 뒤 전체 운영 DoD를 재평가해야 합니다.

## 이번 슬라이스: client configuration acknowledgement를 exact handoff에 대조하기

- `src/ai_platform/mcp/client_acknowledgement.py`
  - `McpClientConfigurationApplication`은 기존 immutable client-neutral handoff을 direct construction
    뒤에도 exact client/server/Tool tuple로 재검증하고, opaque one-line deployment generation과 묶습니다.
  - `McpClientConfigurationAcknowledgement`는 separate client-specific adapter의 successful apply/reload
    receipt를 위한 최소 snapshot이며, client/server/Tool tuple/generation이 application과 전부 일치할 때만
    `verify_mcp_client_configuration_acknowledgement()`가 original handoff을 돌려줍니다.
  - mismatch·mutable/wildcard visibility·forged handoff은 client I/O 전에 generic error로 중단하며 config
    content, credential, path, adapter log 또는 partial visibility를 보관/반환하지 않습니다. Actual client
    config schema/version, credential/file permission, atomic write/reload provenance, connection health는
    별도 production adapter ownership입니다.
- `src/ai_platform/mcp/__init__.py`
  - configuration application, acknowledgement, error, verifier를 public export에 추가했습니다.
- `examples/volume03/mcp_client_configuration_acknowledgement.py`
  - fixed in-memory Hermes label, `safe_calculator` exact visibility, deployment generation receipt만 대조해
    verified fields를 출력합니다. actual Hermes/Codex client, config file, secret, process, filesystem,
    network, MCP server, Tool 또는 destructive action을 호출하지 않습니다.
- `tests/volume03/test_mcp_client_acknowledgement.py`
  - matching original handoff identity, client/server/Tool/generation mismatch, invalid/mutable/duplicate/
    wildcard/newline receipt, forged handoff, invalid application/acknowledgement의 pre-trust rejection을
    in-memory fixture로 검증합니다.
- `docs/volume03-tool-calling-mcp/37-mcp-client-configuration-acknowledgement.md`
  - receipt equality boundary, Hermes 공식 MCP guide, safe offline exercise 및 actual schema/credential/
    reload health ownership 한계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른일곱 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: client configuration acknowledgement slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_client_configuration_acknowledgement.py
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator
configuration_generation: volume03-demo-001

$ uv run ruff format --check src/ai_platform/mcp/client_acknowledgement.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_client_configuration_acknowledgement.py tests/volume03/test_mcp_client_acknowledgement.py
4 files already formatted

$ uv run ruff check src/ai_platform/mcp/client_acknowledgement.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_client_configuration_acknowledgement.py tests/volume03/test_mcp_client_acknowledgement.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/client_acknowledgement.py src/ai_platform/mcp/__init__.py
Success: no issues found in 2 source files

$ uv run pytest tests/volume03/test_mcp_client_acknowledgement.py -q
12 passed in 0.19s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 36 source files

$ uv run pytest -q
349 passed in 1.63s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만 project
environment에서 정상 완료했습니다. 이 slice의 example/test는 in-memory data만 사용했으며 actual
Hermes/Codex client, config file, credential, process, MCP server, network, Tool 또는 destructive action을
호출하지 않았습니다.

## 다음 슬라이스

client receipt equality도 actual configuration security/health의 완료 선언이 아닙니다. Volume 03 DoD를
정확히 재평가하고, production에 남은 official client schema/version, authenticated receipt provenance,
credential injection, file ownership/atomic rollback, reload/reconnect health와 durable operations를
implementation boundary 밖으로 명시적으로 점검해야 합니다.

## 이번 슬라이스: fresh configuration receipt와 client-specific provenance verifier를 분리하기

- `src/ai_platform/mcp/client_attestation.py`
  - `McpClientConfigurationAttestationRequest`는 exact configuration application을 deployment-owned
    16–128 character single-line challenge와 묶고, `McpClientConfigurationAttestation`은 exact
    acknowledgement와 challenge echo만 보관합니다.
  - `verify_mcp_client_configuration_attestation()`은 challenge 및 existing client/server/exact Tool
    tuple/generation acknowledgement를 verifier 호출 전에 대조합니다. trusted injected verifier의 exact
    bool `True`일 때만 original immutable handoff을 반환하며, false/non-bool/exception detail이나 partial
    handoff는 반환하지 않습니다.
  - actual Hermes/Codex client, configuration file, credential/signature, subprocess, filesystem, network,
    MCP server, Tool 또는 destructive action을 호출하지 않습니다. Challenge equality는 freshness correlation
    model일 뿐 authenticated issuer proof, signature validation, reload/reconnect health proof가 아닙니다.
- `src/ai_platform/mcp/client_acknowledgement.py`
  - public verification 시 frozen dataclass를 우회해 mutation된 application/acknowledgement도 exact
    visibility/generation contract로 다시 검사해 forged wildcard receipt가 handoff 반환 전에 막히게 했습니다.
- `src/ai_platform/mcp/__init__.py`
  - attestation request, receipt, verifier, error와 verifier function을 public export에 추가했습니다.
- `examples/volume03/mcp_client_configuration_attestation.py`
  - fixed in-memory Hermes label, `safe_calculator` receipt/challenge와 `OfflineReceiptVerifier`만 대조하여
    verified fields와 one verifier call을 출력합니다. actual client/config/credential/process/network/Tool은
    호출하지 않습니다.
- `tests/volume03/test_mcp_client_attestation.py`
  - exact success/one call, challenge 및 acknowledgement mismatch의 pre-verifier rejection, false/non-bool,
    hidden verifier exception, malformed challenge 및 invalid verifier를 fake seam으로 검증합니다.
- `tests/volume03/test_mcp_client_acknowledgement.py`
  - construction 뒤 frozen receipt mutation을 verification 시 다시 거부하는 regression을 추가했습니다.
- `docs/volume03-tool-calling-mcp/38-mcp-client-configuration-attestation.md`
  - freshness/provenance seam, safe offline exercise, exact-`True` contract와 actual authenticated receipt,
    schema/version, credential/file/reload/reconnect health의 production ownership을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른여덟 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: client configuration attestation slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_client_configuration_attestation.py
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator
verifier_calls: 1

$ uv run ruff format --check src/ai_platform/mcp/client_acknowledgement.py src/ai_platform/mcp/client_attestation.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_client_configuration_attestation.py tests/volume03/test_mcp_client_acknowledgement.py tests/volume03/test_mcp_client_attestation.py
6 files already formatted

$ uv run ruff check src/ai_platform/mcp/client_acknowledgement.py src/ai_platform/mcp/client_attestation.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_client_configuration_attestation.py tests/volume03/test_mcp_client_acknowledgement.py tests/volume03/test_mcp_client_attestation.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/client_acknowledgement.py src/ai_platform/mcp/client_attestation.py src/ai_platform/mcp/__init__.py
Success: no issues found in 3 source files

$ uv run pytest tests/volume03/test_mcp_client_acknowledgement.py tests/volume03/test_mcp_client_attestation.py -q
25 passed in 0.28s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 37 source files

$ uv run pytest -q
362 passed in 1.62s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만 project
environment에서 정상 완료했습니다. Example/test는 fixed in-memory data와 fake verifier만 사용했으며 actual
Hermes/Codex client, configuration file, credential/signature, process, filesystem, network, MCP server, Tool 또는
destructive action을 호출하지 않았습니다.

## 다음 슬라이스

Volume 03 DoD를 정확히 재평가해야 합니다. 이 teaching repository의 fake seams가 authenticated receipt
provenance, credential injection, config file ownership/atomic rollback, actual client schema/version compatibility,
reload/reconnect health, OS-level pipe/process semantics, durable idempotency/audit/reconciliation을 구현하거나
증명하지 않는다는 production boundary를 명시적으로 점검하세요. 남은 production concern을 fake model로 더
세분화할지, current documented scope의 learning DoD를 충족하는지 결정해야 합니다.

## 이번 슬라이스: attested configuration 뒤 health evidence를 one-shot fake seam으로 분리하기

- `src/ai_platform/mcp/client_health.py`
  - `verify_mcp_client_configuration_health()`는 existing fresh provenance attestation을 먼저
    검증하고, caller-owned `McpClientConfigurationHealthProbe`를 정확히 한 번 호출합니다.
  - malformed request/attestation/verifier/probe 및 attestation mismatch/failure는 health probe 호출
    전에 거부합니다. probe의 exact bool `True`만 original immutable handoff을 반환합니다.
  - false/non-bool/exception은 raw adapter detail 또는 partial Tool visibility를 반환하지 않는 generic
    error가 됩니다. actual Hermes/Codex client, config file, credential, reload/connect, network, MCP
    server, Tool 또는 destructive action은 호출하지 않습니다.
- `src/ai_platform/mcp/__init__.py`
  - health error, probe protocol, verification function을 public export에 추가했습니다.
- `examples/volume03/mcp_client_configuration_health.py`
  - fixed Hermes `safe_calculator` application/receipt/challenge와 in-memory verifier/probe만 대조해
    one health-probe call을 출력합니다. actual client, config file, process, filesystem, network, Tool
    또는 destructive action을 수행하지 않습니다.
- `tests/volume03/test_mcp_client_health.py`
  - success의 one-call-per-seam, attestation mismatch/failure의 probe-before-reject, false/non-bool
    result, hidden probe exception 및 invalid probe의 no-call behavior를 fake seam으로 검증합니다.
- `docs/volume03-tool-calling-mcp/39-mcp-client-configuration-health.md`
  - attestation/probe ordering, exact-`True` boundary, safe offline exercise 및 actual reload/reconnect/
    server identity/transport health의 production ownership을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 서른아홉 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: client configuration health slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_client_configuration_health.py
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator
health_probe_calls: 1

$ uv run ruff format --check src/ai_platform/mcp/client_health.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_client_configuration_health.py tests/volume03/test_mcp_client_health.py
4 files already formatted

$ uv run ruff check src/ai_platform/mcp/client_health.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_client_configuration_health.py tests/volume03/test_mcp_client_health.py
All checks passed!

$ uv run mypy src/ai_platform/mcp/client_health.py src/ai_platform/mcp/__init__.py
Success: no issues found in 2 source files

$ uv run pytest tests/volume03/test_mcp_client_health.py -q
9 passed in 0.20s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 38 source files

$ uv run pytest -q
371 passed in 1.58s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만
project environment에서 정상 완료했습니다. Example/test는 fixed in-memory data와 fake verifier/probe만
사용했으며 actual Hermes/Codex client, configuration file, credential, process, filesystem, network, MCP
server, Tool 또는 destructive action을 호출하지 않았습니다.

## 이번 슬라이스: healthy attestation 뒤 client-visible exact Tool snapshot을 대조하기

- `src/ai_platform/mcp/client_capability.py`
  - `verify_mcp_client_configuration_capability()`는 existing fresh provenance attestation과
    one-shot health evidence를 먼저 검증한 뒤 caller-owned capability probe를 정확히 한 번 호출합니다.
  - immutable `McpClientConfigurationCapabilityReceipt`의 1–16 unique exact Tool-name tuple이 original
    handoff tuple과 순서까지 같을 때만 original handoff을 반환합니다. extra/missing/reordered tuple,
    wildcard/malformed/forged receipt, probe exception에는 partial visibility나 raw adapter detail을
    반환하지 않습니다.
  - actual Hermes/Codex client, config file, credential, actual `tools/list`, reload/connect, process,
    filesystem, network, MCP server, Tool 또는 destructive action을 호출하지 않습니다.
- `src/ai_platform/mcp/__init__.py`
  - capability error, receipt, probe protocol과 verification function을 public export에 추가했습니다.
- `examples/volume03/mcp_client_configuration_capability.py`
  - fixed Hermes `safe_calculator` application/receipt/challenge와 in-memory verifier/health/capability
    fake만 대조해 one capability-probe call을 출력합니다. actual client/config/process/network/Tool은
    호출하지 않습니다.
- `tests/volume03/test_mcp_client_capability.py`
  - exact success/one call per seam, invalid attestation와 failed health의 downstream pre-call rejection,
    extra/missing/malformed receipt, hidden probe exception, forged mutable receipt revalidation 및 invalid
    probe의 no-call behavior를 fake seam으로 검증합니다.
- `docs/volume03-tool-calling-mcp/40-mcp-client-configuration-capability.md`
  - attestation/health/capability ordering, exact tuple contract, safe offline exercise와 actual
    tools-list/session/server identity/reconnect 및 production authorization ownership을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 마흔 번째 학습 장을 목록에 추가했습니다.

## 검증 기록: client configuration capability slice

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_client_configuration_capability.py
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator
capability_probe_calls: 1

$ uv run pytest tests/volume03/test_mcp_client_capability.py -q
9 passed in 0.22s

$ uv run ruff format --check src/ai_platform/mcp/client_capability.py src/ai_platform/mcp/__init__.py examples/volume03/mcp_client_configuration_capability.py tests/volume03/test_mcp_client_capability.py
4 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 39 source files

$ uv run pytest -q
380 passed in 1.73s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

모든 `uv` command는 Hermes 활성 가상환경과 project `.venv` 경로 불일치 warning을 출력했지만 project
environment에서 정상 완료했습니다. Example/test는 fixed in-memory data와 fake verifier/probe만 사용했으며 actual
Hermes/Codex client, configuration file, credential, process, filesystem, network, MCP server, Tool 또는
destructive action을 호출하지 않았습니다.

## 다음 슬라이스

이 capability model의 exact tuple은 actual client `tools/list`, reload/reconnect, authenticated session 또는
server identity/transport health proof가 아닙니다. Volume 03의 learning DoD와 production DoD를 명시적으로
분리해 재평가하세요. Production에는 official client schema/version compatibility, authenticated credential/
issuer/key rotation, config file ownership/atomic rollback, bounded reload/reconnect/capability adapter,
OS-level pipe/process semantics, durable audit/idempotency/reconciliation과 operator observability가 여전히
별도 검증 경계로 남아 있습니다.
