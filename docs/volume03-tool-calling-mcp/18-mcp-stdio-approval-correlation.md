# MCP STDIO 승인 상관관계: JSON-RPC ID의 타입까지 요청에 묶기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- STDIO `tools/call`의 고위험 요청을 host가 미리 발급한 `ApprovalGrant`에만 연결한다.
- JSON-RPC string ID `"7"`과 integer ID `7`을 서로 다른 승인·감사 상관관계로 다룬다.
- transport에서 만든 request ID를 caller `params`가 아니라 신뢰된 boundary가 승인 검증에 전달하게 한다.
- 제어 문자가 든 ID를 거부해 감사·승인 기록의 줄 경계를 흐리지 않는다.

## 2. typed correlation ID

`McpToolCallBoundary`는 `tools/call`의 JSON-RPC envelope ID를 dispatcher의 `request_id`로 전달합니다. 이 값은 `ApprovalGrant`가 바인딩하는 요청 전체의 일부이므로, trusted host는 `mcp_stdio_request_correlation_id()`로 **같은 변환**을 사용해 승인 기록을 준비해야 합니다.

```text
trusted approval workflow
  └─ JSON-RPC ID "approved-call-001"
       └─ mcp_stdio_request_correlation_id(...)
            └─ mcp-stdio:string:approved-call-001
                 └─ ApprovalGrant(request ID + Tool + canonical arguments)

READY tools/call envelope
  └─ same typed JSON-RPC ID
       └─ same correlation ID
            └─ allowlist + Schema + HIGH approval match
                 └─ bounded pure Tool execution + minimal audit
```

문자열 `"7"`은 `mcp-stdio:string:7`, 숫자 `7`은 `mcp-stdio:integer:7`이 됩니다. 보이는 문자가 같아도 JSON-RPC ID의 타입이 다르므로 승인 재사용이 일어나지 않습니다. 빈 문자열, boolean, float와 ASCII 제어 문자를 포함한 string ID는 거부합니다.

`mcp_stdio_request_correlation_id()`는 인증·승인 발급기가 아닙니다. 이것은 신뢰된 host의 승인 workflow와 in-memory 교육용 adapter가 같은 request binding 문자열을 쓰게 하는 순수 변환일 뿐입니다. caller가 `params`에 approval ID, policy, handler, timeout 값을 넣어 실행 권한을 만들 수는 없습니다.

## 3. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
conda env update --file environment.yml --prune
python examples/volume03/mcp_stdio_approved_tools_call.py
pytest tests/volume03/test_mcp_stdio.py -q
```

출력은 다음과 같습니다.

```text
approved_safe_text_case: MCP
```

예제는 메모리에서만 handshake를 수행합니다. host 코드가 고정 request ID, Tool 이름, 인자로 교육용 `ApprovalGrant`를 미리 만들고, 교육 목적으로 `HIGH`로 표시한 `SAFE_TEXT_CASE` 하나를 실행합니다. Tool은 문자열을 대문자로 바꾸는 순수 함수입니다. 실제 `sys.stdin`/`sys.stdout`, 파일, 셸, subprocess, 네트워크, 외부 MCP server, destructive action을 사용하지 않습니다.

## 4. 검증하는 거부 경계

| 상태 | 결과 |
|---|---|
| `HIGH` Tool에 matching approval 없음 | handler 전 거부, 고정 `isError: true` Tool result |
| approval은 integer ID `7`, request는 string ID `"7"` | request ID 불일치로 거부; Tool은 실행하지 않음 |
| Tool 이름 또는 canonical JSON arguments 변경 | 승인 불일치로 거부; 기존 allowlist·Schema 검증도 계속 적용 |
| ID에 LF 등 제어 문자 | JSON-RPC parsing 단계에서 거부; audit/approval correlation을 만들지 않음 |
| matching approval + allowlisted pure Tool | bounded dispatcher를 거쳐 성공 result와 최소 audit event 생성 |

MCP parser가 만든 arguments는 변경 불가 snapshot일 수 있습니다. 승인 canonicalization은 이 snapshot을 일반 JSON object로 복사해 비교합니다. 따라서 immutability를 해제하거나 transport mapping의 구현 타입에 따라 승인 비교가 실패하지 않습니다.

## 5. 운영 적용 시 추가할 것

이 예제의 `ApprovalGrant.for_request()`는 교육용 객체이며, 실제 사람 승인이나 신원을 증명하지 않습니다. 운영에서는 인증된 승인 서비스가 actor, tenant, 정책 버전, 사유, 대상 resource, 비용 한도, 만료, 취소와 단회 사용 상태를 durable store에 기록하고, 실행 service가 검증 가능한 immutable approval reference를 확인해야 합니다.

동일 request ID의 replay·collision을 막는 store, tenant-scoped ID namespace, append-only audit, structured-log escaping, cancellation, idempotency와 결과 redaction도 별도 설계해야 합니다. Python thread timeout은 worker를 강제 종료하지 않으므로 이 교육용 boundary에 실제 부작용 Tool을 연결하지 마세요.

## 6. 완료 체크리스트

- [ ] host가 `mcp_stdio_request_correlation_id()`로 approval request ID를 만든다는 점을 확인했다.
- [ ] string ID와 integer ID가 승인 재사용을 막는 별도 correlation 값이 되는지 확인했다.
- [ ] approval이 Tool 이름·인자·기존 allowlist/Schema 검증을 대체하지 않는지 확인했다.
- [ ] 제어 문자가 든 ID가 audit/approval 기록 전에 거부되는지 확인했다.
- [ ] 예제와 테스트를 실제 destructive action 없이 실행했다.
