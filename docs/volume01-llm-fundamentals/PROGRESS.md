# Volume 01 제작 진행 기록

## 현재 상태

- 마지막 완료 슬라이스: 06장 `System Prompt와 생성 파라미터`의 14개 장 구조를 계약 테스트로 고정했다. System/User 메시지 책임, Temperature·Top-p·최대 출력 토큰·Stop Sequence, Mock 기반 직렬화와 선택적 라이브 호출의 비용·외부 전송 경계를 검수한다.
- 회귀 계약: `GenerationParameters`가 문자열·NaN·무한대·소수 토큰 상한을 `LlmConfigurationError`로 거부하도록 입력 검증을 강화했다. `tests/unit/test_llm_client.py`가 이 런타임 경계를 검사하고, `tests/integration/test_volume01_completion_contract.py`가 06장의 필수 섹션, 핵심 개념, 오프라인 pytest, 명시적 비용 경고 및 07장 연결을 검사한다.
- 검증 근거: `uv run ruff check .` 통과, `uv run mypy src` 통과(7 source files), `uv run pytest -q` 통과(72 passed). `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py`도 모두 통과했다. 모든 명령은 프로젝트 `.venv`를 사용했으며, Hermes 활성 가상환경과 다르다는 `uv` 경고만 출력되었다.
- 다음 작은 슬라이스: 07장 `Streaming`의 delta·종료 이유·선택적 사용량·Mock SSE 경계를 계약 테스트로 고정하고, 스트림 이벤트의 입력 검증이 부족하면 단위 테스트와 함께 최소 보완한다.

## 완료 선언 정책

모든 PRD 필수 내용·실습·결과물의 Definition of Done과 권 단위 검증이 통과하기 전에는 `VOLUME01_COMPLETE=true`를 기록하지 않는다. 라이브 API 호출·실제 키·회사 데이터는 완료 검증에 사용하지 않는다.
