# 09. 권 단위 과제: 오프라인 Prompt 계약 검토

## 1. 학습 목표

이 과제는 앞선 장의 Prompt 구성, 예시, 구조화 출력, 입력 경계, 버전 비교를 하나의 검토 흐름으로 연결합니다. 완료한 학습자는 다음을 수행할 수 있어야 합니다.

- 목적·문맥·입력 데이터·출력 형식·제약을 분리한 Prompt를 작성한다.
- 검토된 예시와 신뢰되지 않은 새 입력을 구분한다.
- JSON 출력 계약과 Prompt Injection 대응을 별도로 검증한다.
- 동일한 고정 테스트 데이터로 Prompt 버전을 비교하고, 실패를 자동 보정하지 않는다.

## 2. 왜 필요한가

장별 예제만 통과했다고 서비스 Prompt의 변경이 안전하다고 판단할 수는 없습니다. 형식 계약, 기대 분류, 입력 신뢰 경계는 함께 유지되어야 합니다. 이 과제는 API 키나 모델 호출 없이 그 연결을 직접 점검하게 합니다.

과제의 고정 문자열은 교육용입니다. 실제 고객 원문, 회사 문서, 인증 정보, 모델 응답 기록을 복사해 넣지 않습니다.

## 3. 핵심 개념

| 검토 대상 | 확인할 계약 | 실패 시 처리 |
|---|---|---|
| Prompt 본문 | 소유 지시·출력 형식·제약이 입력보다 앞선다. | Prompt를 수정하고 다시 렌더링한다. |
| Few-shot 예시 | 예시 수와 순서가 mode 계약과 일치한다. | 검토된 예시만 교체하고 근거를 기록한다. |
| 사용자 입력 | 신뢰되지 않은 데이터로 표시하고 검증한다. | 거부하거나 사람 검토 대상으로 분리한다. |
| JSON 응답 | 허용 필드·분류·비어 있지 않은 사유를 만족한다. | 자동 보정하지 않고 실패로 기록한다. |
| 버전 비교 | 동일한 case ID·기대값으로 모든 버전을 비교한다. | 실패 ID를 검토하고 후보로 배포하지 않는다. |

## 4. 동작 구조

```text
서비스 소유 Prompt 계약
        + 검토된 demonstration
        + 고정 PromptTestDataset
                 │
                 ▼
        오프라인 렌더링·검증
                 │
                 ├── 입력 경계 또는 JSON 계약 실패 ──► 수정·재검토
                 │
                 └── 모든 고정 case 통과 ──► 사람 검토 후보
```

이 흐름의 `사람 검토 후보`는 자동 배포 승인이 아닙니다. 외부 Tool 호출, 권한 부여, 데이터 전송은 이 과제 범위에 없습니다.

## 5. 실습 환경

- 저장소 경로: `docs/volume02-prompt-engineering/`, `examples/volume02/`, `src/ai_platform/prompts/`
- 실행 환경: WSL Ubuntu, Linux 또는 Git Bash의 저장소 루트
- 필요 도구: Anaconda Distribution, Python 3.12 이상

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
conda env update --file environment.yml --prune
```

이 명령은 잠긴 개발 의존성을 준비합니다. API 키를 설정하거나 외부 LLM 계정을 만들 필요가 없습니다.

## 6. 단계별 실습

### 6.1 기본: 구성 요소와 JSON 계약을 점검하기

`examples/volume02/prompt_template_demo.py`와 `examples/volume02/structured_output_demo.py`를 실행합니다. 출력에서 `INSTRUCTION`, `CONTEXT`, `OUTPUT FORMAT`, `CONSTRAINTS`, `UNTRUSTED USER INPUT`의 순서와 유효·무효 JSON 판정을 확인합니다.

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
python examples/volume02/prompt_template_demo.py
python examples/volume02/structured_output_demo.py
pytest tests/unit/test_prompts.py -q
```

첫 두 명령은 고정 문자열을 렌더링하거나 검증합니다. 마지막 명령은 정상 입력과 실패 입력을 함께 검사합니다.

