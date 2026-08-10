# MCP STDIO lifecycle: JSON-RPC 한 줄과 handshake를 좁게 검증하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- STDIO MCP 메시지를 **LF 한 줄 JSON-RPC 2.0 object**로만 받도록 framing을 검증한다.
- 문자 수가 아닌 UTF-8 byte 수로 input/output message 상한을 적용한다.
- 고정한 MCP protocol version과 `initialize` → `notifications/initialized` lifecycle을 검증한다.
- transport envelope 검증과 Tool 실행·승인·감사 경계를 분리한다.

## 2. 이번 adapter의 의도적인 범위

`mcp/stdio.py`의 `McpStdioSession`은 실제 `sys.stdin`/`sys.stdout`를 열지 않는 순수 in-memory adapter입니다. 호출자가 하나의 input line을 `receive_line()`에 전달하면, `initialize` request에 대해서만 stdout에 쓸 수 있는 response line 하나를 돌려줍니다.

고정 protocol version은 `2025-03-26`이며 이 장의 작은 계약에서만 사용합니다. 버전 협상, 최신 MCP 기능 전체, JSON-RPC batch, cancellation, HTTP transport, subprocess, SDK, 실제 Server는 구현하지 않습니다. protocol version을 유사하게 보정하거나 fallback하지 않습니다.

또한 session은 `tools/list`와 `tools/call`을 처리하지 않습니다. 따라서 JSON-RPC의 `id`, `method`, `params`가 `McpToolCallRequest.arguments`, `ApprovalGrant`, audit event에 섞이지 않으며 handler도 호출되지 않습니다. 다음 장에서 Tool method를 추가한다면 envelope를 별도로 검증한 뒤 `dispatcher.py`의 좁은 실행 경계에만 명시적으로 연결해야 합니다.

## 3. framing과 lifecycle 계약

입력과 출력은 각각 정확히 하나의 JSON object와 끝의 LF (`\n`)로 구성됩니다. CRLF, LF 없는 문자열, 한 frame 안의 두 JSON object는 거부합니다. UTF-8 인코딩 후 기본 16,384 byte를 넘는 message도 거부합니다. 한 줄만 stdout에 쓰는 transport는 로그·debug 출력도 stdout이 아니라 별도 안전한 관측 경로로 보내야 합니다.

```text
client input line
  │ parse_stdio_jsonrpc_line()
  │ - one LF frame, UTF-8 byte limit, strict JSON, duplicate key rejection
  │ - JSON-RPC "2.0", string/integer ID, object params
  ▼
WAITING_FOR_INITIALIZE
  │ initialize request + exact protocolVersion + minimal client envelope
  ▼
WAITING_FOR_INITIALIZED ── initialize response line
  │ notifications/initialized (notification; params 없음)
  ▼
READY
  │ this chapter: no methods enabled; no Tool handler or audit sink
  ▼
reject any further method
```

`initialize` request에는 non-empty string 또는 integer JSON-RPC ID가 있어야 합니다. `protocolVersion`, object `capabilities`, `clientInfo.name`, `clientInfo.version`도 모두 필요합니다. `clientInfo`에는 정확히 `name`과 `version`만 허용합니다. 이 엄격한 교육용 profile은 transport metadata의 모호한 확장을 먼저 거부하는 데 목적이 있습니다.

