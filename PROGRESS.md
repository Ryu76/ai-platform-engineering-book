# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 세 번째 장 `03-theory.md`를 PRD Chapter Definition of Done의 14개 장 섹션을 갖춘 독립 장으로 보완하고, 모델 토크나이저를 대체하지 않는 오프라인 컨텍스트 예산 검증 코드와 계약 테스트를 추가했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 `04-environment-setup.md`를 포함한 나머지 장의 장별 출고 감사와 전체 실습 재실행 근거가 필요합니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/03-theory.md`
  - AI·머신러닝·딥러닝·생성형 AI·LLM의 포함 관계, Transformer·Attention 개요, Token·Tokenizer·입출력 토큰·Context Window, 환각·최신성의 한계를 한국어로 설명했습니다.
  - PRD의 14개 장 섹션, ASCII 구조도, 실행 위치가 표시된 오프라인 실습, 코드 설명, 정상 결과, 오류 해결, 응용 실습, 과제, 체크리스트, 다음 장 연결을 보완했습니다.
  - 실제 토큰 수는 선택한 모델의 토크나이저 또는 제공자 사용량으로 확인해야 하며, 글자 수 추정으로 안전하다고 판단하면 안 된다는 경계를 명시했습니다.
- `src/ai_platform/llm/context.py`
  - `ContextBudget`, `ContextAssessment`, `ContextBudgetError`를 추가했습니다.
  - 확인한 입력 토큰과 예약 출력 토큰을 합산해 컨텍스트 한도 적합 여부와 남은 예산을 결정론적으로 계산하며, 초과 계획은 라이브 호출 전에 차단합니다.
  - 텍스트 토큰화를 구현하지 않아 모델별 토크나이저를 거짓으로 대체하지 않습니다.
- `src/ai_platform/llm/__init__.py`
  - 컨텍스트 예산 API를 학습 예제에서 안전하게 가져올 수 있도록 내보냈습니다.
- `examples/volume01/token_budget.py`
  - API 키·네트워크·외부 전송 없이 정상 요청과 컨텍스트 초과 요청의 예산을 실제 실행 가능한 코드로 비교합니다.
- `tests/unit/test_context.py`
  - 남은 예산 계산, 초과 판정, 전송 전 차단, 잘못된 윈도우·예약량·입력값 거부를 테스트했습니다.
- `tests/integration/test_volume01_completion_contract.py`
  - 세 번째 장의 14개 필수 섹션, 실행 예제·단위 테스트, 오프라인 경계, 다음 장 링크, 산출물 파일을 고정하는 계약 테스트를 추가했습니다.
- `docs/glossary.md`
  - Transformer, Attention, Context Budget 용어를 추가했습니다.

이번 변경은 문서와 오프라인 검증만 다룹니다. 실제 LLM API 호출·외부 데이터 전송·비용·배포는 수행하지 않았습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run python examples/volume01/token_budget.py
요약 요청: 입력=1500, 출력 예약=400, 계획 합계=1900, 남은 예산=148, 판정=가능
긴 검색 문맥 요청: 입력=1800, 출력 예약=400, 계획 합계=2200, 남은 예산=-152, 판정=초과

$ uv run pytest tests/unit/test_context.py tests/integration/test_volume01_completion_contract.py -q
..............                                                           [100%]
14 passed in 0.17s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 8 source files

$ uv run pytest -q
........................................................................ [100%]
72 passed in 0.78s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0; Git의 LF→CRLF 작업 트리 경고만 출력)
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 실제 외부 LLM API 호출·배포·데이터 전송은 수행하지 않았습니다.

## 알려진 차단 사항

- Volume 01을 완료로 선언할 수 없습니다. 첫 번째부터 세 번째 장만 PRD의 14개 Chapter Definition of Done 섹션과 문서 계약 테스트로 보완했습니다. `04-environment-setup.md`를 포함한 나머지 장의 장별 출고 감사와 보완 근거가 아직 없습니다.
- 라이브 모드는 입력을 선택한 제공자에 전송하고 비용이 발생할 수 있으므로, 학습·CI 검증에는 `--offline-demo`, 컨텍스트 예산 코드, Mock/통합 테스트를 사용합니다.

## 다음 작업

- Volume 01의 네 번째 장 `04-environment-setup.md`를 PRD Chapter Definition of Done에 맞는 독립 장으로 보완하고, 해당 장의 문서 계약 테스트와 오프라인 검증을 추가합니다.
