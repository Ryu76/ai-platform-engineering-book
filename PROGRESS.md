# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 **Streaming** 문서, OpenAI 호환 SSE 스트리밍 계약, 안전한 선택 실행 예제와 네트워크 없는 Mock 테스트를 추가했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 오류 처리 심화, 비용·사용량, CLI 챗봇 및 미니 프로젝트가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/07-streaming.md`
  - Streaming과 완성 응답의 차이, SSE `data:` 이벤트, delta·종료 이유·선택적 사용량, 외부 호출 없는 검증, 오류 해결, 응용 실습·과제·체크리스트를 한국어로 작성했습니다.
- `docs/volume01-llm-fundamentals/README.md`
  - 완료된 Streaming 장을 로컬 링크로 연결했습니다.
- `src/ai_platform/llm/client.py`
  - `StreamChunk`, 일반 완료와 스트리밍을 함께 지원하는 `LlmTransport`, `LlmClient.stream()`을 추가했습니다.
  - `stream: true` payload와 기존 메시지·생성 파라미터 계약을 사용하고, OpenAI 호환 SSE의 단일 `data:` 행과 `[DONE]`을 처리합니다.
  - 텍스트 delta, 종료 이유, 선택적 사용량, 비정상 이벤트·HTTP 오류를 명시적으로 처리합니다.
- `src/ai_platform/llm/__init__.py`
  - `StreamChunk`를 공개 API로 추가했습니다.
- `examples/volume01/streaming.py`
  - 학습자가 명시 실행할 때만 외부 호출을 수행하고, delta를 즉시 출력하며 사용량 미반환도 안전하게 안내하는 예제를 추가했습니다.
- `tests/unit/test_llm_client.py`
  - Mock 스트림으로 요청 직렬화, delta 결합, 종료 이유, 사용량, 제공자 오류, SSE data 행과 UTF-8 오류를 검사하는 테스트를 추가했습니다.

이 슬라이스는 동일한 AI 업무 처리 플랫폼의 Volume 01 호출 경계를 스트리밍까지 확장합니다. 다음 오류 처리 장은 이 `LlmResponse`·`StreamChunk` 오류 계약을 유지하면서 제한된 재시도와 시간 초과 분류를 추가합니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run pytest tests/unit/test_llm_client.py -q
.....................                                                    [100%]
21 passed in 0.15s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 5 source files

$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-8.4.2, pluggy-1.6.0
rootdir: E:\python\ai-platform-engineering-book
configfile: pyproject.toml
testpaths: tests
collected 23 items

tests\unit\test_llm_client.py .....................                      [ 91%]
tests\unit\test_settings.py ..                                           [100%]

============================= 23 passed in 0.16s ==============================

$ uv run python -m compileall -q examples/volume01/streaming.py
(exit 0)

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

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 실제 외부 LLM API 호출은 수행하지 않았습니다. 단위 테스트는 주입한 Mock 전송 계층만 사용합니다.

## 알려진 차단 사항

- 없음. `examples/volume01/streaming.py`의 라이브 호출은 학습자가 자신의 키를 설정하고 명시 실행할 때만 발생합니다.

## 다음 작업

- Volume 01의 `08-error-handling.md`와 제한된 재시도·시간 초과·재시도 불가 오류의 Mock 단위 테스트를 한 슬라이스로 구현합니다.
