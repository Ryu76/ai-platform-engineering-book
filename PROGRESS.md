# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 권 단위 인계·학습자 체크리스트를 추가하고, 목차·실행 결과물·용어집·Volume 02 연결이 실제 파일을 계속 참조하는지 문서 계약 테스트로 검증했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 모든 장이 Chapter Definition of Done을 충족하는지 장별 출고 감사와 전체 실습 재실행 근거가 필요합니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/checklist.md`
  - 학습자가 직접 표시할 개념·보안·오프라인 실행 체크리스트를 작성했습니다.
  - `--offline-demo`, Mock 단위 테스트, 별도 프로세스 통합 테스트, 전체 검사 명령을 실제 경로로 연결했습니다.
  - Volume 02로 인계하는 settings·Client·대화 이력·사용량·CLI 경계와 Prompt Injection 분리 원칙을 명시했습니다.
  - 제작 검수에 필요한 파일 존재와 학습 완료를 구분했으며, 장별 DoD 출고 감사 전에는 Volume 01 완료를 선언하지 않는 상태를 기록했습니다.
- `docs/volume01-llm-fundamentals/README.md`
  - Volume 목차에서 새 체크리스트로 이동하는 링크를 추가했습니다.
- `docs/glossary.md`
  - Token, Tokenizer, Context Window, System Message, Streaming, Hallucination의 한국어 정의를 추가했습니다.
- `tests/integration/test_volume01_completion_contract.py`
  - 13개 기존 학습 문서와 체크리스트, settings·Client·대화·사용량·CLI·단위/통합 테스트 결과물이 존재하는지 검사합니다.
  - 체크리스트의 오프라인 실행·전체 검사 명령·명시적 DoD 보류 문구·Volume 02 인계와 핵심 용어집 항목이 사라지지 않도록 회귀 검사합니다.

이번 변경은 문서, 오프라인 검증, 용어집만 다룹니다. 실제 LLM API 호출·외부 데이터 전송·비용·배포는 수행하지 않았습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run pytest tests/integration/test_volume01_completion_contract.py -q && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
.                                                                        [100%]
1 passed in 0.04s
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과

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
collected 59 items

tests\integration\test_volume01_chat_cli.py .
tests\integration\test_volume01_completion_contract.py .
tests\integration\test_volume01_exercises.py .
tests\integration\test_volume01_summary.py .
tests\unit\test_chat.py ........
tests\unit\test_llm_client.py ................................
tests\unit\test_settings.py ..
tests\unit\test_usage.py .............

============================= 59 passed in 0.88s ==============================

$ git diff --check
(exit 0)
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 실제 외부 LLM API 호출·배포·데이터 전송은 수행하지 않았습니다.

## 알려진 차단 사항

- Volume 01을 완료로 선언할 수 없습니다. 권의 체크리스트와 인계 결과물은 준비되었지만, 모든 장이 PRD의 14개 Chapter Definition of Done 항목을 각각 충족하는지 장별로 검수·보완한 근거가 아직 없습니다. 특히 `01-learning-objectives.md`는 현재 학습 목표·완료 기준·다음 장 연결만 있어 전체 장 템플릿의 모든 섹션을 갖추지 않았습니다.
- 라이브 모드는 입력을 선택한 제공자에 전송하고 비용이 발생할 수 있으므로, 학습·CI 검증에는 `--offline-demo`와 Mock/통합 테스트를 사용합니다.

## 다음 작업

- Volume 01의 첫 장 `01-learning-objectives.md`를 PRD Chapter Definition of Done에 맞는 독립 장으로 보완하고, 해당 장의 문서 계약 테스트와 오프라인 검증을 추가합니다.
