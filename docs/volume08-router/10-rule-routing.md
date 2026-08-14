# Rule-based Router: 명시적 capability 규칙을 정책 경계 안에서 적용하기

## 1. 학습 목표

이 장을 마치면 자연어 모델이나 keyword 추측 없이 요청의 **명시적 capability**에 따라 고정 rule을 선택하고, rule이 최종 대상 선택 권한을 갖지 않도록 `PolicyRouter`에서 다시 검증하는 방법을 설명할 수 있습니다.

## 2. 왜 필요한가

일부 요청은 이미 검증된 업무 신호를 갖습니다. 예를 들어 결제 시스템이 `billing` capability를 부여했다면 Router가 문장의 표현을 다시 분류할 필요 없이 결제 지원 rule을 적용할 수 있습니다. 그러나 rule이 곧바로 Agent를 호출하면 allowlist, health, 비용, 지연 시간 제한을 우회할 위험이 있습니다.

`RuleRouter`는 고정 rule을 고른 뒤 추가 capability만 요청에 합치고, 최종 선택은 기존 `PolicyRouter`에 맡깁니다. 이 실습은 실제 Agent, Tool, Model, LLM, API, 네트워크를 호출하지 않습니다.

## 3. 핵심 개념

- **명시적 rule:** `required_request_capabilities`가 요청 capability의 부분집합일 때만 일치합니다.
- **추가 capability:** rule의 `added_required_capabilities`는 선택 대상이 실제로 제공해야 하는 기능입니다.
- **결정론적 우선순위:** 일치 rule 중 `priority`가 큰 것을 고르고, 동점이면 rule 이름 사전순을 사용합니다.
- **Fail closed:** 일치 rule이 없으면 `NoMatchingRuleRouteError`로 실패합니다. policy 조건을 통과하는 대상이 없으면 기존 `NoEligibleRouteError`를 그대로 반환합니다.
- **정책 재검증:** rule은 allowlist, health, cost, latency 조건을 완화하거나 fallback을 추가할 수 없습니다.

## 4. 동작 구조

```text
RoutingRequest.requirements.required_capabilities
                 │
                 ▼
          RuleRouter
          ├── 모든 일치 rule 탐색
          └── priority 내림차순, 이름 오름차순 선택
                 │
                 ▼
원래 capability ∪ rule 추가 capability
                 │
                 ▼
          PolicyRouter
  health ─► allowlist ─► capability ─► cost/latency
                 │
                 ▼
    RuleRouteDecision.as_log_record()
    └── request_id, rule 이름, policy 결정만 기록
```

## 5. 실습 환경

- `src/ai_platform/router/rule.py`: rule 계약, 결정론적 선택, policy 재검증입니다.
- `examples/volume08/rule_router.py`: 고정 billing fixture 예제입니다.
- `tests/unit/test_volume08_rule_router.py`: 우선순위, 동점, 안전 실패, privacy 계약 테스트입니다.

```bash
# 실행 위치: 저장소 루트
conda env update --file environment.yml --prune
python examples/volume08/rule_router.py
pytest tests/unit/test_volume08_rule_router.py -q
```

모든 명령은 API 키·환경 변수·네트워크 연결 없이 실행됩니다.

## 6. 코드 설명

예제의 요청은 이미 `billing` capability를 갖습니다. `billing-support` rule은 `refund`와 `respond` capability를 추가합니다. `offline-billing-agent`가 세 기능을 모두 제공하고 비용 `0.003`, 지연 시간 `70ms`, allowlist를 통과하므로 선택됩니다.

```python
selected_route = min(matching_routes, key=lambda route: (-route.priority, route.name))
```

이 tie-break는 fixture 선언 순서가 바뀌어도 같은 rule을 선택하게 합니다. 그 다음 `RoutingRequirements`를 새로 만들어 원래 `maximum_cost`, `maximum_latency_ms`, `permitted_target_names`를 변형 없이 보존합니다.

## 7. 정상 실행 결과

검증 시 예제는 다음 JSON 한 줄을 출력했습니다.

```text
{"confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "70", "policy_name": "offline-rule-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-rule-001", "rule_name": "billing-support", "rule_router_name": "offline-rule-router", "target_kind": "agent", "target_name": "offline-billing-agent"}
```

단위 테스트는 최우선 rule, 동점 해소, rule 미일치, policy 거부, JSON 직렬화 및 사용자 원문 비노출을 검사합니다.

## 8. 오류 해결

| 증상 | 원인 | 확인과 해결 |
|---|---|---|
| `no rule route matches the request capabilities` | 요청 capability가 어떤 rule 조건도 충족하지 않습니다. | 검증된 upstream capability와 `required_request_capabilities`를 비교합니다. 임의의 default rule을 추가하지 않습니다. |
| `no healthy target meets the routing requirements` | 일치 rule의 추가 capability 또는 원래 정책 제약 때문에 대상이 제외됐습니다. | rule 추가 capability, allowlist, health, cost, latency를 차례로 확인합니다. 정책을 건너뛰지 않습니다. |
| 같은 조건인데 다른 rule 선택 | priority 또는 이름이 변경됐을 수 있습니다. | 동점 rule과 기대 결과를 fixture 테스트에 명시합니다. |
| 로그에 원문이 있음 | application 코드가 request text를 직접 합쳤습니다. | `as_log_record()`만 사용하고 privacy 회귀 테스트를 유지합니다. |

## 9. 응용 실습과 과제

### 응용 실습

1. `technical` capability에 일치하는 rule과 Agent를 고정 fixture로 추가합니다.
2. `billing`과 `technical`에 같은 priority를 부여하고 이름 사전순 선택을 테스트합니다.
3. billing 요청 allowlist에서 billing Agent를 제거해 policy 안전 실패를 확인합니다.

### 과제

- **기본:** 비용 한도를 `0.002`로 낮춘 billing request가 policy에서 안전 실패하는 테스트를 작성합니다.
- **응용:** 고정 rule 두 개가 같은 요청에 일치할 때 priority 변경 전후의 기대 rule을 테스트로 비교합니다.
- **심화:** upstream capability 발급자를 검증하는 adapter 계약을 설계합니다. 이 Volume의 Router에 사용자 원문, 인증 헤더, API 키를 저장하거나 실제 upstream 호출을 추가하지 마세요.

## 10. 완료 체크리스트

- [ ] Rule Router와 Keyword/Semantic/LLM Router의 입력 신호 차이를 설명할 수 있다.
- [ ] `required_request_capabilities`와 `added_required_capabilities`의 역할을 설명할 수 있다.
- [ ] priority → 이름 동점 해소가 결정론성을 만드는 이유를 설명할 수 있다.
- [ ] rule이 PolicyRouter의 allowlist, health, cost, latency 경계를 우회하지 못함을 확인했다.
- [ ] 일치 rule이 없을 때 fail closed 해야 함을 이해한다.
- [ ] 예제와 단위 테스트를 외부 호출 없이 실행했다.
- [ ] 로그에 사용자 원문, prompt, raw output, 비밀값이 없음을 확인했다.

## 11. 다음 장 연결과 핵심 정리

Rule Router는 신뢰된 구조화 신호를 처리하는 가장 단순한 intent 경로입니다. 다음 [Keyword Router](02-keyword-routing.md)는 자연어 token을 고정 규칙으로 분류하지만, 최종 선택을 PolicyRouter에 재검증한다는 경계는 같습니다. Volume 09 workflow에는 최종 decision, request ID, 원문 없는 audit record와 안전 실패만 전달해야 합니다.
