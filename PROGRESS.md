# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 마지막 장인 **핵심 정리**를 한국어로 작성하고, 오프라인 검증 경계와 다음 Volume 02 연결이 유지되는지 검사하는 문서 계약 테스트를 추가했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 권 단위 Definition of Done(전체 실습 재실행, 미니 프로젝트, 학습자 체크리스트, 용어집, 다음 Volume 인계)을 독립적으로 감사한 뒤에만 Volume 완료로 처리합니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/11-summary.md`
  - Token·Context Window·역할 기반 메시지·생성 파라미터·스트리밍·제한된 재시도·사용량·대화 이력을 하나의 안전한 LLM 호출 흐름으로 정리했습니다.
  - `--offline-demo`, Mock 단위 테스트, 별도 프로세스 통합 테스트의 외부 전송 없는 경계와 `bash scripts/run_all_tests.sh` 검증 절차를 한국어로 명시했습니다.
  - Prompt 템플릿, 구조화된 출력, 입력 검증, Prompt Injection 방어를 다룰 Volume 02로 연결했습니다.
- `tests/integration/test_volume01_summary.py`
  - 핵심 정리에 14개 필수 섹션, 핵심 개념, 실제 오프라인 CLI·단위·통합 테스트 경로, 전체 검사 명령, 외부 API 키·네트워크 없는 실행 경계, Volume 02 연결이 유지되는지 회귀 검사합니다.
- `docs/volume01-llm-fundamentals/README.md`
  - 13번 핵심 정리를 실제 문서 링크로 연결했습니다.

이 슬라이스는 실행 코드와 외부 제공자 설정을 변경하지 않았습니다. 검증은 기존 오프라인 CLI·Mock·문서 검사만 사용했으므로 실제 LLM API 호출·외부 데이터 전송·비용·배포는 수행하지 않았습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run pytest tests/integration/test_volume01_summary.py -q && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
.                                                                        [100%]
1 passed in 0.04s
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
링크 검증 통과
warning: `VIRTUAL_ENV=C:\Users\HODI\AppData\Local\hermes\hermes-agent\venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
코드 블록 검증 통과

$ bash scripts/run_all_tests.sh
All checks passed!
Success: no issues found in 7 source files
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-8.4.2, pluggy-1.6.0
rootdir: E:\python\ai-platform-engineering-book
configfile: pyproject.toml
testpaths: tests
collected 58 items

tests\integration\test_volume01_chat_cli.py .                            [  1%]
tests\integration\test_volume01_exercises.py .                           [  3%]
tests\integration\test_volume01_summary.py .                             [  5%]
tests\unit\test_chat.py ........                                         [ 18%]
tests\unit\test_llm_client.py ................................           [ 74%]
tests\unit\test_settings.py ..                                           [ 77%]
tests\unit\test_usage.py .............                                   [100%]

============================= 58 passed in 0.73s ==============================

$ git diff --check
(exit 0)
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 위 전체 검사 출력에서는 같은 경고가 각 `uv run` 단계 앞에 반복되었습니다. 실제 외부 LLM API 호출·배포·데이터 전송은 수행하지 않았습니다.

## 알려진 차단 사항

- 없음. 라이브 모드는 입력을 선택한 제공자에 전송하고 비용이 발생할 수 있으므로, 학습·CI 검증에는 `--offline-demo`와 Mock/통합 테스트를 사용합니다.

## 다음 작업

- Volume 01의 권 단위 Definition of Done을 한 개의 독립 감사 슬라이스로 검증합니다. 장 링크·실습 재실행 경로·미니 프로젝트·체크리스트·용어집·Volume 02 인계 결과물을 실제 파일과 검사로 확인하고, 충족할 때만 Volume 01을 완료 처리합니다.
