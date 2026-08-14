# MCP STDIO `prompts/list`: handshake 뒤 고정 Prompt metadata만 읽기 전용으로 노출하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 완료된 `initialize` lifecycle 뒤에만 JSON-RPC `prompts/list` request를 받는다.
- `McpPromptCatalog`의 allowlisted metadata snapshot만 response로 투영한다.
- request ID, 빈 params, 알려진 method를 다시 검증한다.
- Prompt 목록 조회를 `prompts/get`, message 보간, Tool 실행과 분리한다.

## 2. 의도적으로 좁은 transport profile

`mcp/stdio.py`의 `McpStdioSession`은 기존 LF 한 줄 framing, UTF-8 byte 상한, strict JSON, JSON-RPC 2.0 및 고정 `2025-03-26` initialize lifecycle을 그대로 사용합니다. `READY` state에서는 request ID가 있는 `tools/list`, `resources/list`, `prompts/list`만 허용합니다.

```text
initialize → initialized notification → READY
                                      │
                                      ├─ prompts/list + request ID + empty/no params
                                      │     └─ McpPromptCatalog.list_prompts() snapshot response
                                      │
                                      └─ prompts/get, resources/read, tools/call, unknown method,
                                         notification, non-empty params
                                            └─ reject; renderer/loader/dispatcher/handler 없음
```

`McpPromptCatalog`는 명시적으로 등록된 `McpStaticPrompt`의 `name`, `description`만 복사하는 읽기 전용 projection입니다. 고정 `messages`는 response에 포함하지 않고, arguments를 받거나 template을 보간하지 않습니다. 그러므로 목록을 반환해도 Prompt message 반환, 사용자 입력 처리, 파일, 환경 변수, 네트워크, Tool handler는 열리지 않습니다.

이 profile은 `prompts/get`, Prompt argument schema, template rendering, pagination cursor, 실제 `sys.stdin`/`sys.stdout`, subprocess, HTTP, SDK 및 외부 MCP server를 구현하지 않습니다. `params`가 없거나 빈 object일 때만 metadata를 반환하며, cursor 같은 확장 metadata를 추측해 해석하지 않습니다.

## 3. response 계약

성공 response는 compact UTF-8 JSON 한 줄과 LF로 인코딩됩니다.

```json
{
  "jsonrpc": "2.0",
  "id": "prompts-001",
  "result": {
    "prompts": [
      {
        "name": "review-tool-boundary",
        "description": "Reviews the fixed Tool Calling safety boundary."
      }
    ]
  }
}
```

`id`는 caller가 보낸 string 또는 integer를 변경하지 않고 되돌립니다. ID 없는 `prompts/list` notification, 비어 있지 않은 params, `prompts/get`과 알 수 없는 method는 오류입니다. response 생성도 기존 byte 상한으로 다시 확인하므로 큰 Prompt catalog를 무제한 stdout에 쓰지 않습니다.

목록에는 Prompt message나 argument가 없으므로 조회가 content 반환 또는 보간 권한이 되지 않습니다. 향후 `prompts/get`을 추가한다면 name allowlist, arguments 객체, Prompt별 argument schema, output-size 정책 및 redacted audit를 별도 request adapter에서 설계·검증해야 합니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
conda env update --file environment.yml --prune
python examples/volume03/mcp_stdio_prompts_list.py
pytest tests/volume03/test_mcp_stdio.py -q
```

출력은 다음과 같습니다.

```text
review-tool-boundary: listed
```

예제는 코드 안에 명시한 정적 `McpStaticPrompt` 하나로 in-memory JSON-RPC handshake와 `prompts/list`만 확인합니다. 실제 표준 입출력, 파일, 환경 변수, 셸, subprocess, 네트워크, 외부 MCP server를 사용하지 않습니다. 특히 `prompts/get`이나 `tools/call`을 보내지 않으므로 message 반환·보간, Tool 실행·승인·timeout/retry·감사 기록도 발생하지 않습니다.

## 5. 코드 읽기 순서

1. `McpStdioSession.__init__()`이 `McpPromptCatalog` 또는 빈 고정 catalog를 받는지 확인합니다.
2. `receive_line()`이 READY 이전 lifecycle을 먼저 검사하는지 봅니다.
3. `_receive_ready_request()`가 method, request ID, empty params를 검사하는지 확인합니다.
4. `prompts/list`가 `McpPromptCatalog.list_prompts()`의 새 metadata snapshot만 response에 넣는지 확인합니다.
5. `prompts/get`이 renderer 또는 message 조회에 도달하기 전에 거부되는지 확인합니다.
6. 테스트에서 고정 metadata projection, notification 거부, non-empty params 거부, Prompt get 미실행을 확인합니다.

## 6. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `prompts/list must include a JSON-RPC request id` | response를 받을 수 없는 notification을 보냈습니다. | 고유한 string/integer request ID를 붙여 request로 보냅니다. |
| `prompts/list params must be empty when present` | 이 profile이 지원하지 않는 cursor/metadata를 보냈습니다. | metadata를 무시하지 말고, 필요한 pagination 계약을 별도 adapter로 명시·테스트합니다. |
| `no MCP methods are enabled besides ...` | `prompts/get`, `resources/read`, `tools/call` 또는 알 수 없는 method를 보냈습니다. | 목록 조회를 content 반환이나 실행 권한으로 해석하지 말고 별도 검증 경계를 추가합니다. |
| `STDIO message exceeds ... bytes` | Prompt metadata response가 transport 상한을 넘었습니다. | 상한을 무제한으로 키우지 말고 pagination·최대 Prompt 수·metadata 길이 정책을 설계합니다. |

## 7. 운영 적용 시 추가할 것

실제 MCP server에는 protocol version 지원표, stderr-only structured logging, EOF/broken-pipe 처리, request ID collision 정책, pagination, authentication/tenant filtering, rate/concurrency limit, deadline·cancellation, durable redacted audit sink를 추가해야 합니다.

동적 Prompt가 필요해도 `prompts/list`의 name을 신뢰해 template이나 파일을 직접 열면 안 됩니다. `prompts/get` transport envelope를 분리해 검증하고, exact allowlist, arguments object/schema, tenant authorization, output type·크기 제한, timeout 및 redacted rendering audit를 통과시켜야 합니다. Prompt 목록은 Tool 실행 승인이 아니므로 `tools/call`도 기존 parser, `ToolRegistry` allowlist·Schema, 위험도·request-bound 사람 승인, timeout/retry, 최소 audit dispatcher를 다시 통과해야 합니다.

## 8. 완료 체크리스트

- [ ] initialize lifecycle이 끝난 뒤에만 request ID가 있는 `prompts/list`를 받는지 확인했다.
- [ ] response가 `McpPromptCatalog`의 읽기 전용 metadata snapshot만 포함하는지 확인했다.
- [ ] notification, non-empty params, `prompts/get`, `resources/read`, `tools/call`과 unknown method가 거부되는지 확인했다.
- [ ] Prompt 목록 조회 중 message 보간·renderer·dispatcher·승인·감사가 호출되지 않는지 확인했다.
- [ ] 예제와 테스트를 실제 STDIO·파일·셸·네트워크·파괴 작업 없이 실행했다.
