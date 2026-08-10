# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 **오류 처리와 제한된 재시도** 문서, 시간 초과·네트워크·HTTP 상태 오류 분류, 명시적이고 제한된 완료 요청 재시도, 안전한 선택 실행 예제와 네트워크 없는 Mock 테스트를 추가했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 비용·사용량, CLI 챗봇, 미니 프로젝트·과제·핵심 정리가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/08-error-handling.md`
  - 시간 초과, 네트워크, 제공자 HTTP, 응답 형식 오류의 구분과 429·5xx에만 적용하는 제한된 지수 백오프를 한국어로 작성했습니다.
  - 스트림의 부분 출력 후 자동 재시도가 중복 출력을 만들 수 있는 이유, 키·프롬프트를 로그에 넣지 않는 원칙, 오류 해결·응용 실습·과제·체크리스트를 포함했습니다.
- `docs/volume01-llm-fundamentals/README.md`
  - 완료된 오류 처리 장을 로컬 링크로 연결했습니다.
- `src/ai_platform/llm/client.py`
  - `LlmTimeoutError`, 상태 코드를 보존하는 `LlmRemoteError`, 최대 1~5회로 한정한 `RetryPolicy`를 추가했습니다.
  - `complete()`는 명시적 정책이 있을 때만 네트워크·시간 초과·429·500·502·503·504를 재시도합니다.
  - 400·401·403·404, 응답 형식 오류, 스트림은 자동 재시도하지 않습니다. `UrllibJsonTransport`는 timeout 원인을 안전한 시간 초과 오류로 분류합니다.
- `src/ai_platform/llm/__init__.py`
  - `LlmTimeoutError`, `RetryPolicy`를 공개 API로 추가했습니다.
- `examples/volume01/error_handling.py`
  - 학습자가 명시 실행할 때만 외부 호출하며, 분류된 오류를 API 키·원문 없이 안내하는 예제를 추가했습니다.
- `tests/unit/test_llm_client.py`
  - Mock 전송으로 503 후 성공, 401 미재시도, 네트워크·시간 초과 시도 한도와 백오프, 잘못된 정책을 검증했습니다.

이 슬라이스는 같은 AI 업무 처리 플랫폼의 Volume 01 호출 경계에 실패 분류와 제한된 복구 정책을 추가합니다. 다음 비용·사용량 장은 기존 `LlmResponse.usage` 및 `StreamChunk.usage` 계약을 유지하며 토큰·비용 추정과 보고를 추가합니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run pytest tests/unit/test_llm_client.py -q
................................                                         [100%]
32 passed in 0.17s

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
collected 34 items

tests\unit\test_llm_client.py ................................           [ 94%]
tests\unit\test_settings.py ..                                           [100%]

============================= 34 passed in 0.31s ==============================

$ uv run python -m compileall -q examples/volume01/error_handling.py
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

- 없음. `examples/volume01/error_handling.py`의 라이브 호출은 학습자가 자신의 키를 설정하고 명시 실행할 때만 발생합니다.

## 다음 작업

- Volume 01의 `09-usage-and-cost.md`와 토큰 사용량·오프라인 비용 추정·예산 상한의 Mock 단위 테스트를 한 슬라이스로 구현합니다.
