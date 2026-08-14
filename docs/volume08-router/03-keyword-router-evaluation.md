# Keyword Router 평가: 고정 dataset과 accuracy gate

## 1. 학습 목표

이 장에서는 외부 LLM·임베딩·API 호출 없이 고정 평가 dataset으로 `KeywordRouter`의 route 정확도와 안전 실패를 함께 측정합니다. 각 사례는 예상 intent·대상 또는 예상 안전 실패를 명시합니다. 평가 보고서에는 사례 ID와 집계만 남기고 사용자 원문은 남기지 않습니다.

## 2. 왜 route 성공만 세면 안 되는가

Router는 일치하지 않는 요청을 임의의 Agent로 보내면 안 됩니다. 이 Volume에서 다음 두 결과는 의도된 **안전 실패**입니다.

- `NO_CONFIDENT_KEYWORD_ROUTE`: keyword가 없거나 confidence threshold를 통과하지 못했습니다.
- `NO_ELIGIBLE_POLICY_ROUTE`: keyword intent는 선택됐지만 PolicyRouter의 capability·허용 대상·비용·지연 시간·상태 경계를 통과할 대상이 없습니다.

따라서 routing accuracy는 route 사례의 intent와 target이 모두 맞는지, 안전 실패 사례가 기대한 실패 유형으로 끝나는지를 함께 계산합니다. 단순 intent 일치만으로 권한 경계를 우회한 대상 선택을 성공으로 세지 않습니다.

## 3. 평가 계약

`KeywordRoutingEvaluationCase`는 추적용 `case_id`, 실행용 `RoutingRequest`, 기대 결과인 `KeywordRoutingExpectation`으로 구성됩니다.

```python
KeywordRoutingEvaluationCase(
    case_id="order-route",
    request=RoutingRequest(request_id="evaluation-001", text="ORDER tracking please"),
    expected=KeywordRoutingExpectation(
        outcome=KeywordRoutingOutcome.ROUTE,
        intent="order_tracking",
        target_name="order-support-agent",
    ),
)
```

성공(`ROUTE`) 기대값은 intent와 target 이름을 반드시 함께 선언합니다. 안전 실패 기대값은 intent와 target을 선언할 수 없습니다. 빈 dataset, 중복 사례 ID, 범위를 벗어난 accuracy threshold, 모호한 기대값은 `RoutingConfigurationError`로 거부합니다.

평가 함수는 다음과 같이 고정 tuple만 받습니다.

```python
report = evaluate_keyword_router(router, dataset)
report.require_minimum_accuracy(Decimal("1"))
```

`require_minimum_accuracy()`는 기준 미달이면 `RoutingQualityGateError`를 발생시킵니다. 기준을 숨긴 채 측정값만 출력하지 않도록 하는 로컬 품질 gate입니다. 이 예제의 dataset은 의도적으로 완전 일치하므로 `1`을 기준으로 씁니다. 운영 환경에서는 별도 검토를 거친 고정 dataset과 명시적 버전 기준을 사용해야 합니다.

## 4. 고정 fixture 실행

```bash
# 실행 위치: 저장소 루트
python examples/volume08/keyword_router_evaluation.py
pytest tests/unit/test_volume08_router_evaluation.py -q
```

예제에는 정상 `order_tracking`·`refund_request` route, keyword가 없는 요청의 confidence 안전 실패, 권한 제약으로 대상이 없는 policy 안전 실패가 각각 하나씩 있습니다. 외부 서비스·환경 변수·API 키·네트워크를 사용하지 않습니다.

정상 실행 시 원문 없이 다음과 같은 JSON 요약 한 줄을 출력합니다.

```text
{"accuracy": "1", "correct_cases": 4, "correct_safe_failures": 2, "mismatched_case_ids": [], "total_cases": 4}
```

## 5. 보고서 해석

`KeywordRoutingEvaluationReport`는 다음을 보관합니다.

| 필드 | 의미 |
|---|---|
| `total_cases` | 고정 dataset 전체 사례 수 |
| `correct_cases` | 예상 route 또는 예상 안전 실패와 정확히 일치한 수 |
| `accuracy` | `correct_cases / total_cases`를 `Decimal`로 계산한 값 |
| `correct_safe_failures` | 정확히 기대한 안전 실패 수 |
| `mismatched_case_ids` | 원문이 아닌, 회귀 분석용 불일치 사례 ID |

`as_log_record()`는 이 다섯 항목만 JSON 직렬화 가능한 값으로 반환합니다. 사용자 `text`, 인증 값, API 키, 대상의 실행 결과는 보고서에 포함하지 않습니다.

## 6. 계약 테스트가 검증하는 내용

`tests/unit/test_volume08_router_evaluation.py`는 고정 fixture만 사용해 다음을 검증합니다.

- 정상 route의 intent와 target을 동시에 비교하는 정확도 계산
- threshold 미달과 PolicyRouter 거부를 서로 다른 안전 실패로 측정하는 동작
- 불일치 사례 ID와 명시적 accuracy gate의 실패
- JSON 평가 로그에 사용자 원문이 없는지 확인
- 빈·중복 dataset, 모호한 기대값, 범위를 벗어난 threshold의 거부

## 7. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `keyword routing accuracy ... is below required minimum ...` | fixture 결과가 기대값과 다르거나 기준이 더 높습니다. | `mismatched_case_ids`로 고정 사례를 확인하고 rule·정책·기대 결과 중 의도한 변경만 함께 검토합니다. 기준을 임의로 낮추지 마세요. |
| `safe-failure expectations must not declare an intent or target name` | 실패 사례에 성공 route의 기대값을 혼합했습니다. | 실패 유형만 명시하고 intent·target은 제거합니다. |
| `keyword routing evaluation dataset must not be empty` | 의미 있는 accuracy 분모가 없습니다. | 정상 route와 안전 실패를 포함한 고정 사례를 추가합니다. |
| 대상 route는 맞는데 accuracy가 낮음 | intent 또는 target 중 하나가 기대값과 다를 수 있습니다. | target 이름까지 비교합니다. capability·권한 경계를 우회한 선택을 성공으로 처리하지 마세요. |

## 8. 완료 체크리스트

- [ ] route 성공과 안전 실패를 같은 고정 dataset에서 평가할 수 있다.
- [ ] accuracy가 intent와 target을 함께 비교한다는 점을 설명할 수 있다.
- [ ] `NO_CONFIDENT_KEYWORD_ROUTE`와 `NO_ELIGIBLE_POLICY_ROUTE`의 차이를 설명할 수 있다.
- [ ] 명시적 `Decimal` accuracy gate가 기준 미달을 막는 것을 확인했다.
- [ ] 평가 로그에 사용자 원문과 비밀값을 넣지 않았다.
- [ ] `pytest tests/unit/test_volume08_router_evaluation.py -q`를 외부 호출 없이 실행했다.

## 9. 핵심 정리

평가는 자연어 분류의 성공률만 세는 과정이 아닙니다. 고정 사례에 대해 intent·target 선택과 fail-closed 결과를 함께 계약으로 만들면, keyword rule 또는 정책 변경이 권한 경계와 안전 실패에 미치는 영향을 재현 가능하게 검출할 수 있습니다. Semantic·LLM Router를 추가하더라도 같은 원칙으로 별도 고정 fixture와 평가 계약을 먼저 만들어야 합니다.
