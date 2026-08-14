# MCP Prompt: 고정 allowlist 템플릿을 보간 없이 제공하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- MCP `prompts/list`와 닮은 Prompt metadata를 명시적 allowlist에서 만든다.
- 정확히 등록된 이름으로만 Prompt를 조회하고 이름을 정규화하거나 유사 이름을 보정하지 않는다.
- 고정 `role`/`content` message snapshot만 반환하고 사용자 입력이나 변수는 보간하지 않는다.
- Prompt 조회를 Resource 읽기와 Tool 실행·승인·전송 계층에서 분리한다.

## 2. Prompt는 Tool이 아니다

Prompt는 모델에 전달할 안내 message의 *정의*입니다. Tool catalog가 실행 가능한 함수의 정의를 보이는 것과 달리, 이 장의 `McpPromptCatalog`는 코드에 넣은 고정 message만 돌려줍니다. `get_prompt()`에는 arguments 매개변수도 없으므로 요청자가 `{{user_input}}` 같은 값을 넣어 message를 바꿀 수 없습니다.

```text
allowlisted McpStaticPrompt
  name + description + fixed McpPromptMessage tuple
                         │
                         ▼
McpPromptCatalog.list_prompts()
  - name, description metadata snapshot
                         │
                         ▼
McpPromptCatalog.get_prompt(exact_name)
  - fixed role/content message snapshot
  - interpolation, Tool execution 없음
```

`McpStaticPrompt`에는 template engine, callback, handler가 없고 `McpPromptCatalog`에는 `execute()`가 없습니다. 따라서 Prompt를 읽는 일은 Tool 권한이나 파일·셸·네트워크 접근 권한을 만들지 않습니다.

## 3. 제한된 정적 Prompt 계약

이 교육용 모델은 다음을 모두 요구합니다.

- Prompt name과 description은 공백만으로 이루어질 수 없습니다.
- Prompt는 1개 이상 8개 이하의 `McpPromptMessage`를 가집니다.
- message role은 `system`, `user`, `assistant` 중 하나입니다.
- message content는 비어 있지 않고 최대 4,096자입니다.
- Prompt name은 catalog 안에서 유일합니다.
- `get_prompt()`는 allowlist에 있는 exact name 하나만 받고 arguments·변수·사용자 입력을 받지 않습니다.

이는 전체 MCP Prompt protocol 구현이 아닙니다. Prompt argument schema, template interpolation, completion, JSON-RPC framing, STDIO·HTTP transport, 인증·인가·rate limit는 이 단계의 범위 밖입니다. 특히 검토되지 않은 사용자 입력을 Prompt 문자열로 합성하는 기능을 이 catalog에 추가하지 마세요.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_static_prompts.py
uv run pytest tests/volume03/test_mcp_prompts.py -q
```

예제 출력은 다음과 같습니다.

```text
tool-safety-reminder: system: Use only reviewed, allowlisted Tools and request approval when required.
```

예제는 내장 system message 한 개만 list/get 합니다. 사용자 입력, template interpolation, Tool handler, 파일·환경 변수·셸·네트워크·외부 MCP server에는 접근하지 않습니다.

## 5. 코드 읽기 순서

1. `McpPromptMessage`가 허용 role과 짧은 고정 content를 제한합니다.
2. `McpStaticPrompt`가 비어 있지 않은 작은 message tuple만 받습니다.
3. `McpPromptCatalog`가 중복 name을 거부하고 Prompt 정의를 복사해 보관합니다.
4. `list_prompts()`가 metadata의 새 snapshot을 제공합니다.
5. `get_prompt()`가 정확한 allowlist key로만 고정 messages를 반환하며 interpolation 인자를 받지 않는지 확인합니다.
6. 테스트가 공백 suffix alias와 두 번째 arguments 인자를 모두 거부하는지 확인합니다.

## 6. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `MCP prompt is not allowlisted` | 이름이 등록되지 않았거나 공백 등이 추가되었습니다. | 이름을 보정하지 말고 검토된 Prompt를 명시적으로 배포합니다. |
| `takes 2 positional arguments but 3 were given` | `get_prompt()`에 interpolation arguments를 전달했습니다. | 고정 Prompt를 먼저 유지하고, 동적 입력은 별도 schema·권한 경계에서 설계합니다. |
| `role must be system, user, or assistant` | 정적 모델이 지원하지 않는 message role입니다. | 제한된 role 집합을 유지하거나 protocol adapter를 별도로 검토합니다. |
| `at most 4096 characters` | 고정 message가 교육용 크기 경계를 넘었습니다. | 최소 안내문만 넣고 큰 문서는 권한 있는 Resource 경계에서 다룹니다. |

## 7. 운영 적용 시 추가할 것

실제 MCP server에서는 고정 SDK·protocol version으로 JSON-RPC Prompt 요청·결과 framing을 검증하세요. 동적 Prompt가 필요하면 arguments JSON Schema, 허용 변수 목록, context provenance, tenant authorization, injection-resistant rendering, output size 제한, rate limit, cancellation·timeout, 민감정보 redaction과 감사 로그를 별도 adapter에 넣어야 합니다.

Prompt를 가져왔다는 사실은 Tool 실행 승인이 아닙니다. 실제 `tools/call` dispatcher는 앞 장의 parser와 `ToolRegistry.validate_request()`를 다시 통과하고, 위험도 정책·사람 승인·timeout/retry·감사 경계를 요청 전체에 묶어야 합니다. 이 장은 destructive Tool, 사용자 입력 보간, 파일 읽기, 셸 실행, 네트워크 요청을 등록하거나 호출하지 않습니다.

## 8. 완료 체크리스트

- [ ] 정적 allowlist의 name으로만 Prompt를 조회함을 확인했다.
- [ ] 고정 role/content message만 반환하고 interpolation 인자가 없음을 확인했다.
- [ ] 중복 name, 비허용 role, 과대 content, 빈 message 목록을 등록 단계에서 거부함을 확인했다.
- [ ] 공백 suffix alias와 interpolation arguments가 Prompt 계약을 우회하지 못함을 확인했다.
- [ ] 예제와 테스트를 실제 부작용 없이 실행했다.
