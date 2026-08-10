# Semantic Router: 고정 score fixture와 정책 경계

## 1. 학습 목표

이 장에서는 실제 embedding 모델, LLM, API, 네트워크를 호출하지 않습니다. 대신 요청 ID별로 사전 계산한 고정 semantic similarity fixture를 사용해 `SemanticRouter`를 재현 가능하게 검증합니다. 선택된 intent는 기존 `PolicyRouter`로 전달되어 capability·허용 대상·비용·지연 시간·상태 제약을 다시 통과해야 합니다.

## 2. 고정 score fixture를 먼저 사용하는 이유

실제 semantic routing은 임베딩 모델 버전, 전처리, 인덱스 상태에 따라 결과가 달라질 수 있습니다. 학습과 단위 테스트에서는 다음 계약을 먼저 고정합니다.

- `SemanticIntentScore`: intent 하나와 `Decimal` 0~1 similarity 하나
- `SemanticScoreFixture`: 요청 ID 하나에 대한 모든 configured intent의 점수
- `minimum_similarity`: route 성공에 필요한 명시적 threshold

fixture는 각 configured intent를 정확히 한 번씩 포함해야 합니다. 누락된 score나 알려지지 않은 intent를 조용히 0점으로 취급하지 않으므로, fixture 변경을 명시적으로 검토할 수 있습니다.

```python
SemanticScoreFixture(
    request_id="lesson-08-semantic-001",
    intent_scores=(
        SemanticIntentScore("order_tracking", Decimal("0.93")),
        SemanticIntentScore("refund_request", Decimal("0.18")),
    ),
)
```

점수는 요청 원문이 아니라 `request_id`로 조회합니다. 이 구현은 semantic score를 계산하지 않으며, 고정된 fixture만 읽습니다.

## 3. 결정론적 선택과 안전 실패

`SemanticRouter`는 threshold 이상인 intent 중 similarity가 가장 높은 것을 선택합니다. 동점은 intent 이름 오름차순으로 해소합니다. 따라서 route 선언·fixture 순서가 달라도 동점 결과가 바뀌지 않습니다.

다음은 성공으로 위장하지 않는 fail-closed 결과입니다.

| 조건 | 오류 |
|---|---|
| 요청 ID의 score fixture가 없음 | `NoSemanticScoreFixtureError` |
| 모든 similarity가 threshold 미만 | `NoConfidentSemanticRouteError` |
| semantic intent는 선택됐지만 policy 후보가 없음 | `NoEligibleRouteError` |

앞의 두 오류도 `NoEligibleRouteError`의 하위 유형입니다. 상위 호출자는 외부 모델로 임의 재시도하거나 일반 Agent로 보내지 않고, 안전 실패를 일관되게 처리할 수 있습니다.

## 4. PolicyRouter 경계 유지

semantic 점수가 높다는 것은 특정 intent 후보가 강하다는 뜻일 뿐, 실행 권한이 있다는 뜻은 아닙니다. 선택한 `SemanticRoute.required_capabilities`는 원래 `RoutingRequest.requirements.required_capabilities`와 합쳐집니다. 이후 `PolicyRouter`가 정상 상태, 허용 대상, capability, 비용, 지연 시간을 모두 검사합니다.

따라서 다음 우회는 불가능합니다.

- score가 높다는 이유로 `permitted_target_names`를 무시하는 것
- semantic route가 요구한 capability 없이 일반 Agent를 선택하는 것
- 비용·지연 시간 제한을 넘는 대상을 성공으로 기록하는 것

## 5. 고정 fixture 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume08/semantic_router.py
uv run pytest tests/unit/test_volume08_semantic_router.py -q
```

예제는 `order_tracking`의 0.93 고정 score와 0.80 threshold를 사용합니다. 허용 대상도 `offline-order-agent`로 고정합니다. 외부 서비스·환경 변수·API 키·네트워크를 사용하지 않습니다.

정상 실행 출력은 사용자 원문 없이 다음과 같습니다.

```text
{"classifier_name": "offline-semantic-intent-router", "confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "70", "intent": "order_tracking", "policy_name": "offline-semantic-support-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-semantic-001", "semantic_similarity": "0.93", "target_kind": "agent", "target_name": "offline-order-agent"}
```

## 6. 감사 로그

성공한 `SemanticRouteDecision.as_log_record()`는 policy 결정 로그에 다음 항목만 추가합니다.

| 필드 | 의미 |
|---|---|
| `classifier_name` | semantic router 이름 |
| `intent` | 고정 score로 선택된 intent |
| `semantic_similarity` | 선택 intent의 `Decimal` score 문자열 |

로그에는 요청 `text`, embedding vector, 인증 값, API 키, 실제 외부 호출 결과를 넣지 않습니다. 점수 fixture의 요청 ID는 이미 기존 policy 로그의 `request_id`로 추적됩니다.

## 7. 계약 테스트가 검증하는 내용

`tests/unit/test_volume08_semantic_router.py`는 고정 fixture만 사용해 다음을 검증합니다.

- 최고 similarity intent와 policy 대상의 선택
- 동일 score에서 intent 이름으로 해소하는 결정론적 동점
- fixture 누락과 threshold 미달의 안전 실패
- semantic route가 policy의 permission·capability 경계를 우회하지 못하는 동작
- JSON 로그의 직렬화 가능성과 사용자 원문 부재
- 범위 밖 score, 불완전 fixture, `NaN` threshold의 거부

## 8. 완료 체크리스트

- [ ] semantic score가 외부 호출이 아닌 고정 `Decimal` fixture임을 확인했다.
- [ ] `minimum_similarity`를 명시적으로 선언했다.
- [ ] fixture 누락과 threshold 미달을 성공 route로 대체하지 않음을 확인했다.
- [ ] semantic intent가 `PolicyRouter`의 capability·권한·비용·지연 시간 경계를 통과해야 함을 확인했다.
- [ ] 감사 로그에 사용자 원문과 비밀값을 넣지 않았다.
- [ ] `uv run pytest tests/unit/test_volume08_semantic_router.py -q`를 외부 호출 없이 실행했다.

## 9. 핵심 정리

semantic routing을 안전하게 도입하는 첫 단계는 실제 모델 호출이 아닙니다. 먼저 완전한 고정 score fixture, 명시적인 threshold, 결정론적 동점 해소, policy 재검증을 계약으로 만들면 모델·임베딩 구현을 나중에 바꾸더라도 권한 경계와 안전 실패를 독립적으로 회귀 테스트할 수 있습니다.
