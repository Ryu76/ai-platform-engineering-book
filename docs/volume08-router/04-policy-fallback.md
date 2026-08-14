# Policy fallback: retry budget 안에서 fail closed 하기

## 1. 학습 목표

이 장에서는 외부 LLM·API·네트워크 호출 없이 고정 `PolicyRouter` fixture를 순서대로 연결해 fallback을 구현합니다. primary 대상이 상태·권한·capability·비용·지연 시간 조건을 만족하지 않을 때만 fallback policy를 시도합니다. fallback은 요청 제약을 변경하지 않으며, 명시한 retry budget을 넘으면 안전하게 실패합니다.

## 2. fallback이 정책 우회가 아니어야 하는 이유

대상이 비정상이거나 선택 불가할 때 다른 대상을 시도하는 것은 유용하지만, 다음과 같이 구현하면 안 됩니다.

- fallback에서 `permitted_target_names`를 제거하는 것
- 비용 또는 지연 시간 제한을 느슨하게 만드는 것
- intent나 요청이 요구한 capability를 생략하는 것
- 후보가 없을 때 임의의 Agent를 성공으로 기록하는 것

`PolicyFallbackRouter`는 **동일한 `RoutingRequest`**를 primary와 모든 fallback `PolicyRouter`에 전달합니다. 각 policy는 기존 `PolicyRouter`의 정상 상태, capability, 허용 대상, 비용, 지연 시간 검사를 다시 수행합니다. 따라서 fallback은 대상 후보를 바꾸지만 정책 경계를 우회하지 않습니다.

## 3. 결정론적 retry 계약

```python
router = PolicyFallbackRouter(
    name="offline-support-fallback-router",
    primary_router=primary_policy,
    fallback_routers=(first_fallback, second_fallback),
    retry_budget=1,
)
```

시도 순서는 primary가 항상 먼저이고 이어서 선언된 fallback 순서입니다. `retry_budget`은 primary 이후 허용할 fallback 시도 횟수입니다.

| `retry_budget` | 최대 시도 policy |
|---:|---|
| `0` | primary만 |
| `1` | primary, 첫 번째 fallback |
| `2` | primary, 첫 번째 fallback, 두 번째 fallback |

예산보다 많은 fallback은 eligible하더라도 시도하지 않습니다. primary와 fallback policy 이름은 감사 로그를 모호하지 않게 하기 위해 서로 달라야 하며, budget은 `bool`이 아닌 0 이상의 `int`여야 합니다.

성공하면 `FallbackRouteDecision`이 최종 `policy_decision`, 실제 `attempted_policy_names`, `fallback_count`를 보관합니다. 모두 실패하거나 budget이 소진되면 `FallbackRouteExhaustedError`가 발생합니다. 이 오류도 `NoEligibleRouteError`의 하위 유형이므로 상위 호출자는 fail-closed 경로로 일관되게 처리할 수 있습니다.

## 4. 고정 fixture 실행

```bash
# 실행 위치: 저장소 루트
python examples/volume08/policy_fallback_router.py
pytest tests/unit/test_volume08_policy_fallback_router.py -q
```

예제는 비정상 primary와 정상 fallback Agent를 사용합니다. 요청의 허용 대상은 fallback Agent 하나로 고정되고 `retry_budget=1`입니다. 외부 서비스·환경 변수·API 키·네트워크를 사용하지 않습니다.

정상 실행 출력은 사용자 원문 없이 다음과 같습니다.

```text
{"attempted_policy_names": ["offline-primary-policy", "offline-fallback-policy"], "confidence": "1", "estimated_cost": "0.002", "estimated_latency_ms": "60", "fallback_count": 1, "fallback_router_name": "offline-support-fallback-router", "policy_name": "offline-fallback-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-fallback-001", "target_kind": "agent", "target_name": "offline-fallback-agent"}
```

## 5. 감사 로그와 안전 실패

성공한 `FallbackRouteDecision.as_log_record()`는 policy 결정의 대상 메타데이터에 다음 항목을 추가합니다.

| 필드 | 의미 |
|---|---|
| `fallback_router_name` | fallback chain 이름 |
| `fallback_count` | primary 뒤에 실제 소비한 fallback 횟수 |
| `attempted_policy_names` | 실제 시도 순서의 policy 이름 |

실패한 `FallbackRouteExhaustedError.as_log_record()`는 `request_id`, `outcome`, `attempted_policy_names`만 반환합니다. 성공·실패 로그 모두 요청 `text`나 비밀값을 넣지 않습니다.

## 6. 계약 테스트가 검증하는 내용

`tests/unit/test_volume08_policy_fallback_router.py`는 고정 fixture만 사용해 다음을 검증합니다.

- primary → 선언된 fallback 순서의 결정론적 시도
- 기존 허용 대상·비용 제한을 fallback이 우회하지 못하는 동작
- `retry_budget=0`일 때 eligible fallback도 시도하지 않는 fail-closed 동작
- 성공과 exhaustion 로그의 JSON 직렬화 가능성 및 사용자 원문 부재
- 음수·불리언 retry budget과 중복 policy 이름의 거부

## 7. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `no eligible route found within the configured fallback retry budget` | 시도한 모든 policy가 요청 제약을 통과하지 못했거나 예산이 소진됐습니다. | `attempted_policy_names`를 확인하고 대상 상태·capability·권한·비용·지연 시간을 검토합니다. 요청 제한을 임의로 제거하지 마세요. |
| fallback이 실행되지 않음 | `retry_budget`이 0이거나 앞선 policy가 이미 성공했습니다. | 허용할 fallback 횟수와 policy 선언 순서를 명시적으로 검토합니다. |
| `primary and fallback policy names must be unique` | 감사 로그에서 시도 policy를 구분할 수 없습니다. | 각 policy에 고유한 이름을 부여합니다. |

## 8. 완료 체크리스트

- [ ] fallback이 같은 `RoutingRequest`를 각 policy에 전달한다는 점을 설명할 수 있다.
- [ ] retry budget이 primary 뒤의 fallback 시도 횟수라는 점을 확인했다.
- [ ] budget 소진 시 임의 대상 선택 대신 `FallbackRouteExhaustedError`로 실패함을 확인했다.
- [ ] 성공·실패 로그에 사용자 원문과 비밀값을 넣지 않았다.
- [ ] `pytest tests/unit/test_volume08_policy_fallback_router.py -q`를 외부 호출 없이 실행했다.

## 9. 핵심 정리

fallback은 신뢰할 수 있는 대상을 더 찾는 절차이지 정책 예외가 아닙니다. 동일한 요청 제한을 유지하고, 고정된 순서와 제한된 retry budget을 계약으로 만들면 장애 전환을 재현 가능하게 테스트하면서도 권한·비용·지연 시간 경계를 유지할 수 있습니다.
