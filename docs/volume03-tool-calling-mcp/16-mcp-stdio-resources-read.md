# MCP STDIO `resources/read`: 고정 allowlist Resource만 반환하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 완료된 `initialize` lifecycle 뒤 JSON-RPC `resources/read` request를 좁게 검증한다.
- exact allowlist URI 하나만 받고 URI 정규화·경로 해석을 하지 않는다.
- `McpResourceCatalog.read_resource()`의 고정 내장 text snapshot을 MCP `contents` envelope로 반환한다.
- Resource 조회를 filesystem loader, URL fetch, Tool execution과 분리한다.

## 2. 좁은 request 계약

`McpStdioSession`은 `READY` state에서 request ID가 있는 `resources/read`만 받습니다. `params`는 `uri` 하나만 가져야 합니다. `uri`는 공백을 제거하거나 path를 정규화하지 않는 exact allowlist key입니다.

```text
resources/read + request ID
  └─ { uri: exact allowlisted ai-platform URI }
       └─ McpResourceCatalog.read_resource(uri)
            └─ fixed text/plain snapshot
                 └─ { contents: [snapshot] }

unknown URI, file URI, alias, notification, extra params
  └─ reject; filesystem/URL loader/tool dispatcher 없음
```

URI가 string이라는 검사는 URI resolver를 호출한다는 뜻이 아닙니다. 이 adapter는 `McpResourceCatalog` mapping에서 완전히 일치하는 key만 찾습니다. `file:///...`, relative path, trailing slash alias, query 및 network URL을 파일 또는 네트워크 접근으로 바꾸지 않습니다.

## 3. response 계약

성공 response는 compact UTF-8 JSON 한 줄과 LF입니다. `contents`는 이 좁은 static model에서 하나의 고정 Resource snapshot만 가집니다.

```json
{
  "jsonrpc": "2.0",
  "id": "resource-001",
  "result": {
    "contents": [
      {
        "uri": "ai-platform://volume03/transport-boundary",
        "mimeType": "text/plain",
        "text": "Reading this resource does not read a file or execute a Tool."
      }
    ]
  }
}
```

catalog가 보관한 내장 `uri`, `mimeType`, `text`만 새 response envelope에 담습니다. caller가 준 URI의 변형, 환경 변수, 파일 내용, Tool 결과를 합성하지 않습니다. response도 기존 transport byte 상한을 통과해야 합니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_stdio_resources_read.py
uv run pytest tests/volume03/test_mcp_stdio.py -q
```

출력은 다음과 같습니다.

```text
ai-platform://volume03/transport-boundary: fixed snapshot
```

예제는 메모리 안에서 handshake와 static Resource 한 개의 `resources/read`만 확인합니다. 실제 `sys.stdin`/`sys.stdout`, filesystem, URL fetch, 환경 변수, 셸, subprocess, 네트워크, 외부 MCP server 및 destructive Tool은 사용하지 않습니다.

## 5. 거부하는 입력

| 입력 | 거부 이유 |
|---|---|
| ID 없는 notification | response를 연결할 request ID가 없습니다. |
| `uri` 누락·빈 문자열·비문자열 | exact allowlist lookup을 안전하게 할 수 없습니다. |
| `uri` 외 extra key | 허용하지 않은 request 모양을 추측해 해석하지 않습니다. |
| trailing slash 등 비슷한 URI | 정규화·fuzzy matching이 allowlist를 우회하지 못하게 합니다. |
| `file:///etc/passwd` 또는 미등록 URI | URI를 filesystem path나 URL로 열지 않고 allowlist 밖 요청을 거부합니다. |

`tools/call`과 unknown method은 계속 거부됩니다. Resource text를 받는 일은 Tool 실행 승인이나 Resource loader 권한이 아닙니다.

## 6. 운영 적용 시 추가할 것

동적 Resource가 필요하면 static `resources/read`과 별도 loader boundary를 명시하세요. tenant authorization, URI canonicalization 정책, root allowlist, symlink/TOCTOU 방어, content type·크기 제한, rate limit, cancellation·timeout, 민감정보 redaction 및 읽기 audit를 모두 검증해야 합니다. 실제 filesystem/database/http 접근을 이 static catalog 또는 이 adapter에 추가하지 마세요.

Tool 실행은 계속 별도 경계입니다. 실제 `tools/call` dispatcher는 parser 및 `ToolRegistry.validate_request()`를 다시 통과하고, 위험도 정책·사람 승인·timeout/retry·최소 audit를 요청 전체에 묶어야 합니다.

## 7. 완료 체크리스트

- [ ] handshake 뒤 request ID가 있는 `resources/read`만 받는지 확인했다.
- [ ] exact `uri` 하나만 받고 alias·extra param을 거부하는지 확인했다.
- [ ] fixed `text/plain` snapshot을 `contents` response로 반환하며 URI를 해석하지 않는지 확인했다.
- [ ] notification, file URI, unknown URI가 거부되는지 확인했다.
- [ ] 예제와 테스트를 실제 부작용 없이 실행했다.
