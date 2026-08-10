# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP Resource의 정적·읽기 전용 allowlist (전송·실행 계층 없음)**
- 완료 선언: 아직 하지 않음. Volume 03의 MCP 호출 dispatcher, Prompt, STDIO, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: URI를 파일로 해석하지 않는 짧은 정적 MCP Resource

- `src/ai_platform/mcp/resources.py`
  - `McpStaticResource`는 authority와 path를 가진 `ai-platform://` URI, 빈 값이 아닌 name, `text/plain`, 최대 4,096자의 내장 text만 받습니다. query와 fragment도 거부합니다.
  - `McpResourceCatalog`는 중복 URI를 거부하고, URI를 정규화·경로 해석하지 않은 정확한 allowlist key로만 조회합니다.
  - `list_resources()`는 `uri`·`name`·`mimeType` metadata snapshot을, `read_resource()`는 allowlisted URI의 고정 `text` snapshot만 돌려줍니다. handler·`execute()`·파일/환경/네트워크 loader가 없습니다.
- `src/ai_platform/mcp/__init__.py`
  - 기존 Tool catalog·call-request API와 함께 제한된 static Resource API만 export합니다.
- `examples/volume03/mcp_static_resources.py`
  - 명시적으로 등록한 `ai-platform://volume03/tool-boundary`의 내장 텍스트 한 개만 list/read 하고 출력합니다. 파일, 셸, 네트워크, 외부 MCP Server, Tool handler에 접근하지 않습니다.
- `tests/volume03/test_mcp_resources.py`
  - allowlisted 내장 text의 목록·읽기, `file:///etc/passwd` 및 slash alias 거부, 중복 URI·외부 URI·비허용 MIME·과대 text 거부, 실행 API 부재를 검증합니다.
- `docs/volume03-tool-calling-mcp/08-mcp-static-resources.md`
  - Resource와 Tool 권한을 분리하고, 정적 계약·오프라인 실습·URI path resolution 금지·동적 Resource 운영 경계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 여덟 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_static_resources.py
ai-platform://volume03/tool-boundary: Resources describe fixed reference text; they do not grant Tool execution.

$ uv run pytest tests/volume03/test_mcp_resources.py -q
3 passed in 0.09s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 17 source files

$ uv run pytest -q
107 passed in 0.84s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv`는 Hermes 활성 가상환경과 프로젝트 `.venv`의 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 모든 명령을 정상 실행했습니다. 실제 LLM 호출, MCP 통신, 파일·시스템 변경, 외부 네트워크 요청은 수행하지 않았습니다.

## 다음 슬라이스

MCP Prompt를 정적 allowlist 템플릿으로 모델링합니다. 이름·설명·고정 role/content message만 snapshot으로 노출하고, 사용자 입력 interpolation, Tool 실행, 파일/환경/네트워크, STDIO는 하지 않습니다. Prompt 조회와 Resource 읽기·Tool 실행 권한을 계속 분리합니다.
