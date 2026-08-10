# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **Tool Calling 기초**
- 완료 선언: 아직 하지 않음. Volume 03의 Function Calling, 여러 Tool 선택, timeout/retry, 권한·승인, 실행 로그, MCP Server/Client, Resource/Prompt, STDIO, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: allowlist 계산기와 인자 검증

- `src/ai_platform/tools/registry.py`
  - 등록된 이름만 호출하는 `ToolRegistry`를 추가했습니다.
  - 객체형 JSON Schema의 required, 타입(number/string), enum, `additionalProperties: false`를 최소 범위로 검증합니다.
  - `safe_calculator`는 `add`, `subtract`, `multiply`, `divide`만 실행하는 순수 로컬 함수입니다. 파일·셸·네트워크·환경 변수·외부 서비스에 접근하지 않습니다.
- `examples/volume03/safe_calculator.py`
  - 고정된 `21 * 2` 입력으로 allowlisted Tool 경계를 재현하는 오프라인 예제를 추가했습니다.
- `tests/volume03/test_tool_registry.py`
  - 정상 계산, 미등록 Tool 거부, 누락·잘못된·추가 인자 거부, 0 나누기, 중복 등록과 미지원 Schema 타입을 네트워크 없이 검증합니다.
- `docs/volume03-tool-calling-mcp/01-tool-calling-allowlist.md`
  - Tool Calling, allowlist, JSON Schema, 실행 경계, 단계별 오프라인 실습, 오류 해결, 운영상 승인 한계를 문서화했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/safe_calculator.py
42

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 9 source files

$ uv run pytest -q
70 passed in 0.80s

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

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv`의 경로가 다르다는 경고를 출력했지만, 프로젝트 가상환경에서 모든 명령이 정상 종료했습니다. 실제 LLM 호출, MCP 통신, 파일·시스템 변경, 외부 네트워크 요청은 수행하지 않았습니다.

## 다음 슬라이스

여러 allowlisted Tool의 JSON Schema를 모델 제공자 호환 Function Calling 형식으로 직렬화하고, 모델의 Tool 선택 결과를 이 Registry 경계로 안전하게 연결합니다. 실제 LLM 호출은 Mock만 사용하고 허용되지 않은 Tool·실제 시스템 변경은 수행하지 않습니다.
