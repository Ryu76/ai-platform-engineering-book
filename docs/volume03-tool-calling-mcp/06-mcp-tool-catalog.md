# MCP Tool catalog: 실행 권한 없이 allowlist를 노출하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 기존 Tool allowlist를 MCP의 `tools/list`와 닮은 메타데이터로 투영한다.
- Tool 정의 공개와 Tool 실행 권한을 분리한다.
- catalog snapshot을 호출자가 변경해도 서버 정의가 바뀌지 않게 한다.
- 아직 SDK, STDIO, 네트워크, subprocess가 없는 교육용 모델의 범위를 설명한다.

## 2. catalog는 실행기가 아니다

MCP Server는 클라이언트가 사용할 수 있는 Tool의 이름, 설명, 입력 Schema를 발견할 수 있게 합니다. 하지만 발견 가능하다는 사실은 실행 권한이 아닙니다. 이 첫 모델의 `McpServerCatalog`는 기존 `ToolRegistry`에 이미 등록된 `ToolSpec`만 복사하고, handler를 보관하거나 `execute()`를 만들지 않습니다.

```text
검토된 ToolRegistry allowlist
             │
             ▼
McpServerCatalog.from_registry()
             │
             ▼
MCP tools/list 모양의 name / description / inputSchema snapshot
             │
             └── Tool handler · 파일 · 셸 · 네트워크 · subprocess 없음
```

따라서 catalog에 `safe_calculator`가 보인다고 해서 모델 또는 MCP client가 계산기를 자동 실행할 수는 없습니다. 이후 호출 경로도 반드시 기존 allowlist, JSON Schema 검증, timeout/retry, 위험도·승인, 감사 경계를 통과해야 합니다.

## 3. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_tool_catalog.py
uv run pytest tests/volume03/test_mcp_catalog.py -q
```

예제는 순수 함수인 `safe_calculator`, `safe_text_case` 두 개를 명시적으로 등록한 뒤 이름과 설명만 출력합니다. 실제 Tool을 호출하지 않고, 파일·셸·환경 변수·네트워크·외부 MCP Server에 접근하지 않습니다.

```text
safe_calculator: 두 유한 수의 허용된 사칙연산을 수행합니다. 외부 시스템을 변경하지 않습니다.
safe_text_case: 문자열을 대문자 또는 소문자로만 변환합니다. 외부 시스템을 변경하지 않습니다.
```

`list_tools()`가 반환하는 각 정의는 다음처럼 MCP Tool 목록에 대응합니다.

```python
{
    "name": "safe_calculator",
    "description": "...",
    "inputSchema": {"type": "object", "properties": {"left": {"type": "number"}}},
}
```

반환된 `inputSchema`를 수정해도 다음 `list_tools()` 호출 결과는 달라지지 않습니다. registry 또는 이전 client의 mutable dict가 catalog 계약을 바꾸지 않도록 생성 시점과 반환 시점에 모두 복사하기 때문입니다.

## 4. 코드 읽기 순서

1. `McpToolDefinition`은 `name`, `description`, 객체형 `input_schema`만 보관합니다.
2. `McpServerCatalog.from_registry()`는 `registry.allowed_tools()`의 allowlisted Tool만 정의로 복사합니다.
3. `list_tools()`는 MCP 관례의 `inputSchema` 키를 사용한 새 snapshot을 돌려줍니다.
4. 이 모듈에는 handler, call dispatch, SDK transport가 없음을 확인합니다.

이름과 Schema를 client에 제공해도 client payload는 신뢰할 수 없습니다. 다음 호출 경계에서 다시 Schema 검증해야 하며, catalog 결과만 보고 Tool을 동적으로 등록해서는 안 됩니다.

## 5. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `MCP tool names must be unique` | 동일 이름의 정의가 두 번 catalog에 들어갔습니다. | 이름 충돌을 해소하고 명시적으로 검토된 Tool 하나만 등록합니다. |
| `MCP tool input schema type must be object` | Tool 입력이 JSON 객체 계약이 아닙니다. | 넓은 임의 payload를 허용하지 말고 object Schema로 좁힙니다. |
| catalog에 필요한 Tool이 없음 | registry allowlist에 등록되지 않았습니다. | 요청/로그만으로 자동 등록하지 말고 ToolSpec과 정책을 별도 검토합니다. |
| catalog가 호출도 해 줄 것으로 기대함 | 목록과 실행 경계를 혼동했습니다. | 실행은 검증·승인·감사를 포함한 별도 dispatcher로 연결합니다. |

## 6. 운영 적용 시 추가할 것

이 모델은 MCP 프로토콜 또는 특정 SDK의 구현이 아닙니다. 운영 MCP Server를 만들 때는 SDK와 프로토콜 버전을 고정하고, STDIO 또는 네트워크 transport의 client 인증·인가, tenant/리소스 범위, 요청 크기·속도 제한, 연결 수명, 취소·timeout, structured audit, 입력 재검증을 별도로 설계해야 합니다.

catalog 자체도 공격 표면입니다. Tool 설명에 비밀값·내부 경로·운영 토큰을 넣지 말고, client별로 공개 가능한 Tool 목록을 최소화하며, 버전이 바뀐 Schema와 정책의 호환성을 검토하세요. Tool의 이름·Schema 노출은 실제 파일 삭제, 셸 실행, 네트워크 요청 권한을 제공하지 않습니다.

## 7. 완료 체크리스트

- [ ] `tools/list` 모양의 정의가 allowlisted Tool에서만 만들어짐을 확인했다.
- [ ] catalog가 handler나 `execute()`를 제공하지 않음을 확인했다.
- [ ] 반환 Schema 수정이 다음 catalog snapshot을 바꾸지 않음을 확인했다.
- [ ] 실제 MCP SDK/STDIO/네트워크 transport가 아직 없음을 설명할 수 있다.
- [ ] 예제와 테스트를 실제 부작용 없이 실행했다.
