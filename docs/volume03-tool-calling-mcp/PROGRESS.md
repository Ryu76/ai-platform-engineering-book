# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP Prompt의 정적·보간 없는 allowlist (전송·실행 계층 없음)**
- 완료 선언: 아직 하지 않음. Volume 03의 MCP 호출 dispatcher, STDIO, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: 사용자 입력을 보간하지 않는 짧은 정적 MCP Prompt

- `src/ai_platform/mcp/prompts.py`
  - `McpPromptMessage`는 `system`·`user`·`assistant` role과 비어 있지 않은 최대 4,096자 content만 받습니다.
  - `McpStaticPrompt`는 비어 있지 않은 name·description과 1~8개의 고정 message tuple만 받으며 template engine·callback·handler가 없습니다.
  - `McpPromptCatalog`는 중복 name을 거부하고, 이름을 정규화하지 않은 정확한 allowlist key로만 조회합니다. `get_prompt()`는 arguments·변수·사용자 입력을 받지 않고 고정 message snapshot만 돌려줍니다.
- `src/ai_platform/mcp/__init__.py`
  - 기존 Tool catalog·call-request·Resource API와 함께 제한된 static Prompt API만 export합니다.
- `examples/volume03/mcp_static_prompts.py`
  - 명시적으로 등록한 `tool-safety-reminder`의 내장 system message 한 개만 list/get 하고 출력합니다. 사용자 입력 보간, 파일, 셸, 네트워크, 외부 MCP Server, Tool handler에 접근하지 않습니다.
- `tests/volume03/test_mcp_prompts.py`
  - allowlisted 고정 message의 목록·조회, 공백 suffix alias와 interpolation arguments 거부, 중복 name·비허용 role·과대 content·빈/비정적 message 목록 거부, 실행 API 부재를 검증합니다.
- `docs/volume03-tool-calling-mcp/09-mcp-static-prompts.md`
  - Prompt와 Tool 권한을 분리하고, 정적 계약·오프라인 실습·입력 보간 금지·동적 Prompt 운영 경계를 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 아홉 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_static_prompts.py
tool-safety-reminder: system: Use only reviewed, allowlisted Tools and request approval when required.

$ uv run pytest tests/volume03/test_mcp_prompts.py -q
3 passed in 0.08s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 18 source files

$ uv run pytest -q
110 passed in 0.91s

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

MCP 호출 dispatcher를 전송 계층 없이 좁게 모델링합니다. parser와 기존 `ToolRegistry` 재검증을 통과한 요청도 정책·승인·감사·timeout 경계에 묶어 명시적으로 dispatch하고, Resource/Prompt 조회와 Tool 실행 권한을 계속 분리합니다. 파일·셸·네트워크·STDIO는 하지 않습니다.
