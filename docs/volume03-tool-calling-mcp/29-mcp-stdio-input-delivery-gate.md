# MCP STDIO input delivery gate: cancellation·disconnect·partial frame을 새 write와 분리하기

## 1. 왜 writer 위에 별도 gate가 필요한가

`write_mcp_stdio_input_frame()`은 immutable JSON-RPC frame을 bounded binary writer에 보내고,
write/flush 실패가 나면 receiver가 prefix 또는 complete frame을 이미 받았을 수 있음을
`frame_may_be_partial=True`로 표시합니다. 그러나 이 신호만으로는 host가 다음 frame을 보내도 되는지,
같은 요청을 재시도해도 되는지, child 종료를 누가 소유하는지가 정해지지 않습니다.

`McpStdioInputDeliveryGate`는 이 책임을 좁게 분리합니다.

```text
trusted typed JSON-RPC ID ──> delivery gate ──> bounded writer
                                   │                   │
                   cancelled/disconnected: no I/O      partial failure
                                   │                   │
                              reject new frame    shutdown_required signal
```

이 module은 subprocess, pipe, child terminate/kill, retry, Tool 실행, durable idempotency,
audit sink, network를 호출하지 않습니다. 실제 child 종료는 기존 host shutdown boundary를 소유한
caller가 판단·실행해야 합니다.

## 2. 좁은 계약

- `cancel(request_id)`는 typed JSON-RPC correlation ID 하나를 취소합니다. string ID `"7"`과
  integer ID `7`은 다른 요청이므로 서로의 취소 상태를 공유하지 않습니다.
- 취소된 ID의 아직 시작하지 않은 write는 writer I/O 전에 `frame_may_be_partial=False`로 거부합니다.
  이미 peer에 전달된 frame을 취소하거나 Tool을 중단하지는 않습니다.
- `disconnect()`는 `OPEN` gate를 `DISCONNECTED`로 바꾸고 이후의 모든 새 frame을 writer I/O 전에
  막습니다. pipe를 닫거나 child를 종료하지는 않습니다.
- bounded writer가 `frame_may_be_partial=True` failure를 보고하면 gate는 `SHUTDOWN_REQUIRED`가 됩니다.
  동일하거나 다른 ID를 blind retry하지 않고 이후 새 frame을 막습니다. error의
  `child_shutdown_requested=True`는 **caller가 child shutdown을 검토해야 한다는 신호**이며,
  이 module이 shutdown side effect를 수행했다는 뜻이 아닙니다.
- invalid request ID, invalid frame 또는 invalid writer는 writer의 기존 validation을 그대로 따릅니다.
  adapter error detail과 raw frame bytes를 error에 반사하지 않습니다.

## 3. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_stdio_input_delivery_gate.py
uv run pytest tests/volume03/test_mcp_input_delivery.py -q
```

예상 출력입니다.

```text
correlation_id: mcp-stdio:string:delivery-demo-001
frame_bytes: 64
flush_calls: 1
state: open
```

예제는 고정 JSON-RPC object와 in-memory `OfflineBinaryWriter`만 사용합니다. actual Popen,
OS pipe, shell, filesystem, network, MCP server, Tool 또는 destructive action은 없습니다.

## 4. 검증 경계

`tests/volume03/test_mcp_input_delivery.py`는 fake writer로 다음을 검증합니다.

1. 취소된 typed request ID는 한 번의 `write()`나 `flush()`도 수행하지 않는다.
2. string/integer JSON-RPC ID의 cancellation state가 혼동되지 않는다.
3. explicit disconnect는 새 frame만 차단하고 child shutdown side effect를 하지 않는다.
4. partial write failure 뒤에는 generic ambiguity error, caller-owned shutdown signal, gate의
   `SHUTDOWN_REQUIRED` 전이와 이후 frame 차단이 함께 발생한다.
5. invalid ID는 writer I/O 전에 generic error로 거부된다.

## 5. 운영 adapter로 잘못 확장하지 않기

이 gate의 성공 receipt도 peer acknowledgement나 exactly-once 보장이 아닙니다. partial frame
failure 뒤 재시도 여부는 receiver acknowledgement, durable idempotency record, request type,
승인 상태를 함께 검토해야 합니다. cancellation도 이미 peer가 받은 frame이나 실행 중인 Tool을
자동 중단하지 않습니다.

다음 adapter slice에서 actual Popen stdin ownership·backpressure, Windows/POSIX process group과
signal, exit-code restart/backoff, durable approval/audit/idempotency, Hermes/Codex integration을
각각 독립적으로 설계·검증해야 합니다.
