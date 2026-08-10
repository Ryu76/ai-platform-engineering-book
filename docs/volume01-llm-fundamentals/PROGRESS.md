# Volume 01 제작 진행 기록

## 현재 상태

- 마지막 완료 슬라이스: 04장 `환경 설정`을 초보자용 14개 장 구조로 확장했다. Windows Git Bash(`/e/...`)·WSL(`/mnt/e/...`) 경로 경계, `uv sync`와 Python 3.12 확인, `.env.example`/로컬 `.env` 분리, `uv run --env-file`의 명시적 주입, 키 없는 오프라인 CLI·Mock 검증과 라이브 전송 선택 경계를 문서화했다.
- 회귀 계약: `tests/integration/test_volume01_completion_contract.py`에 04장의 14개 섹션, Windows/WSL 경로, `.env` 자동 파싱 부재, `uv`·오프라인 검증 명령, 다음 장 연결을 검사하는 테스트를 추가했다.
- 검증 근거: `uv run ruff check src/ai_platform/llm tests/unit/test_settings.py tests/unit/test_llm_client.py tests/unit/test_chat.py tests/integration/test_volume01_completion_contract.py tests/integration/test_volume01_chat_cli.py` 통과, `uv run mypy src/ai_platform/llm` 통과(4 source files), 관련 pytest 48개 통과. `validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py`도 통과했다.
- 다음 작은 슬라이스: 05장 `안전한 최초 호출`을 동일한 장 구조로 보완하고, `LlmClient`의 명시적 전송·Mock transport·비밀값 없는 설정 오류를 초보자 실습과 계약 테스트에 연결한다.

## 완료 선언 정책

모든 PRD 필수 내용·실습·결과물의 Definition of Done과 권 단위 검증이 통과하기 전에는 `VOLUME01_COMPLETE=true`를 기록하지 않는다. 라이브 API 호출·실제 키·회사 데이터는 완료 검증에 사용하지 않는다.
