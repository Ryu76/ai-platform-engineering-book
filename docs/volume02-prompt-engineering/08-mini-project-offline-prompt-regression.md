# 08. 미니 프로젝트: 오프라인 Prompt 회귀 검토

## 1. 학습 목표

이 미니 프로젝트에서는 고객 문의 분류 Prompt의 `v1`, `v2`를 같은 검토 데이터셋으로 비교하고, JSON 계약과 기대 분류가 모두 통과한 버전만 **사람 검토용 release candidate**로 표시합니다.

- Prompt 본문, 고정 테스트 데이터, 기록된 응답을 분리한다.
- 모든 케이스가 통과하지 않으면 후보로 표시하지 않는다.
- 실패한 케이스는 안정적인 ID만 보고한다.
- API 키, 모델, 네트워크, Tool, 실제 고객 데이터를 사용하지 않는다.

## 2. 왜 필요한가

Prompt를 수정한 뒤 일부 예시만 눈으로 확인하면 형식 회귀나 `unknown` 처리 오류를 놓칠 수 있습니다. 같은 테스트 데이터와 기대값을 모든 버전에 적용하면, 변경한 Prompt가 기존 계약을 깨뜨렸는지 반복해서 확인할 수 있습니다.

`release_candidate=True`는 이 작은 고정 데이터셋을 통과했다는 뜻일 뿐입니다. 모델 품질·보안·배포 승인을 대신하지 않습니다. 실제 배포에는 더 넓은 비식별화 데이터, 사람 검토, 권한 통제, 운영 평가가 필요합니다.

## 3. 핵심 개념

| 구성 | 책임 | 이 프로젝트의 처리 |
|---|---|---|
| `PromptTestDataset` | 사람이 승인한 입력·기대값·태그 보관 | `v1`, `v2`에 같은 순서로 제공 |
| `VersionedPrompt` | 변경 사유와 Prompt 계약 보관 | 버전 ID와 렌더링 경계 유지 |
| `RecordedClassification` | 검토할 고정 후보 응답 | 모델 호출 결과라고 주장하지 않음 |
| `PromptRegressionReport` | 비교 요약과 실패 ID 제공 | 원문 입력·응답을 보고서에 보관하지 않음 |

## 4. 동작 구조

```text
검토된 PromptTestDataset
           │ 같은 case_id·기대값
           ├───────────────┐
           ▼               ▼
    VersionedPrompt v1  VersionedPrompt v2
           │               │
   고정 RecordedClassification 기록
           │               │
           ▼               ▼
  JSON 스키마 + 기대값 비교 ───────► PromptRegressionReport
                                      │
                     모든 케이스 통과? ├─ 예: 사람 release review 후보
                                      └─ 아니오: failed_case_ids 검토
```

`evaluate_prompt_records()`는 입력·응답 매핑이 하나라도 누락되거나 중복되면 실패 닫힘으로 예외를 발생시킵니다. JSON이 잘못된 경우에는 자동 보정하지 않고 해당 케이스를 실패로 집계합니다.

## 5. 실습 환경

- 코드: `src/ai_platform/prompts/prompt_mini_project.py`
- 데모: `examples/volume02/prompt_mini_project_demo.py`
- 테스트: `tests/unit/test_prompts.py`

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
uv sync --all-groups
uv run python examples/volume02/prompt_mini_project_demo.py
uv run pytest tests/unit/test_prompts.py -q
```

첫 명령은 의존성을 준비합니다. 둘째 명령은 고정 교육용 문자열을 비교할 뿐 API 키를 읽거나 외부 시스템에 연결하지 않습니다. 셋째 명령은 성공·실패·잘못된 입력 경계를 확인합니다.

## 6. 단계별 실습

### 6.1 같은 데이터셋으로 두 버전을 평가하기

```python
from ai_platform.prompts import RecordedClassification, evaluate_prompt_records

report = evaluate_prompt_records(
    dataset=dataset,
    prompt=version_two,
    recorded_outputs=(
        RecordedClassification(
            "billing-receipt",
            '{"category": "billing", "reason": "영수증 재발급"}',
        ),
        # dataset의 모든 case_id에 정확히 하나의 기록이 필요하다.
    ),
)
```

실제 데모는 세 `case_id` 모두에 기록을 제공합니다. `dataset`이나 Prompt가 잘못된 타입이면, 또는 case ID 매핑이 하나라도 맞지 않으면 결과를 일부만 계산하지 않고 `PromptVersionError`로 중단합니다.

### 6.2 실패를 원문 없이 검토하기

```python
comparison = report.comparison
print(comparison.schema_valid_count, comparison.total_cases)
print(report.failed_case_ids)
print(report.is_release_candidate)
```

보고서는 `dataset_name`, 집계 비교, 실패 ID만 보관합니다. 원문 사용자 입력과 후보 응답은 출력하지 않으므로, 운영 로그에 개인정보나 비밀값을 불필요하게 복사하는 설계를 피할 수 있습니다.

## 7. 코드 설명

`PromptRegressionReport.failed_case_ids`는 JSON 스키마가 틀렸거나 기대 분류와 다른 case ID를 데이터셋 순서대로 반환합니다. `is_release_candidate`는 그 tuple이 비었을 때만 `True`입니다.

`evaluate_prompt_records()`는 06장의 `compare_recorded_classifications()`를 재사용합니다. 따라서 JSON 스키마 검사와 case ID의 일대일 대응 규칙이 버전 비교와 미니 프로젝트에서 달라지지 않습니다. 이 함수는 모델 클라이언트를 만들지 않으며, 네트워크 호출·파일 기록·자동 배포를 수행하지 않습니다.

## 8. 정상 실행 결과

```text
[OFFLINE PROMPT REGRESSION — no model or network was used]
v1: dataset=customer-support-v1, schema=2/3, category_match=1/3, release_candidate=False
  review_case_ids=technical-reset,unknown-ambiguous
