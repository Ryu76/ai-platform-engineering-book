# MCP STDIO stream loop: EOF·전송 실패·안전한 JSON-RPC error 분리하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 이미 검증된 `McpStdioSession`을 host가 전달한 text input/output stream에만 연결한다.
- EOF, input read 실패, output write/flush 실패를 서로 다른 종료 조건으로 다룬다.
- 잘못된 request에는 예외 상세나 원문을 노출하지 않는 고정 JSON-RPC `-32600` response만 쓴다.
- output write가 실패하면 error response를 다시 쓰려 하지 않고 session을 닫는다.

## 2. stream 경계

`run_mcp_stdio_session(input_stream, output_stream, session)`은 `sys.stdin`과 `sys.stdout`을 직접 열지 않습니다. 신뢰된 host가 전달한 text stream에서 `readline()`으로 한 LF-framed message를 읽고, 기존 `McpStdioSession.receive_line()`의 response가 있을 때만 해당 stream에 한 번 `write()`하고 `flush()`합니다.

```text
trusted host
  ├─ injected input text stream
  │    └─ one line → McpStdioSession (framing + lifecycle + allowlist boundary)
  └─ injected output text stream
       └─ exactly one response write + flush

EOF                 → close session, return only aggregate counts
read failure        → close session, raise McpStdioTransportError
write/flush failure → close session, raise McpStdioTransportError; do not retry
invalid request     → fixed JSON-RPC -32600 response when it can be written
```

이 loop는 Tool, filesystem, shell, subprocess, network 또는 외부 MCP server를 추가로 열지 않습니다. `tools/call`은 여전히 명시적으로 구성한 `McpToolCallBoundary`가 있을 때만 기존 allowlist·Schema·approval·timeout/retry·audit 경계로 연결됩니다.

## 3. 안전한 error response

`McpStdioError`가 발생하면 runner는 아래처럼 고정된 envelope만 출력합니다.

```json
{"jsonrpc":"2.0","id":"invalid-001","error":{"code":-32600,"message":"Invalid request."}}
```

입력 예외 문자열, raw request, Tool arguments, handler 세부정보는 response에 포함하지 않습니다. runner는 JSON object가 duplicate key 없이 파싱되고 ID가 기존 canonical string/integer 규칙을 통과한 경우에만 그 ID를 echo합니다. ID가 boolean·float·`null`·제어 문자를 포함하거나 message가 모호하면 response ID는 `null`입니다.

valid ID가 너무 길어 `max_message_bytes` 안에 고정 error envelope를 담을 수 없을 때도 runner는 ID를 `null`로 바꾼 작은 error response만 시도합니다. 따라서 transport error를 보고하는 과정이 size 제한을 우회하지 않습니다.

output stream이 partial write를 보고하거나 write/flush에서 실패하면 response가 실제로 전달됐는지 알 수 없습니다. 이런 경우 runner는 같은 response나 다른 error를 재시도하지 않습니다. 재시도는 JSON-RPC request의 중복 실행·중복 response를 만들 수 있으므로 authenticated host가 별도의 idempotency 정책으로 설계해야 합니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_stdio_injected_stream_runner.py
uv run pytest tests/volume03/test_mcp_stdio.py -q
```

예제 출력은 다음과 같습니다.

```text
responses_written: 2
invalid_request_code: -32600
invalid_request_id: invalid-001
```

예제는 `io.StringIO`에 고정 handshake와 잘못된 protocol version request만 넣습니다. EOF 뒤 session은 닫히며, 실제 `sys.stdin`/`sys.stdout`, file, shell, subprocess, network, 외부 MCP server, destructive Tool은 사용하지 않습니다.

## 5. 검증하는 거부·종료 경계

| 상태 | 결과 |
|---|---|
| 정상 initialize → initialized notification → EOF | notification에는 response 없이 EOF에서 session close와 aggregate stats 반환 |
| protocol/version/lifecycle이 잘못된 request + canonical ID | 고정 `-32600` response; 예외 상세는 숨김 |
| boolean ID, duplicate key, 깨진 JSON | `id: null` 고정 error; 모호한 ID를 반사하지 않음 |
| 긴 valid ID로 error response가 max bytes 초과 | `id: null` fallback error만 기록 |
| input `readline()` 실패 | session close 후 transport exception; output을 쓰지 않음 |
| output `write()`/`flush()` 또는 partial write | session close 후 transport exception; retry/error write 없음 |

## 6. 운영 적용 시 추가할 것

이 loop의 `McpStdioRunStats`는 process-local aggregate count일 뿐 durable audit가 아닙니다. 실제 host integration에서는 subprocess lifecycle, OS pipe backpressure, UTF-8 decoder error policy, cancellation, signal handling, client disconnect, restart policy, authenticated identity, tenant isolation, idempotency key, append-only audit, redaction 및 metrics를 별도로 설계·검증해야 합니다.

특히 output write 실패 뒤 client가 response를 받았는지는 이 adapter가 알 수 없습니다. side-effecting Tool을 이 교육용 loop에 연결하지 말고, durable approval·idempotency·reconciliation이 있는 execution service에서 정확히 한 번에 대한 운영 정책을 정의하세요.

## 7. 완료 체크리스트

- [ ] runner가 host가 전달한 stream만 사용하고 `sys.stdin`/`sys.stdout`을 직접 열지 않는지 확인했다.
- [ ] EOF, read failure, write/flush failure가 모두 session close로 끝나는지 확인했다.
- [ ] invalid request response에 예외 상세·원문·Tool input이 없는지 확인했다.
- [ ] 모호하거나 oversized ID가 `null`로 처리되는지 확인했다.
- [ ] write failure에서 재시도하지 않는 테스트를 실행했다.
- [ ] 예제와 테스트가 실제 destructive action 없이 실행됐는지 확인했다.
