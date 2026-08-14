# MCP STDIO `tools/list`: handshake 뒤 allowlist catalog만 읽기 전용으로 노출하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 완료된 `initialize` lifecycle 뒤에만 JSON-RPC `tools/list` request를 받는다.
- `McpServerCatalog`의 복사본을 response로 투영하고 Tool handler를 호출하지 않는다.
- response ID를 request ID에만 묶고, notification·비어 있지 않은 params·다른 method를 거부한다.
- catalog 조회와 `tools/call` 실행·승인·감사 경계를 계속 분리한다.

## 2. 의도적으로 좁은 transport profile

`mcp/stdio.py`의 `McpStdioSession`은 앞 장의 LF 한 줄 framing, UTF-8 byte 상한, strict JSON, JSON-RPC 2.0 및 고정 `2025-03-26` initialize lifecycle을 그대로 사용합니다. `READY` state에서는 request ID가 있는 `tools/list`만 추가로 허용합니다.

```text
initialize → initialized notification → READY
                                      │
                                      ├─ tools/list + request ID + empty/no params
                                      │     └─ McpServerCatalog.list_tools() snapshot response
                                      │
                                      └─ tools/call, unknown method, notification, non-empty params
                                            └─ reject; dispatcher/handler/audit 없음
```

`McpServerCatalog`는 `ToolRegistry`의 allowlisted 정의를 handler 없이 복사하는 읽기 전용 projection입니다. 따라서 이 adapter가 목록을 반환해도 계산기·텍스트 변환 함수를 포함한 어떤 handler도 실행하지 않습니다. catalog 생성 뒤 registry가 변경돼도 catalog의 정의 snapshot은 바뀌지 않습니다.

이 작은 profile은 pagination cursor, `tools/listChanged` notification, tool annotations, protocol version 협상, batch, cancellation, 실제 `sys.stdin`/`sys.stdout`, subprocess, HTTP, SDK 및 외부 MCP server를 구현하지 않습니다. `params`가 없거나 빈 object일 때만 같은 안전한 목록을 반환하고, cursor 같은 확장 metadata를 추측해 해석하지 않습니다.

## 3. response 계약

성공 response는 compact UTF-8 JSON 한 줄과 LF로 인코딩됩니다.

```json
{
  "jsonrpc": "2.0",
  "id": "list-001",
  "result": {
    "tools": [
      {
        "name": "safe_calculator",
        "description": "두 유한 수의 허용된 사칙연산을 수행합니다. 외부 시스템을 변경하지 않습니다.",
        "inputSchema": {"type": "object"}
      }
    ]
  }
}
```

`id`는 caller가 보낸 string 또는 integer를 변경하지 않고 되돌립니다. ID 없는 `tools/list` notification에는 response를 만들지 않고 오류를 발생시킵니다. response 생성도 기존 byte 상한으로 다시 확인하므로 큰 catalog를 무제한 stdout에 쓰지 않습니다. 실제 server에서 pagination을 추가하려면 cursor의 형식·무결성·상한과 response 크기 계약을 따로 설계·검증하세요.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_stdio_tools_list.py
uv run pytest tests/volume03/test_mcp_stdio.py -q
```

출력은 다음과 같습니다.

```text
safe_calculator, safe_text_case: listed
```

예제는 코드 안에 명시한 `SAFE_CALCULATOR`, `SAFE_TEXT_CASE` 정의로 catalog snapshot을 만들고, 고정한 in-memory JSON-RPC 세 줄만 처리합니다. 파일, 환경 변수, 실제 표준 입출력, 셸, subprocess, 네트워크, 외부 MCP server를 사용하지 않습니다. 특히 `tools/call`을 보내지 않으므로 Tool 실행·승인·timeout/retry·감사 기록도 발생하지 않습니다.

## 5. 코드 읽기 순서

1. `McpStdioSession.__init__()`이 catalog를 받거나 빈 고정 catalog를 만드는지 확인합니다.
2. `receive_line()`이 READY 이전 lifecycle을 먼저 검사하는지 확인합니다.
3. `_receive_ready_request()`가 method, request ID, empty params를 확인하는지 봅니다.
4. `McpServerCatalog.list_tools()`의 독립 snapshot만 `result.tools`에 넣는지 확인합니다.
5. `encode_stdio_jsonrpc_message()`가 response framing·byte 상한을 다시 적용하는지 확인합니다.
6. 테스트에서 handler 없는 catalog projection, notification 거부, non-empty params 거부, `tools/call` 미실행을 확인합니다.

## 6. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `tools/list must include a JSON-RPC request id` | response를 받지 않는 notification을 보냈습니다. | 고유한 string/integer request ID를 붙여 request로 보냅니다. |
| `tools/list params must be empty when present` | 이 profile이 지원하지 않는 cursor/metadata를 보냈습니다. | metadata를 무시하지 말고, 필요한 pagination 계약을 별도 adapter로 명시·테스트합니다. |
| `no MCP methods are enabled besides read-only tools/list` | `tools/call` 또는 알 수 없는 method를 보냈습니다. | 목록 조회를 실행 권한으로 해석하지 말고, call request parser와 dispatcher 경계를 별도로 연결합니다. |
| `STDIO message exceeds ... bytes` | catalog response가 transport 상한을 넘었습니다. | 상한을 무제한으로 키우지 말고 pagination·최대 tool 수·schema 크기 정책을 설계합니다. |

## 7. 운영 적용 시 추가할 것

실제 MCP server에는 protocol version 지원표, stderr-only structured logging, EOF/broken-pipe 처리, request ID collision 정책, pagination, authentication/tenant filtering, rate/concurrency limit, deadline·cancellation, durable redacted audit sink를 추가해야 합니다.

무엇보다 `tools/list` catalog에서 얻은 name/schema를 신뢰해 `tools/call` handler를 직접 부르면 안 됩니다. transport envelope를 분리해 검증하고, `McpToolCallRequest` parser, `ToolRegistry` allowlist·schema 재검증, 위험도·request-bound 사람 승인, timeout/retry 및 최소 audit dispatcher를 순서대로 다시 통과시켜야 합니다.

## 8. 완료 체크리스트

- [ ] initialize lifecycle이 끝난 뒤에만 request ID가 있는 `tools/list`를 받는지 확인했다.
- [ ] response가 `McpServerCatalog`의 읽기 전용 schema snapshot만 포함하는지 확인했다.
- [ ] notification, non-empty params, `tools/call`과 unknown method가 거부되는지 확인했다.
- [ ] catalog 조회 중 handler·dispatcher·승인·감사가 호출되지 않는지 확인했다.
- [ ] 예제와 테스트를 실제 STDIO·파일·셸·네트워크·파괴 작업 없이 실행했다.
