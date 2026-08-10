# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 **토큰 사용량과 비용 추정** 문서, `Decimal` 기반 입력·출력 비용 계산, 통화 일치 검증, 추정 비용 상한 검사, 외부 호출 없는 실행 예제와 단위 테스트를 추가했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 CLI 챗봇, 미니 프로젝트·과제·핵심 정리가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/09-usage-and-cost.md`
  - 입력·출력 토큰, 100만 토큰당 가격표, `Decimal` 계산식, 사용량 미수신, 실제 청구·사전 추정·로컬 상한 검사의 차이를 한국어로 작성했습니다.
  - 실행 위치가 있는 오프라인 실습, 정상 결과, 오류 해결, 응용 실습, 과제, 체크리스트를 포함했습니다.
- `docs/volume01-llm-fundamentals/README.md`
  - 완료된 비용·사용량 장을 로컬 링크로 연결했습니다.
- `docs/glossary.md`
  - 토큰 사용량, 비용 추정, 지수 백오프 용어를 추가했습니다.
- `src/ai_platform/llm/usage.py`
  - `ModelPricing`, `CostEstimate`, `CostBudget`, `estimate_cost()`를 추가했습니다.
  - 가격·예산은 유한한 0 이상 `Decimal`과 세 글자 대문자 통화만 허용하며, 다른 통화 비교와 상한 초과를 안전한 예외로 구분합니다.
  - 이 모듈은 네트워크·환율 조회·반올림을 수행하지 않습니다.
- `src/ai_platform/llm/__init__.py`
  - 비용 추정 공개 API를 추가했습니다.
- `examples/volume01/usage_and_cost.py`
  - 고정 토큰 사용량과 학습용 가격표를 사용해 외부 API 없이 비용·예산 검사를 실행하는 예제를 추가했습니다.
- `tests/unit/test_usage.py`
  - 입력·출력·합계 계산, 상한 일치·초과, 통화 불일치, 가격·예산·수동 사용량의 유효성 검사를 검증했습니다.

이 슬라이스는 기존 `LlmResponse.usage` 계약을 비용 관찰의 최소 단위로 확장합니다. `CostBudget`은 기록 또는 보수적으로 추정한 사용량을 검사하는 로컬 도구이며 제공자 청구 한도·결제를 차단하지 않습니다. 다음 CLI 챗봇 장은 이 호출·오류·사용량 계약을 대화 이력과 안전한 콘솔 입출력으로 연결합니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run python examples/volume01/usage_and_cost.py
입력 토큰: 1200
출력 토큰: 300
입력 비용: 0.003 USD
출력 비용: 0.003 USD
총 추정 비용: 0.006 USD

$ uv run python -m compileall -q examples/volume01/usage_and_cost.py
(exit 0)

$ uv run pytest tests/unit/test_usage.py -q
.............                                                            [100%]
13 passed in 0.16s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 6 source files

$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-8.4.2, pluggy-1.6.0
rootdir: E:\python\ai-platform-engineering-book
configfile: pyproject.toml
testpaths: tests
collected 47 items

tests\unit\test_llm_client.py ................................           [ 68%]
tests\unit\test_settings.py ..                                           [ 72%]
tests\unit\test_usage.py .............                                   [100%]

============================= 47 passed in 0.22s ==============================

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
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 실제 외부 LLM API 호출·배포·데이터 전송은 수행하지 않았습니다. 비용 예제와 단위 테스트는 고정된 로컬 데이터만 사용합니다.

## 알려진 차단 사항

- 없음. 실제 제공자 가격은 변동될 수 있으므로 학습자가 라이브 호출을 선택할 경우 제공자 공식 가격표와 청구서를 확인해야 합니다.

## 다음 작업

- Volume 01의 `10-cli-chatbot.md`, 안전한 대화 이력·종료 명령·오류 안내를 갖춘 `chat_cli.py`, 네트워크 없는 Mock 단위 테스트를 한 슬라이스로 구현합니다.
