# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP Tool catalog (전송 계층 없음)**
- 완료 선언: 아직 하지 않음. Volume 03의 MCP 호출 경계, Resource/Prompt, STDIO, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: allowlist를 실행 권한 없이 MCP Tool 목록으로 투영

- `src/ai_platform/mcp/catalog.py`
  - `McpToolDefinition`은 MCP Tool 이름·설명·객체형 입력 Schema만 보관하며 handler, 실행 함수, 자격 증명 필드를 갖지 않습니다.
  - `McpServerCatalog.from_registry()`는 `ToolRegistry.allowed_tools()`에 이미 등록된 Tool만 복사합니다. 동적 Tool 발견·등록이나 실제 Tool 실행은 하지 않습니다.
  - `list_tools()`는 MCP `tools/list` 관례의 `name`, `description`, `inputSchema`를 새 snapshot으로 반환합니다. 생성과 반환 시 deep copy하므로 client가 받은 Schema를 수정해도 catalog가 변하지 않습니다.
  - 이 첫 모델은 외부 MCP SDK, STDIO, 네트워크, subprocess를 사용하지 않습니다. 이후 호출 경로도 기존 allowlist·Schema·정책·승인·감사 경계를 유지해야 합니다.
- `src/ai_platform/mcp/__init__.py`
  - 교육용 MCP catalog의 제한된 공개 API를 export합니다.
- `examples/volume03/mcp_tool_catalog.py`
  - 순수 `safe_calculator`, `safe_text_case`만 명시적으로 등록하고 Tool을 호출하지 않은 채 이름과 설명을 출력합니다. 파일·셸·네트워크·환경 변수·외부 서비스에 접근하지 않습니다.
- `tests/volume03/test_mcp_catalog.py`
  - allowlisted Tool만 MCP 목록 형태로 투영됨, catalog에 `execute()`가 없음, 반환된 Schema 변경이 이후 snapshot에 영향을 주지 않음, 중복 이름·객체 외 Schema 거부를 검증합니다.
- `docs/volume03-tool-calling-mcp/06-mcp-tool-catalog.md`
  - Tool 발견과 실행 권한의 분리, offline 실습, snapshot 복사, 운영 MCP transport에서 추가할 인증·인가·제한·감사 경계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 여섯 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_tool_catalog.py
safe_calculator: 두 유한 수의 허용된 사칙연산을 수행합니다. 외부 시스템을 변경하지 않습니다.
safe_text_case: 문자열을 대문자 또는 소문자로만 변환합니다. 외부 시스템을 변경하지 않습니다.

$ uv run pytest tests/volume03/test_mcp_catalog.py -q
3 passed in 0.06s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 15 source files

$ uv run pytest -q
94 passed in 0.86s

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

MCP Tool 호출 요청을 받기 전 단계로, 신뢰되지 않은 client의 `name`과 JSON 객체 arguments를 좁게 파싱하고 기존 `ToolRegistry.validate_request()`로 재검증하는 전송 계층 없는 call-request 모델을 구현합니다. 실행, STDIO, 네트워크, 외부 MCP SDK, 파일·셸·네트워크 Tool 등록은 계속 하지 않습니다.
