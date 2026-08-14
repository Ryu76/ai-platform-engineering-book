# Volume 01 제작 진행 기록

## 현재 상태

- `VOLUME01_COMPLETE=true`
- 마지막 갱신: 2026-08-11T01:43:10+09:00
- 작업 브랜치: `volume-01`
- 이전 완료 슬라이스: 09장 `토큰 사용량과 비용 추정`의 14개 장 구조와 오프라인 예산 경계를 계약 테스트로 고정했다. 입력·출력 토큰 분리, 사람이 확인한 고정 가격표, `Decimal` 비용 계산, 사용량 미수신, 제공자 청구 한도와 로컬 검사 차이, 10장 CLI 연결을 검수한다.
- 이전 회귀 계약: `ModelPricing`과 `CostBudget`은 유한한 0 이상 `Decimal` 및 세 글자 대문자 통화를 요구한다. `CostEstimate`도 수동 생성 시 각 비용·통화를 검증하고 `총액 = 입력 비용 + 출력 비용`을 강제해 잘못된 값으로 예산 검사를 우회하지 못하게 한다. `estimate_cost()`는 외부 가격·환율 조회 없이 입력·출력 비용을 결정론적으로 계산하며, 같은 통화에서만 `CostBudget` 상한과 비교한다. `tests/unit/test_usage.py`가 계산식·예산·통화·수동 추정값을, `tests/integration/test_volume01_completion_contract.py`가 09장의 필수 섹션·오프라인 명령·비용 경고·10장 연결을 검사한다.
- 이전 검증 근거: `uv run pytest tests/unit/test_usage.py tests/integration/test_volume01_completion_contract.py -q` 통과(28 passed), `uv run pytest -q` 통과(82 passed), `uv run ruff check .` 통과, `uv run mypy src` 통과(7 source files)했다. `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py`도 모두 통과했고, `uv run python examples/volume01/usage_and_cost.py`는 입력 1200·출력 300 토큰의 총 추정 비용 `0.006 USD`를 출력했다. 모든 검증은 실제 키·라이브 API 호출 없이 프로젝트 `.venv`에서 실행했다. Hermes 활성 가상환경과 다르다는 `uv` 경고만 출력된다.

## 완료 선언 정책

모든 PRD 필수 내용·실습·결과물의 Definition of Done과 권 단위 검증이 통과하기 전에는 `VOLUME01_COMPLETE=true`를 기록하지 않는다. 라이브 API 호출·실제 키·회사 데이터는 완료 검증에 사용하지 않는다.

## 이번 슬라이스: 오프라인 CLI `/help` 통합 계약

- `tests/integration/test_volume01_chat_cli.py`에 별도 Python 프로세스에서 공백·대소문자가 섞인 `/HELP`와 `/quit`을 처리하는 계약을 추가했다.
- 이 경로는 도움말·종료 문구는 출력하지만 `오프라인 데모 응답`은 출력하지 않는다. 따라서 CLI 입구에서 두 명령이 질문으로 처리되지 않는 회귀를 잡는다.
- `12-exercises.md`의 기본 과제를 실제 구현된 `/help`·`/quit` 경계 확인으로 갱신했고, 더 이상 구현 전 과제로 안내하지 않는다.

## 이번 슬라이스 검증 결과

```text
uv run ruff check .
All checks passed!

uv run mypy src
Success: no issues found in 7 source files

uv run pytest tests/unit/test_chat.py tests/integration/test_volume01_chat_cli.py tests/integration/test_volume01_completion_contract.py -q
23 passed in 1.14s

uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개
uv run python scripts/validate_links.py
링크 검증 통과
uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과
uv run python scripts/check_secrets.py
비밀값 검사 통과

printf '/help\n/quit\n' | uv run python examples/volume01/chat_cli.py --offline-demo
AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.
사용자> 도움말: 질문을 입력하면 선택한 LLM에 전송될 수 있습니다. 종료하려면 /exit 또는 /quit을 입력하세요.
사용자> 대화를 마칩니다.
```

## 완료 감사 슬라이스: PRD 범위·Hallucination·오프라인 결과물 계약

- `03-theory.md`에 Hallucination(환각), 학습 지식과 실시간 정보의 차이, 최신 상태·숫자·정책·권한에 대한 외부 근거·검증 코드·사람 검토 경계를 명시했다.
- `tests/integration/test_volume01_prd_contract.py`가 13개 학습 문서의 14단계 학습 구조와 Volume 01 PRD의 필수 개념, 실습 경로, 결과물(`.env.example`, Client, CLI, Mock/통합 테스트)을 오프라인 검증 가능하게 고정한다.
- PRD Volume 01의 필수 내용·실습·결과물을 문서·예제·테스트와 대조했다. 선택 라이브 실습은 외부 전송·비용을 명시적으로 경고하고, 완료 검증은 실제 키·라이브 API 없이 실행했다.
- Hermes cron 목록에서 이 작업의 ID가 `f9dcb63c71e4` (`ai-book-volume-01-author`)임을 확인하고, `cron pause f9dcb63c71e4`로 일정을 중지했다. 후속 목록에서 이 ID는 활성 작업 목록에 더 이상 나타나지 않았다.

