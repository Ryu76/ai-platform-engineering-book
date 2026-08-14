# MCP STDIO bounded stdin write: immutable JSON-RPC frame을 partial write/flush 경계로 보내기

## 1. 왜 stdin write를 output drain과 분리하는가

stdout/stderr drain은 child가 낸 raw bytes를 수집하는 경계입니다. 반대로 stdin은 host가 MCP
peer에 JSON-RPC frame을 **전송**하는 방향입니다. 이 둘을 Popen factory 또는 child shutdown에 섞으면
short write 뒤 peer가 어떤 prefix를 받았는지, flush failure 뒤 request를 재전송해도 되는지가
불명확해집니다.

`write_mcp_stdio_input_frame()`은 trusted host가 이미 만든 immutable
`McpStdioInputFrame`과 injected binary writer만 받습니다. subprocess, OS pipe 생성, shell,
filesystem, network, external MCP server, Tool 또는 destructive action을 실행하지 않습니다.

```text
reviewed JSON-RPC object ──> immutable UTF-8 LF frame ──> <= 4 KiB binary writes ──> one flush
                                       │                         │                     │
                                  invalid: no write       short positive: continue    failure: ambiguous
```

## 2. 좁은 계약

- `build_mcp_stdio_input_frame()`은 dict request/notification을 기존 strict JSON-RPC encoder와 parser로
  round-trip 검증합니다. exact `jsonrpc="2.0"`, one LF frame, valid method/ID/params, 16 KiB byte
  ceiling을 넘는 raw bytes나 malformed envelope는 writer 전에 거부합니다.
- `McpStdioInputFrame`은 immutable `bytes`만 보관합니다. 임의 bytes, invalid UTF-8, CR/LF smuggling,
  incomplete frame은 생성 시점에 거부합니다.
- `write_mcp_stdio_input_frame()`은 host-owned `write(bytes) -> int`와 `flush()` seam만 씁니다.
  요청 chunk는 최대 4 KiB입니다. positive short write는 아직 보내지 않은 suffix에만 이어서 write합니다.
- 모든 bytes가 전송된 후에만 flush를 정확히 한 번 요청합니다. successful receipt은 local writer가
  flush를 마쳤다는 뜻일 뿐 peer가 JSON을 parse했거나 Tool을 실행했다는 receipt가 아닙니다.
- write exception, zero/negative/boolean/non-integer/oversized count, flush exception은
  `McpStdioInputWriteError(frame_may_be_partial=True)`로 끝납니다. receiver가 frame prefix 또는
  complete frame을 이미 받았을 수 있으므로 이 boundary는 retry, child terminate, audit/log emission을
  하지 않습니다.

## 3. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_stdio_bounded_input_write.py
uv run pytest tests/volume03/test_mcp_input_write.py -q
```

예상 출력입니다.

```text
frame_bytes: 55
write_calls: 1
flush_calls: 1
```

예제는 memory-only `OfflineBinaryWriter`와 source에 고정한 `notifications/initialized` notification만
사용합니다. actual child process, OS pipe, shell, filesystem, network, MCP server, Tool 및 destructive
action은 없습니다.

## 4. 검증 경계

`tests/volume03/test_mcp_input_write.py`는 fake binary writer로 다음을 검증합니다.

1. valid immutable frame을 완결 write하고 flush를 한 번 호출한다.
2. positive short write에서는 raw frame을 다시 encode하지 않고 unsent suffix만 계속 전송한다.
3. large but bounded frame의 각 write가 4 KiB를 넘지 않는다.
4. zero/negative/boolean/non-integer/oversized count, write exception, flush exception에는 추가 write,
   flush 재시도, partial receipt가 없고 partial-frame ambiguity가 표시된다.
5. malformed/raw/oversized frame, invalid writer는 어떠한 write 전에 거부된다.

## 5. 운영 adapter로 잘못 확장하지 않기

`flush()` 성공은 remote acknowledgement나 exactly-once semantics가 아닙니다. disconnect 또는 failure
뒤 같은 JSON-RPC ID/request를 blind retry하면 peer가 이미 complete frame을 받았을 때 duplicate Tool
execution이 될 수 있습니다. production host는 typed request ID, durable idempotency record,
peer acknowledgement, cancellation/disconnect policy와 retry decision ownership을 별도로 설계해야 합니다.

또한 this slice는 Popen stdin handle ownership, actual pipe backpressure, child shutdown request,
Windows/POSIX process group/signal, exit-code restart/backoff, durable approval/audit 및 Hermes/Codex
integration을 구현하지 않습니다. 각 책임은 separate adapter slice에서 verification해야 합니다.
