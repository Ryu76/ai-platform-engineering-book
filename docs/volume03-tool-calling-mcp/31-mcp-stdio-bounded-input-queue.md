# MCP STDIO bounded input queue: worker ownership·overload·ambiguity를 실제 I/O와 분리하기

## 1. 왜 synchronous `write()` 앞에 queue policy가 필요한가

`McpStdioPopenInputOwner`는 captured stdin과 live child를 확인하지만, synchronous pipe `write()`는
child가 stdin을 읽지 않을 때 host thread를 block할 수 있습니다. 여러 producer가 raw handle을 직접
호출하면 overload에서 무제한 frame을 쌓거나 cancellation·disconnect와 worker 결과가 경쟁할 수
있습니다.

`McpStdioInputQueue`는 worker 구현 **앞**의 작은 policy model입니다. immutable JSON-RPC frame의
bounded pending admission, 한 worker의 FIFO claim, typed result 기록만 제공합니다. worker, thread,
event loop, Popen, pipe 또는 실제 write를 만들지 않습니다.

```text
trusted immutable frame ──> bounded pending queue ──> one claimed item ──> host-owned worker
                                  │                        │                    │
                    full/cancel/disconnect: no I/O     no second claim      typed outcome only
                                                                             ambiguous -> shutdown signal
```

## 2. 좁은 계약

- constructor의 `max_pending_frames`는 1–128의 명시적 pending-frame budget입니다. pending queue가
  full이면 caller는 `McpStdioInputQueueError`를 받고 frame을 writer에 전달하지 않습니다. claim된
  in-flight frame은 worker ownership이므로 pending budget에는 포함하지 않습니다.
- `offer(request_id, frame)`는 existing immutable `McpStdioInputFrame`과 typed JSON-RPC ID를 받습니다.
  string ID `"7"`와 integer ID `7`은 다른 correlation ID입니다. 같은 correlation ID를 pending 또는
  in-flight 상태에서 중복 admission할 수 없습니다.
- `claim_next()`는 open queue에서만 FIFO item 하나를 single worker로 넘깁니다. worker가 `resolve()`하지
  않은 동안 두 번째 item을 claim할 수 없습니다. 이 model은 worker를 시작하거나 scheduling하지 않습니다.
- `cancel(request_id)`는 아직 claim되지 않은 matching frame을 제거하고 이후 같은 typed ID admission을
  막습니다. 이미 worker가 claim한 frame의 blocking I/O를 interrupt하거나 remote Tool을 취소하지 않습니다.
- `disconnect()`는 아직 pending인 frame을 버리고 새로운 admission/claim을 막습니다. in-flight worker,
  Popen stdin close, process signal, child shutdown은 caller-owned boundary입니다.
- worker는 exact claimed object에 `DELIVERED`, `NOT_DELIVERED`, `AMBIGUOUS` 중 하나만 한 번 반환합니다.
  `AMBIGUOUS`는 receiver가 prefix 또는 complete frame을 받았을 수 있다는 뜻이므로 pending frame을
  버리고 `SHUTDOWN_REQUIRED`로 latch합니다. resolution의 `child_shutdown_requested=True`는 caller가
  별도 shutdown sequence를 검토해야 한다는 signal이며 이 module이 process를 종료했다는 뜻이 아닙니다.

## 3. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_stdio_bounded_input_queue.py
uv run pytest tests/volume03/test_mcp_input_queue.py -q
```

예상 출력입니다.

```text
correlation_id: mcp-stdio:string:queue-demo-001
outcome: delivered
pending_frames: 1
state: open
```

예제와 tests는 fixed JSON-RPC object, immutable in-memory frame 및 enum outcome만 사용합니다. 실제
Popen, OS pipe, thread, event loop, shell, filesystem, network, MCP server, Tool 또는 destructive action은
호출하지 않습니다. `safe/test`는 allowlisted-looking 교육용 method 문자열일 뿐 Tool 실행을 열지 않습니다.

## 4. 검증 경계

`tests/volume03/test_mcp_input_queue.py`는 process/worker fake 없이 다음 policy를 검증합니다.

1. bounded FIFO admission과 one-at-a-time claim을 검증한다.
2. string/integer typed ID가 cancellation state를 공유하지 않음을 검증한다.
3. cancelled in-flight item을 queue가 interrupt·requeue하지 않음을 검증한다.
4. disconnect가 pending frame을 버리고 no-shutdown-signal로 future admission/claim을 막음을 검증한다.
5. ambiguous outcome이 pending frame을 버리고 caller-owned shutdown signal/state로 전이함을 검증한다.
6. forged/stale worker item, invalid outcome, capacity, ID, frame이 state mutation 전에 거부됨을 검증한다.

## 5. 운영 adapter로 잘못 확장하지 않기

이 queue의 `DELIVERED`는 local worker가 reported한 policy outcome일 뿐 peer acknowledgement, child JSON
parse, Tool execution 또는 exactly-once receipt가 아닙니다. `NOT_DELIVERED`도 worker seam의 contract에
의존하므로 durable idempotency 없이 application-level blind retry를 정당화하지 않습니다.

다음 slice는 Windows/POSIX별 blocking I/O cancellation mechanism을 직접 추측하지 않고, actual worker
adapter가 이 queue에서 claim한 immutable item을 bounded delivery gate/Popen owner에 전달한 뒤 outcome을
어떻게 보수적으로 map할지를 tested seam으로 분리해야 합니다. 그 뒤 process group·signal, exit-code
restart/backoff, durable approval/audit/idempotency, Hermes/Codex integration을 별도로 다뤄야 합니다.
