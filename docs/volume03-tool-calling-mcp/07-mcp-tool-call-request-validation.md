# MCP Tool call request: 실행 전에 신뢰되지 않은 JSON 다시 검증하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- MCP client가 보낸 호출 JSON을 실행 기능 없이 좁게 파싱한다.
- 요청의 `name`과 객체형 `arguments`를 기존 `ToolRegistry.validate_request()`로 다시 검증한다.
- 중복 JSON 키, `NaN`/`Infinity`, 알 수 없는 최상위 키를 모호성으로 보고 거부한다.
- 파싱·검증과 handler 실행, 전송 계층, 승인·감사를 분리한다.

## 2. catalog를 신뢰하면 안 되는 이유

앞 장의 `McpServerCatalog`는 client에 Tool 이름과 입력 Schema를 보여 주지만, 그 client가 보낸 `tools/call` 성격의 payload는 신뢰할 수 없습니다. 이전에 보낸 catalog snapshot이나 모델이 선택한 Tool 이름은 실행 권한이 아닙니다.

```text
신뢰되지 않은 JSON 문자열
          │
          ▼
parse_mcp_tool_call_request()
  - JSON object인지 확인
  - name / arguments 두 키만 허용
  - 중복 키, NaN, Infinity 거부
          │
          ▼
McpToolCallRequest.validate_against(registry)
          │
          ▼
기존 ToolRegistry.validate_request()
  - allowlist
  - required / additionalProperties
  - 타입 / enum
          │
          └── 여기까지 handler 실행 없음
```

`McpToolCallRequest`에는 handler, 결과, `execute()`가 없습니다. `validate_against()`는 `ToolRegistry.validate_request()`만 호출합니다. 그러므로 다음 단계에서 실제 dispatcher를 만들더라도 이 검증을 생략하거나 catalog 결과만으로 Tool을 동적 등록하면 안 됩니다.

## 3. 제한된 JSON 계약

이 교육용 경계가 받는 JSON 문자열은 정확히 다음 모양입니다.

```json
{
  "name": "safe_text_case",
  "arguments": {
    "text": "Mcp",
    "operation": "upper"
  }
}
```

- 최상위 키는 `name`, `arguments` 두 개여야 합니다. `id`, `meta`, provider별 옵션은 아직 받지 않습니다.
- `name`은 비어 있지 않은 문자열이고, `arguments`는 JSON 객체여야 합니다.
- 같은 object 안에 같은 키를 두 번 쓰면 JSON parser가 마지막 값을 조용히 덮어쓰지 않도록 거부합니다.
- JSON 표준 밖의 `NaN`, `Infinity`, `-Infinity`도 거부합니다.
- 이 파서는 Schema 전체를 구현하지 않습니다. 파싱 후 **항상** registry가 allowlist와 기존 입력 Schema를 재검증합니다.

이 엄격함은 실제 MCP protocol 전체를 구현한다는 뜻이 아닙니다. JSON-RPC request id, protocol version, content result, cancellation, transport framing은 아직 모델에 넣지 않았습니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_tool_call_request.py
uv run pytest tests/volume03/test_mcp_call_requests.py -q
```

예제 출력은 다음과 같습니다.

```text
validated without execution: safe_text_case
```

예제는 `safe_text_case`의 허용된 인자만 검증하고 handler를 호출하지 않습니다. 파일·셸·환경 변수·네트워크·외부 MCP Server에 접근하지 않으며, 실제 문자열 변환 결과도 만들지 않습니다.

## 5. 코드 읽기 순서

1. `parse_mcp_tool_call_request()`는 JSON object와 정확한 최상위 키를 확인합니다.
2. `_json_object_without_duplicate_keys()`와 `_reject_non_standard_json_constant()`는 파싱 중 모호한 입력을 멈춥니다.
3. `McpToolCallRequest`는 arguments를 복사해 이후 caller의 dict 변경과 분리합니다.
4. `validate_against()`는 자체 allowlist를 만들지 않고 `registry.validate_request()`를 재사용합니다.
5. 테스트는 유효 요청도 handler를 실행하지 않는지, 거부된 Tool·enum이 registry에서 거절되는지 확인합니다.

## 6. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `MCP tool call request has unexpected key: id` | 이 단계는 provider metadata를 받지 않는 좁은 계약입니다. | id 등을 무시하거나 실행 인자에 섞지 말고, 이후 JSON-RPC adapter에서 별도 검증합니다. |
| `MCP tool call JSON contains duplicate key` | 같은 JSON object에서 키를 반복했습니다. | producer를 고치고 중복 키를 정상화하지 않습니다. |
| `tool is not allowlisted` | catalog에 보였더라도 현재 registry allowlist에 없습니다. | 요청으로 Tool을 등록하지 말고 검토된 `ToolSpec`과 정책을 배포합니다. |
| `argument ... must be one of` | parser는 통과했지만 registry Schema가 거부했습니다. | 모델/client 입력을 수정하고 registry 검증을 우회하지 않습니다. |

## 7. 운영 적용 시 추가할 것

실제 MCP Server는 고정한 SDK·protocol version 위에서 JSON-RPC framing과 request id를 처리해야 합니다. STDIO 또는 네트워크 transport마다 client 인증·인가, tenant와 리소스 범위, 메시지 크기·속도 제한, 연결 수명, 취소·timeout을 별도로 적용하세요.

검증만으로 실행을 허용하지 마세요. 실제 dispatcher에는 앞 장들의 위험도 정책·사람 승인·timeout/retry·구조화 감사 로그를 요청 전체에 묶고, Tool 결과의 데이터 노출 범위도 제한해야 합니다. 이 장은 파일 삭제, 셸 실행, 네트워크 요청 Tool을 등록하거나 호출하지 않습니다.

## 8. 완료 체크리스트

- [ ] JSON 문자열의 `name`과 객체형 `arguments`만 받음을 확인했다.
- [ ] 중복 키와 비표준 숫자 상수를 거부함을 확인했다.
- [ ] parser 통과 뒤에도 `ToolRegistry.validate_request()`가 다시 실행됨을 확인했다.
- [ ] 검증 단계가 handler 또는 `execute()`를 제공하지 않음을 확인했다.
- [ ] 예제와 테스트를 실제 부작용 없이 실행했다.
