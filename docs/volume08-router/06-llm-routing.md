# LLM Router: 고정 classifier response와 정책 경계

## 1. 학습 목표

이 장에서는 실제 LLM, API, 네트워크를 호출하지 않습니다. 대신 사전 검토한 요청 ID별 `LLMClassifierResponseFixture`로 `LLMRouter`의 intent 분류 계약을 재현 가능하게 검증합니다. 분류된 intent는 반드시 기존 `PolicyRouter`로 전달되어 capability·허용 대상·비용·지연 시간·상태 제약을 다시 통과해야 합니다.

## 2. 고정 response fixture 계약

실제 LLM 출력은 model version, prompt, sampling parameter, provider 상태에 따라 달라질 수 있습니다. 학습과 단위 테스트는 다음 최소 계약을 먼저 고정합니다.

- `LLMRoute`: intent 하나와 해당 intent가 요구하는 capability
- `LLMClassifierResponseFixture`: 요청 ID 하나, 검토된 intent 하나, `Decimal` 0~1 confidence 하나
- `minimum_confidence`: route 성공에 필요한 명시적 threshold

```python
LLMClassifierResponseFixture(
    request_id="lesson-08-llm-001",
    intent="order_tracking",
    confidence=Decimal("0.92"),
)
```

fixture에는 prompt, 요청 원문, raw model response, provider 식별자, API 키를 넣지 않습니다. Router는 요청 `text`를 LLM에 전송하지 않고 `request_id`로 fixture만 조회합니다. fixture request ID는 중복될 수 없고, intent는 반드시 configured `LLMRoute` 중 하나여야 합니다.

## 3. threshold와 안전 실패

`LLMRouter`는 fixture confidence가 `minimum_confidence` 이상일 때만 fixture intent를 선택합니다. 단일 fixture가 하나의 검토된 label을 나타내므로 선언 순서나 런타임 sampling에 따른 동점 해소가 없습니다.

| 조건 | 오류 |
|---|---|
| 요청 ID의 classifier response fixture가 없음 | `NoLLMClassifierResponseFixtureError` |
| fixture confidence가 threshold 미만 | `NoConfidentLLMRouteError` |
| intent는 선택됐지만 policy 후보가 없음 | `NoEligibleRouteError` |

세 오류는 모두 `NoEligibleRouteError` 계열로 처리할 수 있습니다. 상위 호출자는 fixture 누락 또는 낮은 confidence를 일반 Agent 선택, 외부 LLM 재시도, 임의 fallback 성공으로 바꾸지 않아야 합니다.

## 4. PolicyRouter 경계 유지

LLM classifier의 label과 confidence는 intent 후보를 나타낼 뿐 실행 권한은 아닙니다. 선택한 `LLMRoute.required_capabilities`는 원래 `RoutingRequest.requirements.required_capabilities`와 합쳐집니다. 이어서 `PolicyRouter`가 정상 상태, 허용 대상, capability, 비용, 지연 시간을 모두 검사합니다.

따라서 이 구현에서는 다음이 불가능합니다.

- 높은 LLM confidence를 이유로 `permitted_target_names`를 무시하는 것
- intent capability 없이 일반 Agent를 선택하는 것
- 비용·지연 시간 제한을 넘은 대상을 성공으로 기록하는 것
- fixture 누락을 실제 LLM 호출로 숨기는 것

이는 Keyword·Semantic Router와 같은 policy 재검증 경계입니다. classifier 구현이 달라도 실행 대상 결정의 권한·비용 안전성은 policy 계약으로 유지됩니다.

## 5. 고정 fixture 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume08/llm_router.py
uv run pytest tests/unit/test_volume08_llm_router.py -q
```

예제는 `order_tracking`의 0.92 고정 confidence와 0.80 threshold를 사용합니다. 허용 대상도 `offline-order-agent`로 고정합니다. 외부 서비스·환경 변수·API 키·네트워크를 사용하지 않습니다.

정상 실행 출력은 사용자 원문 없이 다음과 같습니다.

```text
{"classifier_name": "offline-llm-intent-router", "confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "70", "intent": "order_tracking", "llm_classifier_confidence": "0.92", "policy_name": "offline-llm-support-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-llm-001", "target_kind": "agent", "target_name": "offline-order-agent"}
```

## 6. 감사 로그

성공한 `LLMRouteDecision.as_log_record()`는 policy 결정 로그에 다음 항목만 추가합니다.

| 필드 | 의미 |
|---|---|
| `classifier_name` | LLM Router 이름 |
| `intent` | 고정 fixture가 선언한 intent |
| `llm_classifier_confidence` | fixture `Decimal` confidence 문자열 |

로그에는 요청 `text`, prompt, raw classifier response, 모델 출력, 인증 값, API 키, 실제 외부 호출 결과를 넣지 않습니다.

## 7. 계약 테스트가 검증하는 내용

`tests/unit/test_volume08_llm_router.py`는 고정 fixture만 사용해 다음을 검증합니다.

- 검토된 fixture label과 policy 대상의 선택
- 각 fixture가 독립적으로 같은 결정 계약을 따르는 동작
- fixture 누락과 threshold 미달의 안전 실패
- LLM route가 policy의 permission·capability 경계를 우회하지 못하는 동작
- JSON 로그의 직렬화 가능성과 사용자 원문 부재
- 범위 밖 confidence, 알려지지 않은 intent, 중복 request ID, `NaN` threshold의 거부

## 8. 완료 체크리스트

- [ ] LLM classifier response가 외부 호출이 아닌 고정 `Decimal` fixture임을 확인했다.
- [ ] `minimum_confidence`를 명시적으로 선언했다.
- [ ] fixture 누락과 threshold 미달을 성공 route로 대체하지 않음을 확인했다.
- [ ] LLM intent가 `PolicyRouter`의 capability·권한·비용·지연 시간 경계를 통과해야 함을 확인했다.
- [ ] 감사 로그에 사용자 원문, prompt, raw output, 비밀값을 넣지 않았다.
- [ ] `uv run pytest tests/unit/test_volume08_llm_router.py -q`를 외부 호출 없이 실행했다.

## 9. 핵심 정리

LLM routing의 첫 번째 실습은 provider 호출이 아니라 고정 classifier 계약입니다. 검토된 response fixture, 명시적 confidence threshold, fail-closed 오류, policy 재검증을 먼저 만들면 실제 모델 연동을 나중에 검토하더라도 권한·비용·지연 시간 경계와 privacy 로그를 독립적으로 회귀 테스트할 수 있습니다.
