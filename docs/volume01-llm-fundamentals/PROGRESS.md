# Volume 01 제작 진행 기록

## 현재 상태

- 마지막 완료 슬라이스: 07장 `Streaming`의 14개 장 구조를 계약 테스트로 고정했다. delta 결합, `finish reason`, 선택적 사용량, `StreamChunk`, `Mock StreamTransport`·`RecordingStreamTransport`의 오프라인 SSE 경계와 08장 오류 처리 연결을 검수한다.
- 회귀 계약: 스트림 사용량은 생략 또는 `null`일 수 있지만, 제공된 값이 JSON 객체가 아니면 `LlmResponseError`로 거부한다. `tests/unit/test_llm_client.py`가 이 입력 경계와 delta·종료 이유·최종 사용량·제공자 오류를 Mock으로 검사하고, `tests/integration/test_volume01_completion_contract.py`가 07장의 필수 섹션, 핵심 개념, 오프라인 pytest, 명시적 비용 경고 및 08장 연결을 검사한다.
- 검증 근거: `uv run pytest tests/unit/test_llm_client.py tests/integration/test_volume01_completion_contract.py -q` 통과(48 passed). `uv run ruff check .` 통과, `uv run mypy src` 통과(7 source files), `uv run pytest -q` 통과(74 passed). `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py`도 모두 통과했다. 모든 명령은 프로젝트 `.venv`를 사용했으며, Hermes 활성 가상환경과 다르다는 `uv` 경고만 출력되었다.
- 다음 작은 슬라이스: 08장 `오류 처리와 제한된 재시도`의 시간 초과·네트워크·원격 오류 분류, 명시적 재시도 한도와 지수 백오프, Mock 오류 경계를 계약 테스트로 고정하고, 재시도 설정의 입력 검증이 부족하면 단위 테스트와 함께 최소 보완한다.

## 완료 선언 정책

모든 PRD 필수 내용·실습·결과물의 Definition of Done과 권 단위 검증이 통과하기 전에는 `VOLUME01_COMPLETE=true`를 기록하지 않는다. 라이브 API 호출·실제 키·회사 데이터는 완료 검증에 사용하지 않는다.
