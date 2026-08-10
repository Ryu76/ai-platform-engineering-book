# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **Function Calling 실행 제어**
- 완료 선언: 아직 하지 않음. Volume 03의 권한·승인, 실행 로그, MCP Server/Client, Resource/Prompt, STDIO, Hermes/Codex 연동을 구현·문서화·검증해야 합니다.

## 이번 슬라이스: Tool timeout과 제한된 retry

- `src/ai_platform/tools/execution.py`
  - `ToolExecutionPolicy`가 양의 유한 timeout과 총 1~3회의 시도만 받도록 제한합니다.
  - `execute_with_policy()`는 매 시도마다 기존 `ToolRegistry.execute()`를 호출합니다. 따라서 allowlist·JSON Schema 검증을 우회하는 별도 실행 경로가 없습니다.
  - handler가 명시적으로 낸 `RetryableToolError`만 재시도합니다. validation, allowlist, timeout 및 다른 오류는 즉시 실패하며 자동 재시도하지 않습니다.
  - timeout은 daemon worker의 완료 대기만 중단합니다. Python thread를 강제 취소하지 못하므로 부작용 없는 handler 교육 예제에만 사용합니다.
- `examples/volume03/controlled_tool_execution.py`
  - 등록된 순수 `retryable_upper` handler가 고정된 첫 일시 실패 뒤 문자열 대문자 변환을 수행합니다. 파일·셸·네트워크·환경 변수·실제 서비스에는 접근하지 않습니다.
- `tests/volume03/test_tool_execution.py`
  - 성공 전 제한 재시도, validation/미등록 이름의 미재시도, timeout, retry 횟수 소진, 정책 상한을 검증합니다.
  - timeout handler는 `Event`로 해제해 테스트 완료 뒤 worker가 지속되지 않게 합니다.
- `docs/volume03-tool-calling-mcp/03-tool-timeout-retry.md`
  - retry 분류, timeout 취소 한계, 오프라인 실습, 오류 해결과 운영 시 멱등성·승인 조건을 문서화했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/controlled_tool_execution.py
retryable_upper: AI PLATFORM (2 attempts)

$ uv run pytest tests/volume03/test_tool_execution.py -q
4 passed in 0.08s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 11 source files

$ uv run pytest -q
81 passed in 0.93s

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

위험도를 명시한 Tool 권한·사람 승인 정책을 순수한 테스트용 handler로 구현합니다. 승인되지 않은 요청은 handler에 도달하지 않게 하고, 승인 토큰이 allowlist·Schema 검증을 우회하지 않도록 합니다.
