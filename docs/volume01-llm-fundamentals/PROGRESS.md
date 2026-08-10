# Volume 01 제작 진행 기록

## 현재 상태

- 마지막 완료 슬라이스: 05장 `안전한 최초 호출`을 초보자용 14개 장 구조로 보완했다. `LlmSettings`·`LlmClient`·교체 가능한 transport의 책임, Client 생성과 `complete()`의 명시적 전송 시점, `.env`의 명시적 `uv run --env-file` 주입, Mock 기반 요청·응답·오류 검증, 선택적 라이브 호출의 비용·외부 전송 경계를 문서화했다.
- 회귀 계약: `tests/unit/test_llm_client.py`에 Client 생성은 전송하지 않고 `complete()`가 한 번의 transport 호출을 만드는지 검사하는 테스트를 추가했다. `tests/integration/test_volume01_completion_contract.py`에 05장의 14개 섹션, Mock transport, 오프라인 pytest 명령, 명시적 라이브 명령, API 키·네트워크 없는 기본 검증 및 다음 장 연결을 검사하는 계약을 추가했다.
- 검증 근거: `uv run ruff check .` 통과, `uv run mypy src` 통과(7 source files), `uv run pytest -q` 통과(65 passed). `validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py`도 모두 통과했다. 모든 명령은 프로젝트 `.venv`를 사용했으며, Hermes 활성 가상환경과 다르다는 `uv` 경고만 출력되었다.
- 다음 작은 슬라이스: 06장 `System Prompt와 생성 파라미터`를 동일한 장 구조로 보완하고, System/User 메시지 책임·Temperature·Top-p·최대 출력 토큰·Stop Sequence의 Mock 직렬화와 입력 범위 검증을 초보자 실습 및 계약 테스트에 연결한다.

## 완료 선언 정책

모든 PRD 필수 내용·실습·결과물의 Definition of Done과 권 단위 검증이 통과하기 전에는 `VOLUME01_COMPLETE=true`를 기록하지 않는다. 라이브 API 호출·실제 키·회사 데이터는 완료 검증에 사용하지 않는다.
