# MCP STDIO queued input delivery: claimed frame 결과를 보수적으로 map하기

## 1. 왜 queue와 Popen owner 사이에 작은 adapter가 필요한가

`McpStdioInputQueue`는 bounded admission과 single-worker claim만 소유하고, `McpStdioPopenInputOwner`
또는 `McpStdioInputDeliveryGate`는 one-frame local write의 cancellation·disconnect·partial-frame
경계를 소유합니다. 두 책임 사이에서 raw exception을 queue state로 흘리거나 worker가 여러 item을
동시에 claim하면 overload와 ambiguity ownership이 다시 섞입니다.

`deliver_next_mcp_stdio_queued_input()`은 host가 소유한 worker가 호출할 **한 번의 fake-model
adapter**입니다. open queue의 FIFO item 하나만 claim하여 injected delivery owner에 한 번 넘기고
result를 queue의 typed outcome으로 축소합니다.

```text
bounded queue -- claim one immutable item --> injected delivery owner
     |                                           |
     | no next claim while in-flight             | local receipt / typed failure
     v                                           v
queue resolution <--- delivered / not-delivered / ambiguous
                                                  |
                                 ambiguous -> queue shutdown-required signal
```

이 module은 worker/thread/event loop/Popen/pipe를 만들지 않고, child signal·close·restart, retry,
Tool 실행, network, filesystem 또는 audit를 호출하지 않습니다.

## 2. 좁은 계약

- `deliver_next_mcp_stdio_queued_input(queue, owner)`는 valid open queue에 pending item이 없으면
  owner를 호출하지 않고 `None`을 반환합니다. owner seam이 invalid이면 **claim 전**에 generic error로
  거부하여 queue를 바꾸지 않습니다.
- pending item이 있으면 FIFO item 하나를 exact in-flight object로 claim한 뒤 `owner.write()`를 정확히
  한 번 호출합니다. successful result에는 typed correlation ID, frame byte count, positive write count가
  일치하는 `McpStdioInputDeliveryReceipt`가 필요합니다. 이는 peer acknowledgement나 Tool execution
  보장이 아니라 local adapter contract 확인일 뿐입니다.
- matching local receipt는 `DELIVERED`로 resolve합니다. typed `McpStdioInputDeliveryError` 중
  `frame_may_be_partial=False` failure는 receiver가 frame bytes를 받지 않았다는 owner contract에 따라
  `NOT_DELIVERED`로 resolve합니다.
- partial delivery failure, unexpected exception, malformed/mismatched success receipt는 receiver state를
  알 수 없으므로 raw detail을 반사하지 않고 `AMBIGUOUS`로 보수적으로 resolve합니다. queue는 pending을
  버리고 `SHUTDOWN_REQUIRED`로 latch하며 resolution의 `child_shutdown_requested=True`는 caller가 별도
  shutdown boundary를 검토해야 한다는 signal입니다. 이 adapter가 shutdown side effect를 수행하지는
  않습니다.
- `disconnect()`가 item claim **뒤**에 발생하면 queued adapter는 already-owned in-flight delivery를
  interrupt하지 않고 그 결과를 한 번 resolve합니다. disconnect는 pending discard와 future claim block의
  queue policy입니다. Windows/POSIX blocking pipe write cancellation을 여기서 해결하지 않습니다.

## 3. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_stdio_queued_input_delivery.py
uv run pytest tests/volume03/test_mcp_queued_delivery.py -q
```

예상 출력입니다.

```text
correlation_id: mcp-stdio:string:queued-delivery-demo-001
outcome: delivered
write_calls: 1
state: open
```

예제와 tests는 fixed `safe/test` JSON-RPC object, immutable in-memory frame, fake delivery owner와
prebuilt receipt/error만 사용합니다. 실제 Popen, OS pipe, worker thread, process group, shell,
filesystem, network, MCP server, Tool 또는 destructive action은 호출하지 않습니다. `safe/test`는
allowlisted-looking 교육용 method 이름일 뿐 Tool 실행을 열지 않습니다.

## 4. 검증 경계

`tests/volume03/test_mcp_queued_delivery.py`는 fake seam으로 다음을 검증합니다.

1. FIFO claimed frame은 owner에 한 번 전달되고 `DELIVERED`로 resolve되며 next frame은 pending으로 남는다.
2. empty queue는 owner를 호출하지 않는다.
3. typed non-partial delivery failure는 `NOT_DELIVERED`로 map된다.
4. partial failure, unexpected adapter failure, malformed receipt는 raw detail 없이 `AMBIGUOUS`와
   caller-owned shutdown signal로 map된다.
5. claim 뒤 disconnect는 in-flight delivery를 interrupt하지 않되 future pending/claim을 막는다.
6. invalid owner는 claim과 delivery call 전에 거부되고 pending queue를 보존한다.

## 5. 운영 adapter로 잘못 확장하지 않기

이 adapter의 `DELIVERED`는 local write/flush receipt의 matching report일 뿐 child JSON parsing, remote
MCP response, Tool execution, idempotency 또는 exactly-once를 증명하지 않습니다. `NOT_DELIVERED`도
owner seam의 explicit contract에 한정되므로 durable request record·peer acknowledgement·approval
correlation 없이 blind retry를 정당화하지 않습니다.

실제 host worker는 platform-specific bounded I/O/cancellation mechanism과 process lifecycle을 별도
ownership으로 구현하고, 이 one-item result model의 conservative ambiguity signal을 shutdown supervisor에
전달해야 합니다. 다음 slice는 Windows/POSIX process group·signal semantics를 fake plan/fixture 경계로
분리한 뒤 exit-code restart/backoff, durable approval/audit/idempotency, Hermes/Codex integration을
독립적으로 다뤄야 합니다.
