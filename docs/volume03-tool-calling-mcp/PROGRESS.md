# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **Function Calling 기초**
- 완료 선언: 아직 하지 않음. Volume 03의 여러 Tool 선택, timeout/retry, 권한·승인, 실행 로그, MCP Server/Client, Resource/Prompt, STDIO, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: 여러 Function Schema와 Mock dispatch

- `src/ai_platform/tools/registry.py`
  - `allowed_tools()`를 추가해 Registry에 이미 등록된 Tool만 안정된 순서로 내보냅니다.
  - 문자열의 `upper`/`lower`만 수행하는 순수 `SAFE_TEXT_CASE` Tool을 추가했습니다. 파일·셸·네트워크·환경 변수에는 접근하지 않습니다.
- `src/ai_platform/tools/function_calling.py`
  - 등록 Tool을 OpenAI 호환 `{"type": "function", "function": {...}}` 정의로 직렬화하는 `serialize_function_tools()`를 추가했습니다.
  - 모델 응답의 `id`, `type`, `function.name`, JSON 객체 `function.arguments`를 엄격히 파싱합니다.
  - `dispatch_function_call()`은 별도 실행 경로를 만들지 않고 기존 `ToolRegistry.execute()`로 전달하므로 allowlist와 JSON Schema 검증을 우회할 수 없습니다.
- `examples/volume03/mock_function_calling.py`
  - 두 Schema를 받는 고정 Mock 응답을 파싱·dispatch해 `safe_text_case: AI PLATFORM`을 출력합니다. 실제 LLM API·네트워크 호출은 없습니다.
- `tests/volume03/test_function_calling.py`
  - 두 allowlisted Tool의 직렬화, Mock 정상 호출, malformed/non-object JSON 거부, 미등록 `delete_file` 및 enum 밖 인자의 재거부를 검증합니다.
- `docs/volume03-tool-calling-mcp/02-function-calling-mock-dispatch.md`
  - 제공자 호환 형식, 파싱·실행 경계, 오프라인 실습, 오류 해결과 운영상 한계를 문서화했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ /c/Users/HODI/.local/bin/uv.exe run python examples/volume03/mock_function_calling.py
safe_text_case: AI PLATFORM

$ /c/Users/HODI/.local/bin/uv.exe run ruff check .
All checks passed!

$ /c/Users/HODI/.local/bin/uv.exe run mypy src
Success: no issues found in 10 source files

$ /c/Users/HODI/.local/bin/uv.exe run pytest -q
77 passed in 1.42s

$ /c/Users/HODI/.local/bin/uv.exe run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ /c/Users/HODI/.local/bin/uv.exe run python scripts/validate_links.py
링크 검증 통과

$ /c/Users/HODI/.local/bin/uv.exe run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ /c/Users/HODI/.local/bin/uv.exe run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv`는 Hermes 활성 가상환경과 프로젝트 `.venv`의 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 모든 명령을 정상 실행했습니다. 실제 LLM 호출, MCP 통신, 파일·시스템 변경, 외부 네트워크 요청은 수행하지 않았습니다.

## 다음 슬라이스

Tool 실행의 timeout과 제한된 retry를 순수한 테스트용 handler로 구현합니다. 재시도 가능한 오류만 구분하고, timeout/실패가 allowlist·인자 검증·사람 승인 경계를 우회하지 않도록 합니다.
