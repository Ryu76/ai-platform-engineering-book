# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 **학습 과제**로 오프라인 CLI·Mock·통합 테스트 경계를 연결하는 한국어 과제와 그 문서 계약 테스트를 추가했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 핵심 정리와 Volume 완료 검수가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/12-exercises.md`
  - 기본·응용·심화 과제를 오프라인 `--offline-demo`, `ScriptedClient` Mock 단위 테스트, 별도 프로세스 통합 테스트로 단계화해 한국어로 작성했습니다.
  - 모든 명령의 실행 위치, 코드 설명, 정상 결과, 오류 해결, 응용 실습, 보안 경고, 완료 체크리스트를 포함했습니다.
  - 라이브 호출·API 키·네트워크 없이 CLI 시작·입력·응답·종료 계약을 검증해야 한다는 경계를 명시했습니다.
- `tests/integration/test_volume01_exercises.py`
  - 과제 문서의 기본·응용·심화 항목과 오프라인 CLI, Mock 단위 테스트, 통합 테스트 명령이 실제 파일과 함께 존재하는지 검사합니다.
  - 과제가 실제 API·키·네트워크 없이 수행된다는 문서 계약을 회귀 검사합니다.
- `docs/volume01-llm-fundamentals/README.md`
  - 12장 오프라인 실행 경계 과제 링크를 추가했습니다.

이 슬라이스는 기존 `ConversationHistory`, `run_chat_loop()`, `OfflineDemoClient`를 변경하지 않았습니다. 검증은 문서 계약 검사와 기존 `--offline-demo` 경계만 사용했으므로 실제 LLM API 호출·외부 데이터 전송·비용·배포는 수행하지 않았습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run pytest tests/integration/test_volume01_exercises.py -q
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
.                                                                        [100%]
1 passed in 0.04s

$ uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
링크 검증 통과
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
코드 블록 검증 통과

$ bash scripts/run_all_tests.sh
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
All checks passed!
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
Success: no issues found in 7 source files
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
문서 검증 통과: Volume 11개
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
링크 검증 통과
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
코드 블록 검증 통과
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
비밀값 검사 통과
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-8.4.2, pluggy-1.6.0
rootdir: E:\python\ai-platform-engineering-book
configfile: pyproject.toml
testpaths: tests
collected 57 items

tests\integration\test_volume01_chat_cli.py .                            [  1%]
tests\integration\test_volume01_exercises.py .                           [  3%]
tests\unit\test_chat.py ........                                         [ 17%]
tests\unit\test_llm_client.py ................................           [ 73%]
tests\unit\test_settings.py ..                                           [ 77%]
tests\unit\test_usage.py .............                                   [100%]

============================= 57 passed in 0.75s ==============================

$ git diff --check
(exit 0)
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 실제 외부 LLM API 호출·배포·데이터 전송은 수행하지 않았습니다.

## 알려진 차단 사항

- 없음. 라이브 모드는 입력을 선택한 제공자에 전송하고 비용이 발생할 수 있으므로, 학습·CI 검증에는 `--offline-demo`와 Mock/통합 테스트를 사용합니다.

## 다음 작업

- Volume 01의 핵심 정리 문서를 한국어로 추가하고, 완료한 장·실습·테스트 경로를 한 곳에서 다시 확인할 수 있도록 하는 한 개의 작은 문서 슬라이스를 구현합니다.