### 6.2 응용: 안전한 few-shot 분류 Prompt를 설계하기

1. `examples/volume02/shot_prompt_demo.py`의 검토 예시를 하나 선택합니다.
2. 새 교육용 입력 하나와 기대 JSON 분류 하나를 작성합니다. 실제 사용자 입력은 사용하지 않습니다.
3. `ShotMode.FEW`의 예시 개수와 순서를 유지합니다.
4. 새 입력을 `<user_input>` 경계 안에 렌더링했는지 확인합니다.
5. `validate_classification_json()`이 기대 JSON을 수용하고, 허용되지 않은 분류를 거부하는지 단위 테스트로 확인합니다.

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
python examples/volume02/shot_prompt_demo.py
pytest tests/unit/test_prompts.py -q
```

예시 입력은 서비스 소유자가 검토한 demonstration이고, 새 입력은 신뢰되지 않은 데이터입니다. 두 영역을 섞어 Prompt 정책을 바꾸지 않습니다.

### 6.3 심화: Prompt Injection과 회귀를 함께 검토하기

1. `examples/volume02/injection_defense_demo.py`에서 위험 신호와 입력 경계를 확인합니다.
2. `examples/volume02/prompt_mini_project_demo.py`에서 `v1`의 실패 ID와 `v2`의 후보 상태를 확인합니다.
3. `v2`와 같은 fixture에 JSON은 유효하지만 기대 분류가 다른 고정 기록을 하나 추가합니다.
4. `failed_case_ids`에 해당 ID가 포함되고 `is_release_candidate`가 `False`가 되는지 확인합니다.
5. Prompt·fixture·기대값 중 무엇을 왜 바꿀지, 사람이 검토할 변경 기록을 작성합니다.

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
python examples/volume02/injection_defense_demo.py
python examples/volume02/prompt_mini_project_demo.py
pytest tests/unit/test_prompts.py -q
```

모든 명령은 네트워크, API 키, 라이브 모델, Tool 실행을 사용하지 않습니다. 위험 신호 평가는 차단 또는 검토 우선순위를 정하는 보조 수단이며, 권한 통제를 대체하지 않습니다.

## 7. 코드 설명

`PromptSections.render()`는 서비스 소유 Prompt 섹션을 먼저 만들고 새 입력을 `UNTRUSTED USER INPUT` 경계에 넣습니다. `ShotPrompt`는 zero-shot·one-shot·few-shot의 예시 개수 계약을 검사합니다.

`validate_classification_json()`은 문자열을 추측해 고치지 않고 JSON 스키마를 검사합니다. `validate_untrusted_input()`과 `assess_injection_risk()`는 입력 유효성 및 명시적 위험 신호를 별도로 다룹니다.

`evaluate_prompt_records()`는 `PromptTestDataset`의 모든 case ID에 정확히 하나의 `RecordedClassification`을 요구합니다. `PromptRegressionReport`는 원문 대신 집계와 실패 ID만 제공하므로, 검토 로그에 불필요한 사용자 데이터를 넣지 않습니다.

## 8. 정상 실행 결과

정상적인 미니 프로젝트 실행은 다음과 같이 두 버전의 집계만 표시합니다.

```text
[OFFLINE PROMPT REGRESSION — no model or network was used]
v1: dataset=customer-support-v1, schema=2/3, category_match=1/3, release_candidate=False
  review_case_ids=technical-reset,unknown-ambiguous
v2: dataset=customer-support-v1, schema=3/3, category_match=3/3, release_candidate=True
```

심화 과제에서 의도적으로 기대 분류 불일치를 추가했다면, 해당 case ID가 `review_case_ids`에 나타나고 후보 상태는 `False`여야 합니다. 이 결과는 고정 교육용 기록의 계약 검토 결과일 뿐 모델 품질이나 운영 승인 결과가 아닙니다.

## 9. 오류 해결