## 완료 검증 결과

```text
uv run pytest tests/integration/test_volume01_prd_contract.py tests/integration/test_volume01_completion_contract.py tests/integration/test_volume01_chat_cli.py tests/integration/test_volume01_exercises.py -q
15 passed in 0.96s

bash scripts/run_all_tests.sh
All checks passed!
Success: no issues found in 7 source files
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
88 passed in 1.17s
```

모든 검증은 프로젝트 `.venv`에서 실행했으며 실제 키·라이브 API·외부 서비스 호출을 사용하지 않았다. Hermes 활성 가상환경과 프로젝트 `.venv`의 경로가 다르다는 `uv` 경고만 있었고, 모든 명령은 종료 코드 0으로 완료됐다.

## 재검증 슬라이스: 완료 상태 및 일정 중지

- 마지막 갱신: 2026-08-13T15:26:54+09:00
- 현재 `volume-01` 브랜치에서 Volume 01의 PRD 계약, 문서, 오프라인 예제 및 전체 테스트를 다시 검수했다. 이미 선언된 `VOLUME01_COMPLETE=true`는 유지한다.
- Hermes 세션 환경의 ID는 `cron_f47b02d46ebb_20260813_145827`였다. Hermes CLI가 셸 PATH에 없어서 설치 경로의 프로젝트 가상환경 Python으로 CLI를 실행했다.
- `hermes cron list`는 활성 일정이 없다고 보고했다. 일정 저장소를 대조해 세션 ID의 작업 `f47b02d46ebb`를 식별했으며, `hermes cron pause f47b02d46ebb`는 `Paused job: ai-book-volume-08-author (f47b02d46ebb)`를 반환했다. 재확인한 `cron list`와 `cron status`도 활성 작업이 없음을 보고했으므로, 이 실행의 일정은 중지된 상태다.

## 재검증 결과

```text
bash scripts/run_all_tests.sh
All checks passed!
Success: no issues found in 7 source files
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
88 passed in 2.28s

/c/Users/HODI/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe \
  /c/Users/HODI/AppData/Local/hermes/hermes-agent/hermes cron list
No scheduled jobs.

/c/Users/HODI/AppData/Local/hermes/hermes-agent/.venv/Scripts/python.exe \
  /c/Users/HODI/AppData/Local/hermes/hermes-agent/hermes cron pause f47b02d46ebb
Paused job: ai-book-volume-08-author (f47b02d46ebb)
```

검증 중 실제 키·라이브 API·외부 서비스 호출은 사용하지 않았다. `uv`가 Hermes 활성 가상환경과 프로젝트 `.venv` 경로 차이를 경고했지만, 모든 품질 검사와 pytest는 종료 코드 0으로 완료됐다.

## 재검증 슬라이스: Volume 01 완료 상태 확인 및 실제 일정 식별

- 마지막 갱신: 2026-08-14T11:40:08+09:00
- `VOLUME01_COMPLETE=true`를 유지한다. PRD Volume 01의 필수 개념, 10개 실습, Client·CLI·`.env.example`·Mock/통합 테스트 결과물은 권 전용 계약 테스트와 오프라인 CLI 실행으로 재확인했다.
- Hermes cron 목록에서 현재 작업 디렉터리 `E:\python\ai-platform-engineering-book-volume-01` 및 작업명 `ai-book-volume-01-author`를 기준으로 이 작업을 `f9dcb63c71e4`로 식별했다. 이전 기록의 Volume 08 작업 ID와 혼동하지 않는다.

## 재검증 결과

```text
uv run pytest tests/unit/test_llm_client.py tests/unit/test_chat.py tests/unit/test_usage.py tests/integration/test_volume01_prd_contract.py tests/integration/test_volume01_completion_contract.py tests/integration/test_volume01_chat_cli.py tests/integration/test_volume01_exercises.py tests/integration/test_volume01_summary.py -q
86 passed in 1.48s

uv run ruff check .
All checks passed!
uv run mypy src
Success: no issues found in 7 source files

uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개
uv run python scripts/validate_links.py
링크 검증 통과
uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과
uv run python scripts/check_secrets.py
비밀값 검사 통과

printf '/help\\n/quit\\n' | uv run python examples/volume01/chat_cli.py --offline-demo
AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.
사용자> 도움말: 질문을 입력하면 선택한 LLM에 전송될 수 있습니다. 종료하려면 /exit 또는 /quit을 입력하세요.
사용자> 대화를 마칩니다.
```

모든 명령은 종료 코드 0으로 완료됐으며 실제 키·라이브 API·외부 서비스 호출을 사용하지 않았다. `uv`는 Hermes 활성 가상환경과 프로젝트 `.venv` 경로 차이에 대한 경고만 출력했다.

## 일정 중지 확인

- `hermes cron pause f9dcb63c71e4`가 `Paused job: ai-book-volume-01-author (f9dcb63c71e4)`를 반환했다.
- 후속 `hermes cron list` 및 `hermes cron status`는 Volume 01 작업을 활성 목록에 표시하지 않았고, 활성 작업 수는 8개에서 7개가 됐다.
