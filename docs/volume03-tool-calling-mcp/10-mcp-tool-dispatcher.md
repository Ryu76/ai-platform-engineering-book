# MCP Tool dispatcher: 검증된 요청을 실행 정책에 묶기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 전송 계층이 없는 작은 dispatcher에서 신뢰되지 않은 MCP Tool JSON을 다시 파싱한다.
- parser와 `ToolRegistry.validate_request()`를 통과한 요청만 위험도·사람 승인·timeout/retry·감사 경계로 보낸다.
- Tool handler를 직접 호출하지 않고 기존 allowlist 실행 경계에 재진입시킨다.
- Resource/Prompt 조회와 Tool 실행 권한을 계속 분리한다.

## 2. dispatcher가 추가하는 순서

이전 장의 `McpToolCallRequest`는 실행 의도와 검증만 모델링했습니다. `dispatch_mcp_tool_call()`은 제한된 실행 정책을 명시적으로 조합하되, JSON-RPC·STDIO·HTTP server나 외부 MCP client는 열지 않습니다.

```text
raw JSON string
  │ parse_mcp_tool_call_request() — exact name + object arguments
  ▼
McpToolCallRequest.validate_against(registry) — allowlist + schema, handler 없음
  ▼
authorize_request() — risk policy + request-bound approval
  ▼
execute_with_policy() — every attempt re-enters ToolRegistry, bounded timeout/retry
  ▼
minimal audit event — request ID, tool, risk, approval ID, outcome only
```

`request_id`는 공백이 아닌 문자열이어야 합니다. dispatcher는 raw request에 임의의 ID·metadata를 허용하지 않습니다. 요청 JSON은 여전히 정확히 `name`과 `arguments`만 포함해야 하므로, transport metadata가 Tool 인자나 권한 입력에 섞일 수 없습니다.

## 3. 실행 계약과 경계

`dispatch_mcp_tool_call()`은 아래 순서를 지킵니다.

1. JSON parser가 중복 키, 비표준 숫자 상수, 예상 밖 키를 거부합니다.
2. `McpToolCallRequest.validate_against()`가 handler를 부르지 않고 정확한 allowlist 이름과 JSON Schema를 확인합니다.
3. `authorize_request()`가 등록된 위험도 정책과 고위험 Tool의 request-bound `ApprovalGrant`를 확인합니다.
4. `execute_with_policy()`가 timeout과 최대 3회 retry를 적용하고 **각 시도**마다 `ToolRegistry.execute()`로 돌아가 allowlist·Schema를 재검증합니다.
5. `execute_audited_with_policy()`가 원문 인자·결과·예외 없이 최종 상태를 한 번 기록합니다.

parser 단계에서 거부된 raw request는 신뢰할 수 있는 Tool 요청이 아니므로 audit sink에 기록하지 않습니다. parse 뒤 실행 경계에 도달한 승인/정책 거부와 실행 결과만 최소 감사 이벤트가 됩니다. 이 교육용 sink는 승인·allowlist·Schema 거부를 `denied`, timeout·retry 소진과 handler 예외를 `failed`로 기록합니다. 운영 환경에서는 세분화된 오류 분류, timestamp, actor/tenant correlation, append-only 원격 sink와 sink 실패 정책을 별도 설계하세요.

`McpStaticResource`와 `McpPromptCatalog`는 이 dispatcher에 전달되지 않으며, Prompt/Resource를 읽었다고 Tool 실행 권한이나 승인이 생기지 않습니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
conda env update --file environment.yml --prune
python examples/volume03/mcp_tool_dispatcher.py
pytest tests/volume03/test_mcp_dispatcher.py -q
```

예제 출력은 다음과 같습니다.

```text
safe_text_case: MCP (succeeded)
```

예제는 코드에 명시적으로 등록한 순수 문자열 대소문자 변환 Tool 하나만 호출합니다. 입력은 고정 JSON 문자열이며 파일·환경 변수·셸·네트워크·STDIO·외부 MCP Server에 접근하지 않습니다. `SAFE_TEXT_CASE`는 allowlist에 없는 Tool로 교체할 수 없고, 실제 파괴 작업을 수행하지 않습니다.

## 5. 코드 읽기 순서

1. `mcp/dispatcher.py`에서 `request_id`를 확인하고 raw JSON을 parser로 넘깁니다.
2. `_validate_request_without_execution()`이 실행 전 registry 검증을 강제하는지 봅니다.
3. `tools/authorization.py`의 `authorize_request()`가 실행과 승인 검사를 분리하는지 확인합니다.
4. `execute_authorized_with_policy()`가 승인 후에도 `execute_with_policy()`만 사용하고 handler를 직접 부르지 않는지 확인합니다.
5. `tools/audit.py`의 `execute_audited_with_policy()`가 최소 이벤트 하나만 남기는지 확인합니다.
6. 테스트에서 retry 성공, 고위험 승인 거부, 불완전 raw request의 handler 미호출을 확인합니다.

## 6. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `unexpected key: id` | raw Tool JSON에 실행 계약 밖 metadata를 넣었습니다. | transport envelope는 별도 adapter에서 검증하고, 이 좁은 dispatcher에는 `name`/`arguments`만 전달합니다. |
| `tool is not allowlisted` | 등록되지 않은 이름이 요청되었습니다. | 이름을 유사 보정하지 말고 검토된 `ToolSpec`을 명시적으로 등록합니다. |
| `human approval is required` | 고위험 Tool에 request-bound 승인 기록이 없습니다. | 승인 workflow에서 동일 request ID·Tool·인자로 새 `ApprovalGrant`를 발급합니다. |
| `tool execution timed out` | 순수 handler가 정책 시간 안에 끝나지 않았습니다. | handler를 취소 가능·멱등적으로 설계하고 외부 실행 adapter의 강한 cancellation을 별도로 구현합니다. |

## 7. 운영 적용 시 추가할 것

실제 MCP server에는 고정 protocol version의 JSON-RPC framing, STDIO/HTTP transport lifecycle, 인증·tenant authorization, request ID collision 방지, per-tool rate/concurrency limits, deadline propagation, cancellation, idempotency key, durable append-only audit sink, redaction, alerting을 추가해야 합니다.

Python thread timeout은 worker를 강제 종료하지 않습니다. 따라서 실제 부작용 Tool에 이 교육용 thread timeout/retry만 적용하면 안 됩니다. 외부 시스템 호출은 취소·보상·멱등성·권한이 있는 별도 adapter에서 다루고, retry 대상은 명시적으로 안전한 `RetryableToolError`로 제한하세요.

## 8. 완료 체크리스트

- [ ] raw JSON이 parser와 기존 allowlist·Schema 검증을 handler 전에 통과하는지 확인했다.
- [ ] 고위험 Tool이 request-bound 승인 없이는 실행되지 않는지 확인했다.
- [ ] timeout/retry가 매 시도 기존 registry 실행 경계로 재진입하는지 확인했다.
- [ ] 감사 이벤트에 원문 인자·결과·예외가 없는지 확인했다.
- [ ] 예제와 테스트를 실제 부작용 없이 실행했다.
