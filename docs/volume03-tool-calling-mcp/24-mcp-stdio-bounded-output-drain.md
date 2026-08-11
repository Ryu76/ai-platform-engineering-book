# MCP STDIO bounded output drain: 한 binary pipe를 byte ceiling 안에서 EOF까지 수집하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- MCP child output을 text가 아닌 binary bytes로 먼저 수집한다.
- `stdout` 또는 `stderr`라는 고정 channel과 launch plan과 같은 finite byte budget만 받는다.
- ceiling을 넘는 첫 byte를 감지한 즉시 실패하고 이후 input을 더 읽지 않는다.
- fake readable stream으로 raw pipe, subprocess, decode, logging 없이 read 경계를 검증한다.

## 2. single-stream ownership 경계

앞 장의 `McpStdioSubprocessFactory`는 binary stdout/stderr pipe topology를 만들 수 있지만,
그 pipe를 읽지는 않았습니다. `drain_mcp_stdio_binary_stream()`은 **이미 trusted host가 소유한
한 stream**만 EOF까지 synchronous하게 수집하는 작은 adapter입니다.

```text
trusted host-owned binary stream
             │ fixed 4 KiB-or-less reads
             ▼
     bounded raw-byte collector
             │ EOF only
             ▼
immutable stdout/stderr capture
```

입력에는 stream object, exact `stdout`/`stderr`, 1,024–1,048,576 byte budget만 있습니다.
MCP peer나 model이 file path, stream attribute name, chunk size, decode encoding, log label,
subprocess option을 제공할 수 없습니다. 이 함수는 Tool을 실행하지 않습니다.

## 3. overflow를 위한 한 byte sentinel

각 `read()`는 남은 budget보다 최대 한 byte만 더 요청합니다.

1. accumulator가 비어 있고 budget이 1,024이면 첫 read size는 `min(4096, 1025)`입니다.
2. 반환 chunk가 1,024 byte 이하이면 accumulator에 보관합니다.
3. 1,025번째 byte가 반환되면 `exceeded byte budget`으로 실패합니다.
4. 실패 후 read 재시도, partial capture 반환, decode, logging, child terminate를 하지 않습니다.

따라서 cooperative binary stream에서는 이 adapter가 한 read에서 보관할 untrusted output이
`max_bytes + 1`을 넘지 않습니다. `read(size)` 계약을 무시하고 size보다 큰 bytes를 반환하는
adapter는 `violated read bound`로 거부합니다. stream read exception과 non-bytes 반환도 raw
adapter detail 없이 generic error로 좁힙니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_stdio_bounded_stream_drain.py
uv run pytest tests/volume03/test_mcp_stream_drain.py -q
```

예제 출력은 다음과 같습니다.

```text
channel: stdout
captured_bytes: 18
read_calls: 3
```

`OfflineReadableStream`은 메모리의 고정 `bytes` list만 반환합니다. 예제와 테스트는 actual
subprocess, OS pipe, shell, process signal, filesystem, network, external MCP server, Tool,
destructive action을 실행하지 않습니다.

## 5. 검증하는 허용·거부 경계

| 입력/상태 | 처리 |
|---|---|
| `stdout` + 1,024 byte budget + EOF | raw bytes immutable snapshot 반환 |
| `stderr` + configured ceiling | 같은 algorithm으로 별도 capture 반환 |
| ceiling보다 정확히 한 byte 큰 chunk | 첫 read 뒤 overflow로 실패; 다음 read 없음 |
| `read(size)`보다 큰 bytes | stream contract violation으로 거부 |
| `bytearray`/`str`/other non-bytes | decode 전에 거부 |
| read exception | raw adapter detail 없는 generic read failure |
| `stdin`, custom channel, boolean/tiny/huge budget | read 전에 거부 |

## 6. 아직 의도적으로 제외한 운영 책임

이 collector는 stdout/stderr를 **동시에** 소비하지 않습니다. production host가 한 pipe만
blockingly drain하면 반대 pipe의 child write가 막혀 deadlock/backpressure가 생길 수 있습니다.
따라서 다음 단계는 fake schedulable streams로 two-pipe interleaving ownership과 aggregate
failure policy를 별도로 설계·검증해야 합니다.

또한 다음은 이 slice의 책임이 아닙니다.

- UTF-8 decode, JSON-RPC LF framing, invalid byte redaction, sensitive diagnostic logging
- stdin framing/write/flush, partial write, peer disconnect, cancellation propagation
- overflow 때 child shutdown을 누가 요청할지와 process group/signal semantics
- child exit classification, finite restart/backoff, metrics, durable audit/idempotency

특히 captured stderr 또는 stdout을 user-facing error에 그대로 넣지 마세요. byte capture와
redaction/observability policy는 서로 다른 보안 경계입니다.

## 7. 완료 체크리스트

- [ ] only `stdout`/`stderr` channel과 finite byte budget을 허용하는지 확인했다.
- [ ] EOF capture가 raw immutable bytes이고 decoding을 하지 않는지 확인했다.
- [ ] overflow sentinel 뒤에는 더 읽지 않고 raw detail을 노출하지 않는지 확인했다.
- [ ] fake readable stream만으로 success, overflow, contract violation, read failure를 검증했다.
- [ ] concurrent drain, decode/redaction, stdin, shutdown/restart가 별도 작업임을 확인했다.
