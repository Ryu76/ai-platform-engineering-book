# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 **System Prompt와 생성 파라미터** 문서, 검증 가능한 생성 파라미터 모델, 안전한 선택 실행 예제를 추가했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 Streaming, 오류 처리 심화, 비용·사용량, CLI 챗봇 및 미니 프로젝트가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/06-system-prompt-and-parameters.md`
  - System Prompt와 User Message의 책임 분리, Temperature·Top-p·최대 출력 토큰·Stop Sequence의 동작과 한계, 안전한 선택 라이브 호출, 오류 해결, 응용 실습·과제·체크리스트를 한국어로 작성했습니다.
- `docs/volume01-llm-fundamentals/README.md`
  - 완료된 6장 문서를 로컬 링크로 연결했습니다.
- `src/ai_platform/llm/client.py`
  - `GenerationParameters`를 추가했습니다. Temperature(`0~2`), Top-p(`0 초과~1 이하`), 양의 최대 출력 토큰, 비어 있지 않은 최대 4개의 Stop Sequence를 요청 전 검증하고, 지정 값만 OpenAI Chat Completions 호환 payload로 직렬화합니다.
  - `LlmClient.complete()`가 선택적인 `generation` 인자를 받아 기존의 모델·메시지 요청 경계에 합치도록 확장했습니다.
- `src/ai_platform/llm/__init__.py`
  - `GenerationParameters` 공개 API를 추가했습니다.
- `examples/volume01/system_prompt_parameters.py`
  - 학습자가 명시 실행할 때만 외부 호출을 수행하는 System Prompt·생성 파라미터 예제를 추가했습니다.
- `tests/unit/test_llm_client.py`
  - 네트워크 없는 Mock 전송 계층으로 파라미터 payload, 허용 경계값, 잘못된 수치, 빈/과다 Stop Sequence를 확인하는 테스트를 추가했습니다.

이 슬라이스는 동일한 AI 업무 처리 플랫폼의 LLM 호출 경계를 확장합니다. 다음 Streaming 장은 이 `ChatMessage`와 `GenerationParameters` 계약을 유지한 채 토큰 조각 전달을 추가합니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run pytest tests/unit/test_llm_client.py -q
..............                                                           [100%]
14 passed in 0.24s

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
collected 16 items

tests\unit\test_llm_client.py ..............                             [ 87%]
tests\unit\test_settings.py ..                                           [100%]

============================= 16 passed in 0.15s ==============================

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ uv run python -m compileall -q examples/volume01/system_prompt_parameters.py
(exit 0)

$ git diff --check
(exit 0)
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 실제 외부 LLM API 호출은 수행하지 않았습니다. 단위 테스트는 주입한 Mock 전송 계층만 사용합니다.

## 알려진 차단 사항

- 없음. `examples/volume01/system_prompt_parameters.py`의 라이브 호출은 학습자가 자신의 키를 설정하고 명시 실행할 때만 발생합니다.

## 다음 작업

- Volume 01의 `07-streaming.md`와 LLM 스트림 이벤트 계약·Mock 단위 테스트를 한 슬라이스로 구현합니다.
