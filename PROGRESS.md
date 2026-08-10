# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 **안전한 최초 호출** 문서와 OpenAI 호환 LLM 클라이언트·Mock 단위 테스트
- 완료 선언: 아직 하지 않음. Volume 01의 System Prompt·생성 파라미터, Streaming, 오류 처리 심화, 비용·사용량, CLI 챗봇 및 미니 프로젝트가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/05-first-call.md`
  - 최초 호출의 요청·응답 구조, 환경 변수, 선택적 라이브 호출, 오류 해결, 과제와 체크리스트를 한국어로 작성했습니다.
- `docs/volume01-llm-fundamentals/README.md`
  - 완료된 Volume 01 장 문서를 로컬 링크로 연결했습니다.
- `src/ai_platform/llm/__init__.py`
- `src/ai_platform/llm/client.py`
  - API 키·모델·URL·Timeout 검증, OpenAI Chat Completions 호환 요청, HTTP/연결/응답 형식 오류 분리, 교체 가능한 `JsonTransport`를 구현했습니다.
- `src/ai_platform/core/settings.py`
  - `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS` 설정과 양수 Timeout 검증을 추가했습니다.
- `examples/volume01/first_call.py`
  - 학습자가 명시적으로 실행할 때만 외부 호출을 수행하는 최초 호출 예제를 추가했습니다.
- `tests/unit/test_llm_client.py`
  - 외부 네트워크 없이 성공 응답, 요청 형식, 비밀값 비노출, 제공자 오류, 잘못된 응답, 메시지 검증을 확인합니다.
- `tests/unit/test_settings.py`
  - 기본 URL·Timeout 및 잘못된 Timeout 설정을 확인합니다.
- `.env.example`
  - 안전한 `LLM_TIMEOUT_SECONDS=30` 예시를 추가했습니다.

이 슬라이스는 동일한 AI 업무 처리 플랫폼의 LLM 호출 경계를 제공합니다. 다음 장의 System Prompt와 생성 파라미터는 이 `LlmClient`를 확장해 사용합니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run pytest tests/unit/test_llm_client.py -q
.....                                                                    [100%]
5 passed in 0.13s

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
collected 7 items

tests\unit\test_llm_client.py .....                                      [ 71%]
tests\unit\test_settings.py ..                                           [100%]

============================== 7 passed in 0.15s ==============================

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

- 없음. 라이브 호출은 의도적으로 학습자가 키를 설정하고 `examples/volume01/first_call.py`를 명시 실행할 때만 발생합니다.

## 다음 작업

- Volume 01의 `06-system-prompt-and-parameters.md`와 `LlmClient`의 생성 파라미터(Temperature, Top-p, 최대 출력 토큰, Stop Sequence) 검증·Mock 테스트를 한 슬라이스로 구현합니다.
