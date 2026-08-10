# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP Tool call request 검증 (전송·실행 계층 없음)**
- 완료 선언: 아직 하지 않음. Volume 03의 MCP 호출 dispatcher, Resource/Prompt, STDIO, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: 신뢰되지 않은 MCP 호출 JSON을 실행 전 allowlist·Schema로 재검증

- `src/ai_platform/mcp/requests.py`
  - `parse_mcp_tool_call_request()`는 정확히 `name`과 객체형 `arguments`만 가진 JSON 문자열을 받습니다. 최상위 추가·누락 키, 비문자열 name, 배열 arguments를 거부합니다.
  - JSON object의 중복 키와 JSON 표준 밖 `NaN`·`Infinity` 상수를 거부하므로 앞선 값 덮어쓰기나 비유한 수의 모호성을 실행 경계에 넘기지 않습니다.
  - `McpToolCallRequest`는 arguments snapshot을 복사하며 handler·결과·`execute()`를 갖지 않습니다.
  - `validate_against()`는 새 allowlist를 만들지 않고 기존 `ToolRegistry.validate_request()`를 호출합니다. 파싱 성공 뒤에도 허용 Tool, required/additionalProperties, 타입, enum을 실행 없이 재검증합니다.
- `src/ai_platform/mcp/__init__.py`
  - catalog API와 함께 제한된 call-request API만 export합니다.
- `examples/volume03/mcp_tool_call_request.py`
  - 명시적으로 등록한 순수 `safe_text_case`의 JSON 요청을 검증만 하고 `validated without execution: safe_text_case`를 출력합니다. handler, 파일, 셸, 네트워크, 환경 변수, 외부 서비스에는 접근하지 않습니다.
- `tests/volume03/test_mcp_call_requests.py`
  - 유효 요청도 handler를 실행하지 않음, 비계약·중복·비표준 JSON 거부, allowlist·enum의 registry 재검증, caller dict 변경으로부터 arguments snapshot이 분리됨을 검증합니다.
- `docs/volume03-tool-calling-mcp/07-mcp-tool-call-request-validation.md`
  - catalog 신뢰 금지, 제한된 JSON 계약, parser와 registry 재검증의 분리, 실제 MCP transport에 아직 없는 JSON-RPC/인증·인가/제한/승인·감사 경계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 일곱 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_tool_call_request.py
validated without execution: safe_text_case

$ uv run pytest tests/volume03/test_mcp_call_requests.py -q
10 passed in 0.09s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 16 source files

$ uv run pytest -q
104 passed in 0.92s

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

실행을 만들기 전에 MCP Resource를 읽기 전용 정적 catalog로 모델링합니다. 명시적 allowlist의 URI·이름·MIME type·짧은 내장 텍스트만 snapshot으로 노출하고, 로컬 파일 읽기·경로 해석·STDIO·네트워크는 하지 않습니다. Resource 요청의 범위와 Tool 실행 권한을 계속 분리합니다.
