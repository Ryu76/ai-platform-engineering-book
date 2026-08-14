# MCP STDIO ready drain: fake readiness snapshot에서만 읽기

## 1. 왜 readiness와 read를 분리하는가

앞 장의 round-robin 모델은 두 synchronous fake stream을 번갈아 읽습니다. 실제 pipe에서는
`read()`가 block할 수 있으므로, **읽어도 되는 순간을 정하는 adapter**와 bounded raw-byte
collector를 같은 함수에 섞으면 selector handle, child lifecycle, cancellation, backpressure의
책임이 불명확해집니다.

이 장의 `drain_mcp_stdio_ready_stream_pair()`는 real selector·thread·event loop를 열지 않습니다.
trusted host가 주입한 **fake readiness scheduler**의 immutable snapshot에서 ready로 선언된
in-memory binary stream만 fixed `stdout`, 다음 `stderr` 순서로 최대 한 번씩 읽습니다.

```text
trusted fake scheduler ──> ready snapshot ──> bounded one-turn read
                                      │                 │
                              stdout then stderr        ▼
                                                   raw byte pair
```

## 2. 좁은 계약

- `stdout_stream`, `stderr_stream`은 서로 다른 `read(size) -> bytes` object여야 합니다.
- scheduler는 매 round에 `McpStdioReadyChannels(stdout_ready, stderr_ready)`만 반환합니다.
  두 flag는 truthy 값이 아닌 `bool`이어야 합니다.
- 아직 EOF가 아닌 channel만 ready가 될 수 있습니다. closed channel을 다시 ready로 선언한 stale
  snapshot은 read 전에 거부합니다.
- 둘 다 ready가 아닌 snapshot도 busy wait 또는 재시도하지 않고 실패합니다. 이 fake boundary에는
  blocking wait ownership이 없기 때문입니다.
- 한 snapshot에서는 ready인 open channel만 한 번 읽고, 순서는 항상 stdout 뒤 stderr입니다.
  각 output은 독립적인 1,024–1,048,576 byte ceiling 및 4 KiB-or-less / one-byte overflow
  sentinel을 사용합니다.
- 두 output이 EOF일 때만 immutable raw-byte pair capture를 반환합니다. scheduler failure,
  malformed snapshot, read failure, non-bytes, read-bound violation, overflow에는 partial output을
  반환하지 않으며 scheduler와 stream을 더 호출하지 않습니다.

scheduler exception의 selector/handle detail과 stream exception의 raw detail은 external error에
포함하지 않습니다. 이 함수는 decode, redaction, logging 또는 child terminate도 수행하지 않습니다.

## 3. 안전한 오프라인 실습

저장소 루트에서 다음을 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_stdio_ready_drain.py
uv run pytest tests/volume03/test_mcp_ready_drain.py -q
```

예상 출력입니다.

```text
stdout_bytes: 10
stderr_bytes: 10
turns: stdout,stderr,stdout,stderr,stdout,stderr
```

예제의 stream과 scheduler는 메모리의 fixed bytes/list만 사용합니다. subprocess, OS pipe,
selector, shell, filesystem, network, external MCP server, Tool 실행 및 destructive action은 없습니다.

## 4. 검증 경계

`tests/volume03/test_mcp_ready_drain.py`는 다음을 fake seam으로 검증합니다.

1. 한 snapshot의 ready stream당 최대 한 read와 deterministic stdout-then-stderr 순서
2. stdout EOF 뒤 scheduler에게 전달되는 open state와 stdout skip
3. no-progress 및 closed channel stale-ready snapshot의 read 전 거부
4. overflow 뒤 같은 snapshot의 stderr, 다음 scheduler round, partial capture를 모두 막는 정책
5. scheduler failure/invalid snapshot의 detail 은닉, non-boolean flags, invalid scheduler/stream/budget의
   IO 전 거부

## 5. 운영 adapter로 잘못 확장하지 않기

이 모델은 actual pipe readability, wakeup, fairness, EOF notification을 증명하지 않습니다.
production adapter는 OS별 selector 또는 thread/async runtime으로 readiness를 얻고, bounded queue와
backpressure, cancellation/disconnect, stream failure 시 child shutdown 요청의 owner를 명시해야 합니다.
특히 readiness snapshot이 없다고 이 함수에 polling loop나 sleep을 추가하지 마세요.

UTF-8/JSON-RPC decode·framing, sensitive-output redaction/observability, stdin partial write/flush,
process group/signal, exit-code restart/backoff, durable approval/audit/idempotency 및 Hermes/Codex
integration도 별도 slice의 책임입니다.