`notifications/initialized`는 ID와 params가 없는 notification이어야 하며, initialize response를 받은 뒤에만 허용됩니다. `close()` 뒤에는 새 input을 받지 않습니다. 유효하지 않은 frame/lifecycle에는 response를 만들어 추측하지 않고 `McpStdioError`를 발생시킵니다. 실제 server라면 검토된 JSON-RPC error mapping, stderr logging, 종료 정책을 별도 설계하세요.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_stdio_lifecycle.py
uv run pytest tests/volume03/test_mcp_stdio.py -q
```

예제 출력은 다음과 같습니다.

```text
2025-03-26: ready
```

예제는 고정한 initialize JSON 두 줄을 메모리에서 주고받습니다. 파일, 환경 변수, 실제 표준 입출력, 셸, subprocess, 네트워크, 외부 MCP Server, Tool handler를 사용하지 않습니다. 반환된 response는 출력 형식 확인용으로 `json.loads()`만 하며 Tool 실행을 요청하지 않습니다.

## 5. 코드 읽기 순서

1. `parse_stdio_jsonrpc_line()`이 LF framing과 UTF-8 byte 상한을 먼저 확인하는지 봅니다.
2. JSON parser가 duplicate key와 `NaN`/`Infinity`를 거부하는지 봅니다.
3. `McpStdioSession.receive_line()`이 initialize 전·후 state를 구분하는지 봅니다.
4. `_validate_initialize_params()`가 protocol version과 client envelope를 정확히 검증하는지 봅니다.
5. `encode_stdio_jsonrpc_message()`가 compact JSON 한 줄에 LF를 붙이고 output 크기도 다시 확인하는지 봅니다.
6. 테스트에서 protocol version 불일치, CRLF/multiple frames, byte limit, Tool method 미실행을 확인합니다.

## 6. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `STDIO message must end with one LF` | transport가 frame terminator 없이 문자열을 전달했습니다. | `readline()` 단위처럼 정확히 한 LF frame만 adapter에 전달합니다. |
| `STDIO message exceeds ... bytes` | UTF-8 기준 input/output이 정책 상한을 넘었습니다. | 상한을 무제한으로 풀지 말고 검토된 최대 크기와 pagination/chunking 계약을 별도로 설계합니다. |
| `unsupported MCP protocol version` | 고정 profile과 다른 protocol version을 보냈습니다. | 임의 fallback 대신 지원 version을 명시적으로 추가·테스트합니다. |
| `initialize must be followed by notifications/initialized` | handshake 순서나 notification 형태가 맞지 않습니다. | initialize response 뒤 ID·params 없는 initialized notification을 하나만 보냅니다. |
| `no MCP methods are enabled` | 이 장의 adapter는 실행 method를 의도적으로 제공하지 않습니다. | Tool 요청을 직접 실행하지 말고 다음 실행 adapter에서 dispatcher·allowlist·승인 경계로 연결합니다. |

## 7. 운영 적용 시 추가할 것

실제 STDIO MCP server에는 stdin EOF 처리, stderr-only 구조화 logging, JSON-RPC error response, protocol version 지원표, request ID collision 정책, batch/cancellation 정책, deadline, authentication/tenant boundary, rate/concurrency limit, backpressure, output flush·broken pipe 정책, durable redacted audit sink를 추가해야 합니다.

특히 stdio로 전달된 `tools/call`을 곧바로 handler나 subprocess로 넘기면 안 됩니다. Tool 이름과 object arguments를 별도 parser로 좁힌 뒤에도 `ToolRegistry`, 위험도·사람 승인, timeout/retry, 최소 감사의 기존 dispatcher 경계를 반드시 다시 통과시켜야 합니다. 외부 부작용과 강한 cancellation은 이 교육용 thread timeout이 아니라 권한·멱등성·보상 기능을 갖춘 adapter에서 다룹니다.

## 8. 완료 체크리스트

- [ ] 한 input/output frame이 하나의 LF-종료 UTF-8 JSON object인지 확인했다.
- [ ] UTF-8 byte message 상한과 duplicate key/non-standard number 거부를 확인했다.
- [ ] 고정 protocol version 및 initialize lifecycle이 순서 밖 input을 거부하는지 확인했다.
- [ ] STDIO envelope가 Tool arguments·승인·감사에 섞이지 않고 handler를 호출하지 않는지 확인했다.
- [ ] 예제와 테스트를 실제 표준 입출력·외부 서버·파괴 작업 없이 실행했다.
