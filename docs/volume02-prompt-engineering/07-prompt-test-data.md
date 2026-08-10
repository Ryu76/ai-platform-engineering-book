# 07a. Prompt 테스트 데이터

## 이 슬라이스에서 만드는 것

Prompt를 바꾼 뒤에는 **같은 입력과 같은 기대값**으로 다시 확인해야 합니다. 이 슬라이스는 사람이 검토한 고정 fixture를 만들고, 06장의 버전 비교 계약으로 안전하게 변환합니다.

- `src/ai_platform/prompts/prompt_test_data.py`: fixture 데이터 계약과 실패 닫힘 검증
- `examples/volume02/prompt_test_data_demo.py`: 외부 호출 없이 fixture를 출력하는 데모
- `tests/unit/test_prompts.py`: ID·태그·중복·순서·기대값 검증

`PromptTestCase`의 기대 분류는 모델이 생성한 답이 아닙니다. 테스트를 위해 사람이 승인한 기준값입니다. 이 코드는 API 키를 읽지 않고, LLM·Tool·네트워크를 호출하지 않습니다.

## 왜 별도 테스트 데이터가 필요한가

Prompt 본문과 검토 입력을 한 파일에 섞으면, 버전별 결과가 달라졌을 때 Prompt 변경 때문인지 테스트 입력 변경 때문인지 알기 어렵습니다. 테스트 데이터를 분리하면 다음을 반복할 수 있습니다.

1. `case_id`, 사용자 입력, 기대 분류, 검토 목적, 태그를 사람이 검토한다.
2. 모든 Prompt 버전에 동일한 `PromptTestDataset`을 적용한다.
3. 06장의 `compare_recorded_classifications()`에 `comparison_cases()` 결과를 전달한다.
4. JSON 스키마 준수와 기대 분류 일치를 버전별로 비교한다.

교육용 fixture에는 실제 고객 대화, 개인정보, API 키, 비공개 문서를 넣지 않습니다. 실제 운영 로그를 사용할 경우에는 별도 승인·비식별화·접근 통제가 필요합니다.

## 데이터 계약

각 `PromptTestCase`는 다음 필드를 가집니다.

| 필드 | 역할 | 검증 규칙 |
|---|---|---|
| `case_id` | 결과와 연결하는 안정적 식별자 | 소문자로 시작하며 소문자·숫자·하이픈만 허용 |
| `user_input` | 처리 대상인 고정 입력 | 비어 있으면 실패 |
| `expected_category` | 사람이 검토한 기대 분류 | `billing`, `technical`, `unknown`만 허용 |
| `purpose` | 이 사례가 필요한 이유 | 비어 있으면 실패 |
| `tags` | happy-path, edge-case 같은 검토 축 | 비어 있지 않은 문자열 tuple만 허용 |

`PromptTestDataset`은 비어 있지 않은 tuple만 받고, 중복 `case_id`를 거부합니다. 순서는 유지됩니다. 따라서 같은 데이터셋을 여러 버전에 투입해도 비교 기준이 바뀌지 않습니다.

## 실행

저장소 루트의 Git Bash, WSL 또는 Linux 터미널에서 실행합니다.

```bash
uv sync --all-groups
uv run python examples/volume02/prompt_test_data_demo.py
uv run pytest tests/unit/test_prompts.py -q
```

정상 출력에는 세 개의 교육용 fixture와 비교에 전달될 ID가 표시됩니다.

```text
[PROMPT TEST DATA] customer-support-v1
billing-receipt: expected=billing, tags=happy-path,billing, purpose=명확한 청구 문의를 분류한다.
technical-reset: expected=technical, tags=happy-path,technical, purpose=명확한 기술 문의를 분류한다.
unknown-ambiguous: expected=unknown, tags=edge-case,unknown, purpose=근거 없는 추측 대신 unknown을 선택한다.

[COMPARISON CASE IDS]
billing-receipt
technical-reset
unknown-ambiguous
```

이 출력은 fixture를 읽어 보인 것일 뿐 모델 품질 측정 결과가 아닙니다.

## 코드 사용 예

```python
from ai_platform.prompts import PromptTestCase, PromptTestDataset

fixtures = PromptTestDataset(
    name="customer-support-v1",
    cases=(
        PromptTestCase(
            case_id="billing-receipt",
            user_input="영수증을 다시 받고 싶어요.",
            expected_category="billing",
            purpose="명확한 청구 문의를 분류한다.",
            tags=("happy-path", "billing"),
        ),
    ),
)
comparison_cases = fixtures.comparison_cases()
```

태그는 결과를 바꾸지 않고 검토 범위를 선택하는 메타데이터입니다. 예를 들어 `fixtures.cases_with_tag("edge-case")`로 경계 사례를 검토할 수 있습니다. 공백 태그, 잘못된 ID, 중복 ID는 조용히 보정하지 않고 예외로 중단합니다.

## 이 슬라이스 체크리스트

- [ ] 테스트 데이터와 Prompt 본문을 분리했다.
- [ ] 각 fixture에 안정적인 ID, 기대값, 검토 목적, 태그를 기록했다.
- [ ] 같은 fixture를 버전 간 비교에 사용한다.
- [ ] 중복·빈 값·잘못된 식별자를 실패 닫힘으로 처리했다.
- [ ] 실제 고객 데이터·비밀값·라이브 API 호출을 fixture와 데모에 넣지 않았다.

다음 슬라이스에서는 이 fixture를 사용하는 고객 문의 분류 미니 프로젝트와 학습 과제를 추가합니다.
