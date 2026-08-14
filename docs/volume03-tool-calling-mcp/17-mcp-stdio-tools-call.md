# MCP STDIO `tools/call`: 명시적 실행 경계로 순수 Tool만 연결하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- `READY` state의 JSON-RPC `tools/call`을 기본적으로 비활성화하고, 검토된 실행 경계가 있을 때만 연다.
- transport `params`를 기존 MCP Tool request parser로 다시 전달해 `name`·객체형 `arguments`·allowlist·Schema를 재검증한다.
- 위험도 정책, request-bound 승인, timeout/retry, 최소 감사를 기존 dispatcher에서 계속 적용한다.
- 순수 Tool의 작고 JSON인 결과만 MCP text content로 투영하고, 거부·실패 세부정보와 원문 인자를 내보내지 않는다.

## 2. 명시적 실행 연결

`McpStdioSession()`만 생성하면 `tools/call`은 계속 거부됩니다. 실행은 host가 구성한 `McpToolCallBoundary`를 명시적으로 전달한 session에서만 가능합니다. boundary에는 `ToolRegistry`, `ToolAuthorizationPolicy`, `ToolExecutionPolicy`, `InMemoryToolAuditSink`, 그리고 필요할 때 신뢰된 `ApprovalGrant`만 들어갑니다.

```text
READY tools/call + JSON-RPC request ID
  └─ explicit McpToolCallBoundary?
       ├─ no  → reject; dispatcher/handler 없음
       └─ yes → compact JSON {name, arguments}
                 └─ parse_mcp_tool_call_request()
                      └─ registry allowlist + Schema
                           └─ authorization + approval
                                └─ bounded timeout/retry
                                     └─ minimal audit
                                          └─ small JSON output → MCP text content
```

caller가 policy, approval, handler, timeout, audit sink를 JSON `params`에 넣을 수 없습니다. 기존 parser는 `name`과 `arguments` 외 key를 거부합니다. `tools/call` request ID는 audit의 `mcp-stdio:string:<id>` 또는 `mcp-stdio:integer:<id>` correlation ID로 변환하므로 JSON-RPC string ID `"1"`과 integer ID `1`이 audit에서 충돌하지 않습니다.

## 3. 성공 response와 오류 정책

성공한 순수 Tool의 output은 최대 4,096 UTF-8 byte의 JSON object text 하나로만 반환합니다.

```json
{
  "jsonrpc": "2.0",
  "id": "call-001",
  "result": {
    "content": [
      {"type": "text", "text": "{\"text\":\"MCP\"}"}
    ],
    "isError": false
  }
}
```

이미 유효한 JSON-RPC `tools/call` envelope에서 parser, allowlist, Schema, approval, timeout/retry, handler 또는 result projection이 실패하면 session은 request ID를 보존한 정상 JSON-RPC `result`를 반환합니다. 다만 내용은 항상 아래의 고정 application-level Tool error입니다.

```json
{
  "content": [
    {"type": "text", "text": "Tool request was denied or failed."}
  ],
  "isError": true
}
```

따라서 handler 예외, policy detail, 승인 정보, Tool 인자와 결과 serialization 실패가 transport response에 섞이지 않습니다. malformed JSON-RPC framing, lifecycle 위반, notification, ID 누락, boundary 자체의 미구성은 request로 안전하게 실행할 수 없으므로 기존처럼 `McpStdioError`로 거부하며 response를 만들지 않습니다. parser 전에 거부된 요청은 신뢰할 Tool request가 아니므로 audit에 기록되지 않습니다. parser 뒤 dispatcher에 들어간 요청의 성공·거부·실패는 최소 audit 정책을 따릅니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
conda env update --file environment.yml --prune
python examples/volume03/mcp_stdio_tools_call.py
pytest tests/volume03/test_mcp_stdio.py -q
```

출력은 다음과 같습니다.

```text
safe_text_case: MCP
```

예제는 메모리 안에서 handshake와 코드에 고정된 `SAFE_TEXT_CASE` 한 번만 실행합니다. 이 Tool은 문자열을 대문자로 바꾸는 순수 함수입니다. filesystem, 실제 `sys.stdin`/`sys.stdout`, shell, subprocess, network, 외부 MCP server, destructive action을 사용하지 않습니다.

## 5. 거부하거나 숨기는 입력

| 입력 또는 상태 | 처리 |
|---|---|
| boundary 없이 `tools/call` | `McpStdioError`; dispatcher와 handler를 호출하지 않습니다. |
| ID 없는 `tools/call` notification | `McpStdioError`; response correlation과 실행을 허용하지 않습니다. |
| `name`/`arguments` 외 params, 중복 key, 비객체 arguments | 고정 `isError: true` Tool result; handler와 audit에 도달하지 않습니다. |
| 미등록 Tool 또는 Schema 불일치 | 고정 `isError: true` Tool result; handler를 호출하지 않습니다. |
| 승인 거부, timeout/retry 소진, handler failure | 고정 `isError: true` Tool result; dispatcher의 최소 audit만 남깁니다. |
| 4 KiB 초과 또는 JSON이 아닌 Tool output | 고정 `isError: true` Tool result; output 원문을 전송하지 않습니다. |

Tool 결과 text를 다시 자동 실행하거나, `content`에 승인·정책을 주입하지 마세요. `tools/list`, Resource, Prompt를 읽은 사실도 Tool 실행 권한이 아닙니다.

## 6. 운영 적용 시 추가할 것

이 예제는 실제 STDIO process loop, EOF/error policy, cancellation, concurrency control, rate limit, tenant authentication, durable audit sink, approval issuance, request-ID replay/collision store를 구현하지 않습니다. Python thread timeout은 worker를 강제 종료하지 않으므로 실제 부작용 Tool에 사용하면 안 됩니다.

운영용 transport는 process lifecycle과 JSON-RPC error response 정책을 별도 설계하고, trusted host configuration에서만 Tool boundary를 조립하세요. 실제 외부 Tool은 취소 가능 adapter, idempotency, compensation, least privilege credential, result redaction, output size/content-type 검증을 갖춰야 합니다. 이 static 학습 boundary에 filesystem, shell, network, dynamic Tool discovery를 추가하지 마세요.

## 7. 완료 체크리스트

- [ ] `tools/call`이 explicit boundary 없이 비활성화되는지 확인했다.
- [ ] transport params가 기존 parser와 allowlist·Schema 검증을 다시 통과하는지 확인했다.
- [ ] policy·approval·timeout/retry·감사가 caller JSON이 아니라 trusted boundary에서만 공급되는지 확인했다.
- [ ] 성공 output이 제한된 JSON text이고, 실패 detail·인자가 고정 error result에 노출되지 않는지 확인했다.
- [ ] 예제와 테스트를 실제 destructive action 없이 실행했다.
