# MCP STDIO `prompts/get`: 고정 allowlist Prompt만 보간 없이 반환하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 완료된 `initialize` lifecycle 뒤 JSON-RPC `prompts/get` request를 좁게 검증한다.
- exact allowlist name과 없거나 빈 `arguments`만 받는다.
- `McpPromptCatalog.get_prompt()`의 고정 message snapshot만 response로 반환한다.
- Prompt 조회를 template rendering, 사용자 입력, Resource read, Tool execution과 분리한다.

## 2. 좁은 request 계약

`McpStdioSession`은 `READY` state에서 request ID가 있는 `prompts/get`만 받습니다. `params`는 `name` 하나, 또는 `name`과 빈 object `arguments`만 가질 수 있습니다. `name`은 공백을 제거하거나 alias를 찾지 않는 exact allowlist key입니다.

```text
prompts/get + request ID
  └─ { name: exact allowlisted name, arguments?: {} }
       └─ McpPromptCatalog.get_prompt(name)
            └─ fixed role/content snapshot

arguments with values, unknown keys, unknown name, notification
  └─ reject; interpolation/renderer/resource loader/tool dispatcher 없음
```

`arguments`를 빈 object까지로 제한하는 이유는 이 static Prompt model에 변수 schema나 renderer가 없기 때문입니다. 빈 arguments는 client의 일반 envelope와 호환되는 명시적 no-op일 뿐, future template interpolation 권한이 아닙니다.

## 3. response 계약

성공 response는 compact UTF-8 JSON 한 줄과 LF입니다.

```json
{
  "jsonrpc": "2.0",
  "id": "prompt-001",
  "result": {
    "name": "review-tool-boundary",
    "description": "Reviews the fixed Tool Calling safety boundary.",
    "messages": [
      {
        "role": "system",
        "content": "Review allowlist and approval boundaries without executing Tools."
      }
    ]
  }
}
```

서버는 caller의 ID를 string 또는 integer 그대로 되돌리고, catalog가 복사해 가진 fixed message만 반환합니다. message를 수정하거나 사용자 값·환경 변수·파일 내용을 합성하지 않습니다. response도 기존 transport byte 상한을 통과해야 합니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_stdio_prompts_get.py
uv run pytest tests/volume03/test_mcp_stdio.py -q
```

출력은 다음과 같습니다.

```text
review-tool-boundary: fixed snapshot
```

예제는 메모리 안에서 handshake와 static Prompt 한 개의 `prompts/get`만 확인합니다. 실제 `sys.stdin`/`sys.stdout`, template engine, 사용자 입력, 파일, 셸, subprocess, 네트워크, 외부 MCP server 및 destructive Tool은 사용하지 않습니다.

## 5. 거부하는 입력

| 입력 | 거부 이유 |
|---|---|
| ID 없는 notification | response를 연결할 request ID가 없습니다. |
| `name` 누락·빈 문자열 | exact allowlist lookup을 안전하게 할 수 없습니다. |
| `arguments`가 비어 있지 않음 | renderer와 Prompt argument schema가 이 profile에 없습니다. |
| `arguments`가 object가 아님 또는 extra key | 허용하지 않은 request 모양을 추측해 해석하지 않습니다. |
| 공백 suffix 또는 미등록 name | 이름 정규화·fuzzy matching으로 allowlist를 우회하지 않습니다. |

`tools/call`, `resources/read`, unknown method은 계속 거부됩니다. Prompt message를 받는 일은 Tool 실행 승인도, Resource 접근 권한도 아닙니다.

## 6. 운영 적용 시 추가할 것

동적 Prompt가 필요하면 `prompts/get`과 별도 renderer boundary를 명시하세요. Prompt별 arguments JSON Schema, 허용 변수, provenance, tenant authorization, injection-resistant rendering, output type·byte limit, timeout/cancellation, redacted audit를 모두 검증해야 합니다. Tool은 기존 parser, `ToolRegistry` allowlist·Schema, 승인, timeout/retry와 최소 audit dispatcher를 별도로 통과해야 합니다.

## 7. 완료 체크리스트

- [ ] handshake 뒤 request ID가 있는 `prompts/get`만 받는지 확인했다.
- [ ] exact `name`과 없거나 빈 object `arguments`만 받는지 확인했다.
- [ ] fixed message snapshot을 반환하며 보간·loader·dispatcher를 호출하지 않는지 확인했다.
- [ ] notification, unknown name, alias, non-empty arguments, unknown key가 거부되는지 확인했다.
- [ ] 예제와 테스트를 실제 부작용 없이 실행했다.
