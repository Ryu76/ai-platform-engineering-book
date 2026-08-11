# Volume 02 학습자·제작 검수 체크리스트

## 1. 목적

이 체크리스트는 Volume 02를 학습한 뒤 Volume 03으로 넘어가기 전에 사용합니다. 학습자는 명령을 실제로 실행하고 결과를 확인한 뒤에만 체크 표시를 합니다. 파일과 테스트가 존재한다는 사실은 Prompt 계약을 이해하거나 운영 배포를 승인했다는 뜻이 아닙니다.

## 2. 권의 연결 구조

```text
서비스 소유 Prompt 구성 요소
           + 검토된 demonstration
           + 신뢰되지 않은 사용자 입력
                         │
                         ▼
       JSON 스키마·입력 경계·Injection 신호 검사
                         │
                         ▼
      고정 fixture의 버전별 오프라인 회귀 검토
                         │
                         ▼
 Volume 03 Tool Calling의 인수 검증·권한·allowlist 경계
```

Volume 02는 모델 호출 결과를 흉내 내는 고정 교육용 문자열만 다룹니다. 다음 권에서 Tool Calling을 추가하더라도 Prompt 텍스트나 위험 신호가 권한, 파일 경로, 네트워크 전송을 직접 결정하게 해서는 안 됩니다.

## 3. 학습자 완료 체크리스트

### 3.1 Prompt 설계와 구조화 출력

- [ ] Instruction, Context, Input Data, Output Format, Constraint의 책임을 구분할 수 있다.
- [ ] zero-shot, one-shot, few-shot의 예시 수와 예시 순서가 계약이라는 점을 설명할 수 있다.
- [ ] 역할 Prompt는 서비스 책임을 설명하지만 사용자 입력의 권한을 높이지 않는다는 점을 설명할 수 있다.
- [ ] JSON 출력은 Prompt 문구만이 아니라 소비 직전 스키마 검증이 필요함을 설명할 수 있다.
- [ ] 내부 Chain of Thought를 요구하거나 저장하지 않고 공개 결과·근거 요약 계약을 설계할 수 있다.

### 3.2 안전 경계와 변경 검토

- [ ] 새 사용자 입력과 외부 문서를 신뢰되지 않은 데이터 경계 안에 넣었다.
- [ ] 빈 값, 과도하게 긴 값, NUL 문자가 포함된 입력을 거부하는 이유를 설명할 수 있다.
- [ ] Prompt Injection 위험 신호 평가는 보조 신호이며 권한 통제를 대체하지 않는다는 점을 설명할 수 있다.
- [ ] Prompt 버전, 변경 사유, 고정 테스트 fixture, 기대값을 분리해 관리할 수 있다.
- [ ] JSON 실패 또는 기대 분류 실패를 자동 보정하지 않고 안정적인 case ID로 검토할 수 있다.
- [ ] `release_candidate=True`가 자동 배포 승인이 아님을 설명할 수 있다.

### 3.3 오프라인 실행과 검증

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
uv sync --all-groups
uv run python examples/volume02/prompt_template_demo.py
uv run python examples/volume02/structured_output_demo.py
uv run python examples/volume02/injection_defense_demo.py
uv run python examples/volume02/prompt_mini_project_demo.py
uv run pytest tests/unit/test_prompts.py tests/integration/test_volume02_exercises.py -q
bash scripts/run_all_tests.sh
```

- [ ] 위 데모가 API 키, 네트워크, 라이브 LLM, Tool 실행 없이 실행됨을 확인했다.
- [ ] 단위 테스트가 정상·실패 입력, JSON 계약, 버전 비교의 실패 닫힘 경계를 확인함을 설명할 수 있다.
- [ ] 전체 검사 결과에서 Ruff, mypy, 문서·링크·코드 블록·비밀값 검사, pytest가 통과했음을 확인했다.
- [ ] 과제와 테스트 fixture에 실제 사용자·회사 데이터, API 키, `.env`, 내부 추론을 넣지 않았다.

## 4. 제작 검수 근거

다음 항목은 제작자가 저장소에서 확인할 수 있는 결과물 경계입니다. 학습자의 체크 표시를 대신하지 않습니다.

- [x] [Volume 목차](README.md)가 01~09장, 이 체크리스트, 제작 진행 기록을 연결한다.
- [x] `src/ai_platform/prompts/`에 템플릿, few-shot, 구조화 출력, 구조적 추론, 입력 방어, 버전 비교, 고정 fixture, 회귀 보고서 코드가 있다.
- [x] `examples/volume02/`에 외부 API를 호출하지 않는 각 장의 데모가 있다.
- [x] `tests/unit/test_prompts.py`와 `tests/integration/test_volume02_exercises.py`가 정상·실패 계약을 검사한다.
- [x] 각 장과 권 단위 Definition of Done의 최종 재실행 결과는 별도 출고 감사에서 확인했다. 실행 근거는 [PROGRESS.md](PROGRESS.md)에 기록한다.

> [!WARNING]
> 이 체크리스트의 제작 검수 항목만으로 Volume 02 완료나 운영 배포를 선언하지 않습니다. `release_candidate`는 작은 고정 교육용 fixture를 모두 통과한 사람 검토 후보 표식일 뿐이며, Tool 실행·권한 부여·데이터 전송의 승인이 아닙니다.

## 5. Volume 03으로의 인계

[Volume 03. Tool Calling & MCP](../volume03-tool-calling-mcp/README.md)에서는 Volume 02의 Prompt 경계를 유지한 채 Tool 정의, JSON Schema 인수, allowlist, Timeout, Retry, 권한 통제, 승인 흐름을 추가합니다.

인계할 재사용 가능 경계는 다음과 같습니다.

- `PromptSections`와 `ShotPrompt`: 서비스 소유 지시·검토 예시를 신뢰되지 않은 새 입력보다 앞에 고정한다.
- `validate_classification_json()`과 `validate_reasoning_json()`: 허용 필드만 받으며 실패한 문자열을 추측해 고치지 않는다.
- `validate_untrusted_input()`과 `InjectionResistantPrompt`: 입력 형식과 Prompt 신뢰 경계를 구분한다. 위험 신호는 Tool 권한 정책이 아니다.
- `PromptTestDataset`, `VersionedPrompt`, `evaluate_prompt_records()`: 고정 fixture·변경 사유·실패 ID로 변경을 검토하며 원문을 보고서에 복사하지 않는다.

Volume 03의 Tool 인수는 별도의 스키마 검증과 allowlist를 통과해야 합니다. 신뢰되지 않은 Prompt 입력, 모델 출력, `release_candidate` 상태를 Tool 선택, 경로 선택, 네트워크 접근, 권한 상승의 근거로 사용하지 않습니다.

## 6. 관련 문서

- [Volume 02 목차](README.md)
- [Prompt 구성 요소](01-prompt-components.md)
- [구조화된 JSON 출력](03-role-structured-output.md)
- [Prompt Injection 방어](05-prompt-injection-input-validation.md)
- [Prompt 테스트 데이터](07-prompt-test-data.md)
- [오프라인 Prompt 회귀 미니 프로젝트](08-mini-project-offline-prompt-regression.md)
- [권 단위 과제](09-exercises.md)
- [제작 진행 기록](PROGRESS.md)
- [Volume 03 시작](../volume03-tool-calling-mcp/README.md)
