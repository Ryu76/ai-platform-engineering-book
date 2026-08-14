# MCP STDIO Popen stdin owner: captured handle·liveness·delivery gate를 분리하기

## 1. 왜 raw `process.stdin`을 바로 쓰지 않는가

앞 장의 `McpStdioInputDeliveryGate`는 frame의 cancellation, explicit disconnect, partial-write
ambiguity만 모델링합니다. 그러나 actual `Popen(stdin=PIPE)`를 운영 adapter에 연결하면 다음의
추가 ownership 문제가 생깁니다.

- child가 이미 종료한 뒤 stale stdin handle에 새 JSON-RPC frame을 쓰면 안 됩니다.
- host 내부의 여러 component가 `process.stdin`을 다시 얻어 서로 다른 frame을 섞으면 안 됩니다.
- `write()`/`flush()`는 OS pipe backpressure로 block할 수 있지만, bounded 4 KiB write 자체가
  non-blocking I/O나 cancellation interrupt를 제공하지는 않습니다.

`McpStdioPopenInputOwner`는 이 문제를 좁게 분리합니다. trusted host가 실제로 시작한
Popen-like process를 한 번 전달하면 `stdin` binary handle을 construction 시점에 snapshot하고,
live child인 경우에만 기존 bounded delivery gate로 frame을 넘깁니다.

```text
trusted Popen process
    │ stdin snapshot (one time) + poll()
    ▼
McpStdioPopenInputOwner ──> McpStdioInputDeliveryGate ──> bounded binary write/flush
    │                              │
    │ exited: disconnect/no write  └─ partial: shutdown-required signal
    └─ no process close, signal, retry, worker/thread ownership
```

## 2. 좁은 계약

- constructor는 `write(bytes) -> int`, `flush()`를 가진 binary stdin과 `poll() -> int | None`을
  모두 가진 trusted Popen-like process만 받습니다. missing/invalid stdin은 `poll()` 전에 거부합니다.
- `stdin`은 **한 번만** snapshot합니다. 나중에 foreign code가 `process.stdin` attribute를 바꿔도
  owner는 그 replacement handle을 사용하지 않습니다. 이것은 host의 single-owner convention이며,
  raw handle을 가진 foreign code의 직접 write를 OS 수준에서 방지하는 lock은 아닙니다.
- cancelled typed request, `DISCONNECTED`, `SHUTDOWN_REQUIRED` 상태는 `poll()`과 writer I/O 전에
  기존 gate가 거부합니다. string ID `"7"`와 integer ID `7`은 계속 구분됩니다.
- open state에서는 `poll()`이 `None`인 경우에만 immutable frame을 전달합니다. integer exit code면
  gate를 `DISCONNECTED`로 바꾸고 writer I/O 없이 generic unavailable error를 반환합니다.
- `poll()` exception 또는 non-integer/non-`None` result도 raw OS detail 없이 generic error로 끝나며,
  writer에 도달하지 않습니다. 이는 liveness를 모르는 상태이므로 이 tiny adapter가 retry·shutdown을
  결정하지 않습니다.
- bounded writer가 partial delivery 가능성을 보고하면 기존 gate처럼 `SHUTDOWN_REQUIRED`와
  `child_shutdown_requested=True` signal을 반환합니다. owner도 child terminate/kill/pipe close를
  직접 호출하지 않습니다.

## 3. backpressure에서 이 model이 보장하지 않는 것

이 adapter는 local frame validation과 **각 write 최대 4 KiB**라는 기존 bound를 재사용합니다.
그렇다고 Windows anonymous pipe나 POSIX pipe의 `write()`가 유한 시간에 return한다는 보장은 없습니다.
`Popen` binary stream은 synchronous이므로 child가 stdin을 읽지 않으면 host thread가 block할 수 있습니다.

따라서 production host는 별도 slice/adapter에서 다음을 명시해야 합니다.

1. dedicated worker 혹은 platform-aware asynchronous I/O ownership,
2. bounded queue와 overload admission policy,
3. cancellation/disconnect가 in-flight blocking I/O를 깨우는 정확한 Windows/POSIX mechanism,
4. worker 결과를 delivery gate의 partial-frame ambiguity와 child shutdown sequence에 결합하는 방식,
5. stdout/stderr drain과 stdin writer의 deadlock-free lifecycle.

이 chapter는 selector, thread, event loop, process group, signal, close, timeout, retry를 구현하지
않습니다. `disconnect()`도 new frame만 막을 뿐 Popen stdin을 닫지 않습니다.

## 4. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_stdio_popen_input_owner.py
uv run pytest tests/volume03/test_mcp_popen_input.py -q
```

예상 출력입니다.

```text
correlation_id: mcp-stdio:string:popen-input-demo-001
frame_bytes: 67
poll_calls: 1
flush_calls: 1
state: open
```

예제와 tests는 `OfflinePopen`과 `OfflineBinaryWriter` fake만 사용합니다. 실제 `Popen`, executable,
OS pipe, shell, filesystem, network, external MCP server, Tool, process signal 또는 destructive action을
호출하지 않습니다. request method `safe/test`도 allowlisted-looking 교육용 문자열일 뿐 Tool 실행을
열지 않습니다.

## 5. 검증 경계

`tests/volume03/test_mcp_popen_input.py`는 다음을 fake seam으로 검증합니다.

1. live `poll() is None`일 때 captured stdin으로 immutable frame과 one flush를 전달한다.
2. cancelled request는 `poll()`·`write()`·`flush()` 전에 거부한다.
3. exited child는 writer I/O 없이 owner를 `DISCONNECTED`로 만들고 future delivery도 poll 없이 막는다.
4. poll failure detail은 숨기고 writer에 도달하지 않는다.
5. partial writer failure는 existing shutdown-required signal/state를 유지한다.
6. stdin replacement가 일어나도 construction-time snapshot만 사용한다.
7. missing/invalid stdin은 process poll 전에 거부한다.

## 6. 운영상 다음 단계

이 owner의 successful receipt은 local buffered stdin flush가 완료됐다는 뜻일 뿐 child JSON parser,
peer acknowledgement, Tool execution, exactly-once를 증명하지 않습니다. production에서는 Windows/POSIX
process group 및 signal semantics, exit-code restart/backoff, durable approval/audit/idempotency, tenant
identity와 Hermes/Codex integration을 별도의 tested boundary로 계속 구현해야 합니다.