v2: dataset=customer-support-v1, schema=3/3, category_match=3/3, release_candidate=True
```

`v1`은 한 JSON 형식 오류와 한 기대값 불일치 때문에 후보가 아닙니다. `v2`가 후보로 표시되어도 사람이 Prompt 변경 사유, 테스트 데이터 범위, 안전성, 운영 요구사항을 검토한 뒤에만 다음 단계를 결정합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `dataset must be a PromptTestDataset instance` | 임의 tuple이나 list를 전달했다. | 승인된 `PromptTestDataset` 객체를 생성해 전달한다. |
| `recorded_outputs must contain exactly one response for every case` | 결과가 누락되었거나 알 수 없는 ID가 있다. | 데이터셋의 모든 `case_id`에 정확히 하나의 기록을 연결한다. |
| `release_candidate=False` | JSON 형식 또는 기대 분류가 하나 이상 실패했다. | `failed_case_ids`를 검토하고 Prompt·기록·기대값 중 무엇을 변경할지 사람이 결정한다. |
| `release_candidate=True`인데 운영 문제가 발생했다 | 이 미니 프로젝트의 데이터 범위가 작다. | 운영 배포를 자동화하지 말고 보안·권한·더 넓은 평가·사람 승인을 추가한다. |

## 10. 응용 실습

1. **기본:** `edge-case` 태그를 가진 케이스를 하나 추가하고 두 버전의 실패 ID가 어떻게 바뀌는지 확인합니다.
2. **응용:** `v3`에 변경 사유를 기록하고, JSON은 유효하지만 기대 분류가 다른 고정 기록을 하나 만듭니다.
3. **심화:** 테스트 데이터 승인자, 변경 검토자, 결과 보존 기간, 접근 권한을 포함한 운영 평가 절차를 설계합니다. 실제 고객 원문이나 API 키는 과제 산출물에 넣지 않습니다.

## 11. 실무 적용

실제 서비스에서는 Prompt 버전, 데이터셋 버전, 모델 설정, 실행 시각, 익명화 정책을 별도 변경 관리합니다. 결과 보고서에는 필요한 최소 지표와 case ID만 남기고, 원문 접근은 승인된 담당자에게 제한합니다. Prompt의 `release_candidate`는 CI의 자동 배포 조건이 아니라, 사람이 검토할 입력 중 하나로 취급합니다.

> [!WARNING]
> Prompt Injection 방어, 출력 스키마, Tool allowlist, 사용자 권한, 데이터 보존 정책은 서로 대체할 수 없습니다. 이 미니 프로젝트는 오프라인 Prompt 회귀 검토만 다루며, Tool이나 외부 API를 호출하지 않습니다.

## 12. 과제

- **기본:** `schema_valid_count`와 `category_match_count`가 각각 무엇을 의미하는지 설명합니다.
- **응용:** 오류 원문을 로그에 저장하지 않으면서 디버깅 가능한 최소 메타데이터를 설계합니다.
- **심화:** release candidate가 아닌 버전을 실수로 배포하지 않도록 변경 승인·CI 상태·롤백 책임을 분리해 작성합니다.

## 13. 완료 체크리스트

- [ ] 같은 `PromptTestDataset`을 두 버전에 적용했다.
- [ ] 각 case ID에 정확히 하나의 고정 응답 기록을 연결했다.
- [ ] JSON 실패와 기대 분류 실패를 자동 보정하지 않았다.
- [ ] 실패 ID만으로 검토 대상을 식별할 수 있음을 확인했다.
- [ ] `release_candidate`가 자동 배포 승인이 아님을 설명할 수 있다.
- [ ] 데모와 단위 테스트를 API 키·네트워크·실제 고객 데이터 없이 실행했다.

## 14. 핵심 정리

Prompt 변경은 고정 테스트 데이터와 비교해야 회귀를 확인할 수 있습니다. 이 미니 프로젝트는 하나의 Prompt 버전과 한 세트의 기록을 안전하게 비교하고, 모든 계약을 통과한 경우에만 사람 검토 후보로 표시합니다. 다음 슬라이스에서는 Volume 02의 과제와 학습자 체크리스트, 다음 Volume 인계 목록을 정리합니다.
