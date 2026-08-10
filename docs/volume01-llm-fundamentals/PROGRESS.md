# Volume 01 제작 진행 기록

## 현재 상태

- 마지막 완료 슬라이스: 08장 `오류 처리와 제한된 재시도`의 14개 장 구조를 계약 테스트로 고정했다. 시간 초과·네트워크·원격 오류 분류, `RetryPolicy`의 명시적 시도 한도와 지수 백오프, `ScriptedTransport` Mock 경계 및 09장 사용량·비용 연결을 검수한다.
- 회귀 계약: `RetryPolicy`는 1~5회의 유한한 시도와 유한한 0 이상 기본 대기만 허용한다. `complete()`는 429·5xx, 네트워크·시간 초과만 재시도하고 400대 오류와 응답 형식 오류를 즉시 전달한다. `stream()`은 재시도 정책이 명시되어도 제공자 오류 뒤 한 번만 호출되어 부분 출력 중복을 막는다. `tests/unit/test_llm_client.py`가 이 Mock 경계와 재시도 횟수·대기 시간을 검사하고, `tests/integration/test_volume01_completion_contract.py`가 08장의 필수 섹션, 핵심 개념, 오프라인 pytest, 비용 경고 및 09장 연결을 검사한다.
- 검증 근거: `uv run pytest tests/unit/test_llm_client.py tests/integration/test_volume01_completion_contract.py -q` 통과(50 passed). `uv run ruff check .` 통과, `uv run mypy src` 통과(7 source files), `uv run pytest -q` 통과(76 passed). `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py`도 모두 통과했다. 모든 검증은 실제 키·라이브 API 호출 없이 프로젝트 `.venv`에서 실행한다. Hermes 활성 가상환경과 다르다는 `uv` 경고만 출력된다.
- 다음 작은 슬라이스: 09장 `토큰 사용량과 비용 추정`의 입력·출력 토큰 분리, 명시적 가격표, `Decimal` 기반 비용 추정, 예산 상한과 외부 가격 조회 금지 경계를 계약 테스트로 고정하고, 비용 자료형의 입력 검증이 부족하면 단위 테스트와 함께 최소 보완한다.

## 완료 선언 정책

모든 PRD 필수 내용·실습·결과물의 Definition of Done과 권 단위 검증이 통과하기 전에는 `VOLUME01_COMPLETE=true`를 기록하지 않는다. 라이브 API 호출·실제 키·회사 데이터는 완료 검증에 사용하지 않는다.
