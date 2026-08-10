# Volume 02 제작 진행 기록

## 현재 상태

- 상태: 진행 중
- 작업 브랜치: `volume-02`
- 안전 경계: 모든 현재 예제와 테스트는 API 키·네트워크·라이브 LLM 호출 없이 실행한다.
- 완료 선언: 아직 불가. `VOLUME02_COMPLETE=true`는 모든 PRD Definition of Done 근거가 확보된 뒤에만 추가한다.

## 완료한 슬라이스

| 슬라이스 | 문서·코드·테스트 | 검증 상태 |
|---|---|---|
| 01. Prompt 구성 요소와 첫 템플릿 | `01-prompt-components.md`, `src/ai_platform/prompts/prompt_templates.py`, `examples/volume02/prompt_template_demo.py`, `tests/unit/test_prompts.py` | 2026-08-10 전체 검사 및 70개 테스트 통과 |
| 02. Zero-shot·One-shot·Few-shot | `02-zero-one-few-shot.md`, `src/ai_platform/prompts/shot_prompts.py`, `examples/volume02/shot_prompt_demo.py`, `tests/unit/test_prompts.py` | 2026-08-10 전체 검사와 오프라인 데모 통과 |
| 03. 역할 Prompt와 구조화된 JSON 출력 | `03-role-structured-output.md`, `src/ai_platform/prompts/structured_output.py`, `examples/volume02/structured_output_demo.py`, `tests/unit/test_prompts.py` | 2026-08-10 오프라인 데모, 단위·전체 검사 통과 |
| 04. ReAct와 내부 추론 비노출 공개 결과 | `04-react-without-cot-exposure.md`, `src/ai_platform/prompts/structured_reasoning.py`, `examples/volume02/structured_reasoning_demo.py`, `tests/unit/test_prompts.py` | 2026-08-10 오프라인 데모, 단위·전체 검사 통과 |
| 05. Prompt Injection 방어와 입력 검증 | `05-prompt-injection-input-validation.md`, `src/ai_platform/prompts/injection_defense.py`, `examples/volume02/injection_defense_demo.py`, `tests/unit/test_prompts.py` | 2026-08-10 오프라인 데모, 신뢰 경계·위험 신호·실패 닫힘 입력 검사, 단위·전체 검사 통과 |

## 남은 PRD 요구사항

- Prompt Versioning, Template, 버전별 결과 비교
- Prompt 테스트 데이터, 미니 프로젝트, 과제, 권 단위 학습자 체크리스트
- 전체 Volume 재실행, 문서·링크·비밀값 검증, 다음 Volume 인계 목록

## 검증 기록

| 날짜 | 범위 | 결과 |
|---|---|---|
| 2026-08-10 | `bash scripts/run_all_tests.sh` | Ruff 통과, mypy(9개 소스) 통과, 문서·링크·코드 블록·비밀값 검사 통과, pytest 70 passed |
| 2026-08-10 | `uv run python examples/volume02/prompt_template_demo.py` | 네트워크·API 키 없이 Prompt 다섯 섹션을 렌더링함 |
| 2026-08-10 | `uv run ruff check src/ai_platform/prompts examples/volume02/shot_prompt_demo.py tests/unit/test_prompts.py` | 통과 |
| 2026-08-10 | `uv run mypy src/ai_platform/prompts` | 3개 소스, 오류 없음 |
| 2026-08-10 | `uv run pytest tests/unit/test_prompts.py -q` | 17 passed |
| 2026-08-10 | `uv run python examples/volume02/shot_prompt_demo.py` | zero-shot·one-shot·few-shot Prompt를 외부 호출 없이 렌더링함 |
| 2026-08-10 | `bash scripts/run_all_tests.sh` | Ruff 통과, mypy(10개 소스) 통과, 문서·링크·코드 블록·비밀값 검사 통과, pytest 78 passed |
| 2026-08-10 | `uv run python examples/volume02/structured_reasoning_demo.py` | ReAct 작업 절차·공개 JSON 계약과 고정 검증 샘플을 네트워크·API 키·Tool 실행 없이 출력함 |
| 2026-08-10 | `bash scripts/run_all_tests.sh` | Ruff 통과, mypy(12개 소스) 통과, 문서·링크·코드 블록·비밀값 검사 통과, pytest 92 passed |
| 2026-08-10 | `uv run python examples/volume02/injection_defense_demo.py` | 고정된 Injection 유사 입력을 `high` 신호로 평가하고 신뢰 경계 뒤에 렌더링함. 네트워크·API 키·LLM·Tool 호출 없음 |
| 2026-08-10 | `uv run ruff check src/ai_platform/prompts examples/volume02/injection_defense_demo.py tests/unit/test_prompts.py` / `uv run mypy src/ai_platform/prompts` / `uv run pytest tests/unit/test_prompts.py -q` | Ruff 통과, mypy(6개 소스) 통과, Prompt 단위 테스트 38 passed |
| 2026-08-10 | `bash scripts/run_all_tests.sh` | Ruff 통과, mypy(13개 소스) 통과, 문서·링크·코드 블록·비밀값 검사 통과, pytest 99 passed |
