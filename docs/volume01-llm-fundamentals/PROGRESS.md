# Volume 01 제작 진행 기록

## 현재 상태

- 마지막 완료 슬라이스: 09장 `토큰 사용량과 비용 추정`의 14개 장 구조와 오프라인 예산 경계를 계약 테스트로 고정했다. 입력·출력 토큰 분리, 사람이 확인한 고정 가격표, `Decimal` 비용 계산, 사용량 미수신, 제공자 청구 한도와 로컬 검사 차이, 10장 CLI 연결을 검수한다.
- 회귀 계약: `ModelPricing`과 `CostBudget`은 유한한 0 이상 `Decimal` 및 세 글자 대문자 통화를 요구한다. `CostEstimate`도 수동 생성 시 각 비용·통화를 검증하고 `총액 = 입력 비용 + 출력 비용`을 강제해 잘못된 값으로 예산 검사를 우회하지 못하게 한다. `estimate_cost()`는 외부 가격·환율 조회 없이 입력·출력 비용을 결정론적으로 계산하며, 같은 통화에서만 `CostBudget` 상한과 비교한다. `tests/unit/test_usage.py`가 계산식·예산·통화·수동 추정값을, `tests/integration/test_volume01_completion_contract.py`가 09장의 필수 섹션·오프라인 명령·비용 경고·10장 연결을 검사한다.
- 검증 근거: `uv run pytest tests/unit/test_usage.py tests/integration/test_volume01_completion_contract.py -q` 통과(28 passed), `uv run pytest -q` 통과(82 passed), `uv run ruff check .` 통과, `uv run mypy src` 통과(7 source files)했다. `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py`도 모두 통과했고, `uv run python examples/volume01/usage_and_cost.py`는 입력 1200·출력 300 토큰의 총 추정 비용 `0.006 USD`를 출력했다. 모든 검증은 실제 키·라이브 API 호출 없이 프로젝트 `.venv`에서 실행했다. Hermes 활성 가상환경과 다르다는 `uv` 경고만 출력된다.
- 다음 작은 슬라이스: 10장 `안전한 CLI 챗봇`의 오프라인 기본 흐름, `/exit`·빈 입력·이력 한도·오류 비노출 경계와 별도 프로세스 실행을 계약 테스트로 고정하고, CLI 테스트에 빠진 안전 경계가 있으면 최소 보완한다.

## 완료 선언 정책

모든 PRD 필수 내용·실습·결과물의 Definition of Done과 권 단위 검증이 통과하기 전에는 `VOLUME01_COMPLETE=true`를 기록하지 않는다. 라이브 API 호출·실제 키·회사 데이터는 완료 검증에 사용하지 않는다.
