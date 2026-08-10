# MCP Resource: 짧은 내장 텍스트만 읽기 전용으로 노출하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- MCP `resources/list`와 닮은 Resource metadata를 고정 allowlist에서 만든다.
- Resource URI를 로컬 파일 경로·URL·glob으로 해석하지 않고 정확한 allowlist key로만 조회한다.
- 짧은 내장 `text/plain` 텍스트를 snapshot으로 돌려준다.
- Resource 읽기와 Tool 실행·호출 요청 검증·전송 계층을 분리한다.

## 2. Resource는 Tool이 아니다

Tool catalog는 모델이 호출할 수 있는 함수의 *정의*를 보여 주고, 여전히 실행 시 allowlist·Schema·정책·승인이 필요합니다. Resource는 그보다 더 좁습니다. 이 장의 `McpResourceCatalog`는 미리 코드에 넣은 짧은 참조 텍스트를 반환할 뿐입니다.

```text
allowlisted McpStaticResource
  URI + name + text/plain + 짧은 내장 text
                  │
                  ▼
McpResourceCatalog.list_resources()
  - uri, name, mimeType metadata snapshot
                  │
                  ▼
McpResourceCatalog.read_resource(exact_uri)
  - 고정 text snapshot
  - URI를 파일·URL·경로로 해석하지 않음
```

`McpStaticResource`에는 path, loader, handler가 없고 `McpResourceCatalog`에는 `execute()`가 없습니다. 따라서 `file:///...`, 상대 경로, 비슷한 URI는 Resource로 열리지 않습니다. `read_resource()`는 정확히 등록된 URI만 dictionary key로 찾습니다.

## 3. 제한된 정적 Resource 계약

이 교육용 모델의 Resource는 다음 조건을 모두 만족해야 합니다.

- URI는 authority와 path가 있는 `ai-platform://...` URI이며 query·fragment가 없습니다.
- name은 비어 있지 않습니다.
- MIME type은 `text/plain`만 허용합니다.
- text는 비어 있지 않고 최대 4,096자이며 코드에 직접 들어 있습니다.
- URI는 catalog 안에서 유일합니다.

이 제한은 실제 MCP Resource protocol 전체가 아닙니다. binary content, resource template, subscribe/update notification, 실제 filesystem/database/http loader, JSON-RPC framing, STDIO·HTTP transport는 아직 구현하지 않습니다. 특히 URI를 받아 파일을 읽는 기능을 이 catalog에 추가하지 마세요.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_static_resources.py
uv run pytest tests/volume03/test_mcp_resources.py -q
```

예제 출력은 다음과 같습니다.

```text
ai-platform://volume03/tool-boundary: Resources describe fixed reference text; they do not grant Tool execution.
```

예제는 한 개의 내장 문자열만 list/read 합니다. 파일·디렉터리·환경 변수·셸·네트워크·외부 MCP server에 접근하지 않고 Tool handler도 호출하지 않습니다.

## 5. 코드 읽기 순서

1. `McpStaticResource`가 URI, MIME type, text 길이를 고정합니다.
2. `McpResourceCatalog`가 중복 URI를 거부하고 Resource 정의만 보관합니다.
3. `list_resources()`가 metadata의 새 snapshot을 제공합니다.
4. `read_resource()`는 URI의 정규화나 path resolution 없이 mapping의 정확한 key를 찾습니다.
5. 테스트가 `file:///etc/passwd`와 slash가 하나 더 있는 alias를 모두 거부하는지 확인합니다.

## 6. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `MCP resource is not allowlisted` | URI가 명시적으로 등록되지 않았거나 비슷한 URI입니다. | URI를 파일 경로로 보정하지 말고 검토된 정적 Resource를 배포합니다. |
| `must be an ai-platform URI` | `file://`, `http://` 또는 불완전 URI를 등록하려 했습니다. | 이 단계에는 외부 loader를 넣지 말고 내장 텍스트만 사용합니다. |
| `MIME type must be text/plain` | binary/구조화 content를 제공하려 했습니다. | 별도 schema와 content-size 정책이 있는 후속 Resource adapter를 설계합니다. |
| `at most 4096 characters` | 참조 텍스트가 이 교육용 정적 경계를 넘었습니다. | 필요한 최소 안내문만 넣고 큰 문서는 별도, 인증된 저장소 경계에서 다룹니다. |

## 7. 운영 적용 시 추가할 것

실제 MCP server에서는 고정 SDK·protocol version으로 JSON-RPC의 Resource 요청·결과 framing을 검증하세요. 동적 Resource가 필요하면 tenant authorization, URI canonicalization, root allowlist, symlink/TOCTOU 방어, content type·크기 제한, rate limit, cancellation·timeout, 민감정보 redaction과 읽기 감사 로그를 별도 adapter에 넣어야 합니다.

Resource를 읽었다는 사실은 Tool 실행 승인이 아닙니다. 실제 `tools/call` dispatcher는 앞 장의 parser 및 `ToolRegistry.validate_request()`를 다시 통과하고, 위험도 정책·사람 승인·timeout/retry·감사 경계를 요청 전체에 묶어야 합니다. 이 장은 destructive Tool, 파일 읽기, 셸 실행, 네트워크 요청을 등록하거나 호출하지 않습니다.

## 8. 완료 체크리스트

- [ ] URI를 경로나 URL로 해석하지 않고 exact allowlist key로만 조회함을 확인했다.
- [ ] 짧은 내장 `text/plain` Resource만 반환함을 확인했다.
- [ ] 중복 URI, 외부 URI, 큰 content를 등록 단계에서 거부함을 확인했다.
- [ ] `file:///...`와 비슷한 URI alias가 allowlist를 우회하지 못함을 확인했다.
- [ ] 예제와 테스트를 실제 부작용 없이 실행했다.