| 증상 | 확인할 원인 | 해결 |
|---|---|---|
| `few-shot Prompt requires at least two examples` | 예시가 하나뿐이거나 mode가 맞지 않는다. | 검토된 예시를 두 개 이상 제공하거나 one-shot으로 바꾼다. |
| JSON 스키마 테스트 실패 | 필드 추가, 빈 `reason`, 허용되지 않은 `category`가 있다. | 출력 계약에 맞게 고정 문자열을 수정하고 자동 보정은 하지 않는다. |
| `InputValidationError` | 빈 입력, 4,000자 초과, NUL 문자가 있다. | 입력을 거부하고 신뢰 경계 밖의 원본을 Prompt 정책으로 취급하지 않는다. |
| `recorded_outputs must contain exactly one response` | case ID가 누락·중복되었거나 알 수 없는 ID가 있다. | fixture의 모든 ID에 정확히 한 개의 기록을 연결한다. |
| `release_candidate=True`를 배포 승인으로 해석했다 | 고정 데이터셋 범위가 제한적이다. | 변경 사유, 데이터 범위, 보안, 권한을 사람이 별도로 검토한다. |

## 10. 응용 실습

- 분류 계약에 `shipping`을 추가한다고 가정하고, Prompt 제약·JSON 허용값·테스트 fixture·기대값을 모두 변경해야 하는 이유를 표로 작성합니다.
- `unknown` 사례와 Injection 유사 입력의 차이를 설명하고, 각각 거부·검토·분류 중 어떤 후속 처리가 필요한지 설계합니다.
- 실패 ID만 공유되는 검토 보고서에서 원문을 볼 수 있는 담당자, 보존 기간, 삭제 책임을 정합니다.

## 11. 실무 적용

실서비스에서는 Prompt 본문, 테스트 데이터셋, 모델 설정, 실행 환경을 별도로 버전 관리합니다. 고정 테스트가 통과해도 새로운 데이터 분포, 권한 경계, 출력 소비자, 비용·지연 시간, 사람 검토 절차를 추가로 확인해야 합니다.

> [!WARNING]
> Prompt에 “JSON만 반환”이라고 적는 것만으로 구조화 출력 안전성이 보장되지는 않습니다. 소비 직전 스키마 검증, 입력 검증, 권한 통제, Tool allowlist를 함께 적용해야 합니다.

## 12. 과제 제출물

- **기본:** 다섯 Prompt 구성 요소를 포함한 교육용 분류 Prompt와 유효·무효 JSON 예시를 제출합니다.
- **응용:** two-shot 이상의 검토 예시, 새 교육용 입력, 기대 분류, 입력 신뢰 경계를 포함한 설계 메모를 제출합니다.
- **심화:** 동일 fixture에서 비교한 두 Prompt 버전, 실패 ID, 변경 사유, 사람이 검토할 배포 판단 기준을 제출합니다.

제출물에는 API 키, `.env` 파일, 실제 사용자·회사 데이터, Chain of Thought, 자동 배포 명령을 넣지 않습니다.

## 13. 완료 체크리스트

- [ ] 기본 과제에서 다섯 Prompt 구성 요소를 분리했다.
- [ ] one-shot 또는 few-shot 예시를 신뢰되지 않은 새 입력과 구분했다.
- [ ] JSON 출력의 성공·실패 사례를 스키마로 확인했다.
- [ ] 입력 검증과 Injection 위험 신호를 별도로 확인했다.
- [ ] 같은 테스트 fixture로 두 Prompt 버전을 비교했다.
- [ ] 실패한 JSON 또는 분류를 자동 보정하지 않았다.
- [ ] 모든 명령을 실제 API·키·네트워크·Tool 실행 없이 수행했다.
- [ ] `release_candidate`가 자동 배포 승인이 아님을 설명할 수 있다.

## 14. 핵심 정리

Prompt Engineering은 문장을 길게 쓰는 작업이 아니라, 소유 지시·문맥·입력 데이터·출력 계약·제약을 분리하고 반복 검토하는 작업입니다. 오프라인 fixture와 명시적 실패 처리를 사용하면 Prompt 변경의 회귀를 더 안전하게 검토할 수 있습니다. 다음 슬라이스에서는 이 권 전체를 다시 실행하기 위한 학습자 체크리스트와 Volume 03 인계 목록을 정리합니다.
