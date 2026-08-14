# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO injected binary stdin writer의 bounded frame/partial delivery model**
- 완료 선언: 아직 하지 않음. actual Popen stdin ownership/backpressure, cancellation/disconnect,
  Windows/POSIX process-group/signal semantics, exit-code restart supervisor, durable audit/idempotency와
  Hermes/Codex 연동 및 전체 운영 DoD를 구현·문서화·검증해야 합니다.

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

## 다음 슬라이스

actual OS pipe의 backpressure를 direct synchronous `write()`로 해결하려 하지 말고, Windows/POSIX별
blocking/cancellation semantics를 노출하지 않는 bounded queue·worker result policy를 fake seam부터
분리해 모델링해야 합니다. 이어 Windows/POSIX process group·signal, exit-code restart/backoff, durable
approval/audit/idempotency, Hermes/Codex integration을 각각 독립적인 fixture·검증 경계로 진행하세요.
