# Multi-stage Router: 고정 escalation fixture로 Agent·Tool·Model을 안전하게 전환하기

## 1. 학습 목표

이 장에서는 외부 Agent, Tool, Model, API, 네트워크를 호출하지 않습니다. 요청 ID에 연결한 고정 `EscalationFixture`와 정적 정책 대상만으로 Agent → Tool → Model 순의 다단계 라우팅을 재현합니다. 각 단계는 원래 요청의 capability, 허용 대상, 비용, 지연 시간 제약을 그대로 다시 `PolicyRouter`에 전달해야 합니다.

## 2. 왜 다단계 Router가 필요한가

단일 Router는 한 대상이 정상이고 정책 조건을 만족한다는 가정에서 간단합니다. 하지만 실제 설계에서는 다음과 같은 순서가 필요할 수 있습니다.

1. 비용이 낮은 Agent를 먼저 시도한다.
2. Agent가 사용할 수 없으면 특정 Tool을 시도한다.
3. Tool도 사용할 수 없으면 더 비싼 Model을 검토한다.

이 순서를 임의의 런타임 판단이나 실제 재시도로 처리하면 결과를 재현하기 어렵고, 마지막 단계가 권한·비용 제한을 우회할 위험이 있습니다. 이 실습은 **고정 순서, 명시적 예산, 매 단계 policy 재검증**을 계약으로 만듭니다.

## 3. 고정 stage·fixture 계약

`RoutingStage`는 하나의 단계가 선택할 수 있는 대상 종류와 이름을 고정합니다.

- `name`: 감사 로그와 fixture가 참조하는 고유 stage 이름
- `target_kind`: `agent`, `tool`, `model` 중 하나
- `policy_router`: 해당 stage에서 실행할 기존 `PolicyRouter`
- `permitted_target_names`: 해당 policy 안에 존재하며 `target_kind`와 일치하는 대상 이름 집합

생성 시 stage의 대상 이름이 policy에 없거나 대상 유형이 맞지 않으면 `RoutingConfigurationError`로 거부합니다. 따라서 `tool-stage`가 Agent를, `model-stage`가 Tool을 선택할 수 없습니다.

`EscalationFixture`는 사용자 원문 없이 요청 ID마다 시도 순서를 고정합니다.

```python
EscalationFixture(
    request_id="lesson-08-escalation-001",
    stage_names=("agent-stage", "tool-stage", "model-stage"),
)
```

fixture의 stage는 중복될 수 없고 모두 구성된 stage여야 합니다. 실제 대상 상태와 policy 조건에 따라 일부 stage가 실패하더라도 다음 stage는 이 고정 순서로만 검토됩니다.

## 4. escalation budget과 안전 실패

`MultiStageEscalationRouter`의 `escalation_budget`은 첫 stage 뒤에 추가로 시도할 수 있는 최대 stage 수입니다.

| `escalation_budget` | 최대 시도 수 | 예시 fixture 순서 |
|---:|---:|---|
| `0` | 1 | Agent만 시도 |
| `1` | 2 | Agent, Tool |
| `2` | 3 | Agent, Tool, Model |

성공 후에는 `MultiStageRouteDecision`에 실제 시도한 `attempted_stage_names`와 `escalation_count`를 남깁니다. 다음 경우에는 성공 대상을 만들어 내지 않고 fail closed 합니다.

| 조건 | 오류 |
|---|---|
| 요청 ID의 escalation fixture가 없음 | `NoEscalationFixtureError` |
| budget 안에서 모든 stage가 policy 조건을 만족하지 못함 | `EscalationRouteExhaustedError` |

두 오류 모두 `NoEligibleRouteError` 계열입니다. 따라서 상위 호출자는 fixture 누락이나 budget 소진을 외부 API 호출, 무제한 재시도, 임의의 fallback 성공으로 바꾸지 않아야 합니다.

## 5. 매 stage의 PolicyRouter 재검증

각 stage는 원래 `RoutingRequest`를 복제하면서 자기 `permitted_target_names`로만 대상을 **더 좁힙니다**. 원래 요청에 허용 대상이 있다면 두 집합의 교집합만 사용합니다. 교집합이 비면 그 stage는 안전하게 실패합니다.

다음 조건은 모든 Agent·Tool·Model stage에서 다시 검사됩니다.

- `required_capabilities`
- `permitted_target_names`
- `maximum_cost`
- `maximum_latency_ms`
- 대상 `healthy` 상태

따라서 escalation으로 다음을 할 수 없습니다.

- Agent 실패 후 허용되지 않은 Tool 또는 Model을 선택하는 것
- 마지막 Model stage에서 비용·지연 시간 한도를 무시하는 것
- 실패한 capability 요구를 일반 대상 선택으로 숨기는 것
- fixture에 없는 stage나 실제 네트워크 호출을 추가하는 것

## 6. 고정 fixture 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume08/multi_stage_escalation_router.py
uv run pytest tests/unit/test_volume08_multi_stage_escalation_router.py -q
```

예제는 고정 Agent와 Tool을 비정상 상태로 두고, `agent-stage → tool-stage → model-stage` 순으로 세 단계를 검토합니다. `offline-summary-model`은 비용 `0.004`, 지연 시간 `90ms`이며 요청의 비용 `0.005`, 지연 시간 `100ms`, 허용 대상 제약을 모두 만족해 최종적으로 선택됩니다. API 키, 환경 변수, 외부 서비스, 네트워크는 사용하지 않습니다.

정상 실행 출력은 사용자 원문 없이 다음과 같습니다.

```text
{"attempted_stage_names": ["agent-stage", "tool-stage", "model-stage"], "confidence": "1", "escalation_count": 2, "estimated_cost": "0.004", "estimated_latency_ms": "90", "multi_stage_router_name": "offline-support-escalation-router", "policy_name": "offline-model-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-escalation-001", "stage_name": "model-stage", "stage_target_kind": "model", "target_kind": "model", "target_name": "offline-summary-model"}
```

## 7. 감사 로그

성공한 `MultiStageRouteDecision.as_log_record()`는 기존 policy 결정 로그에 다음만 추가합니다.

| 필드 | 의미 |
|---|---|
| `multi_stage_router_name` | 다단계 Router 이름 |
| `stage_name` | 성공한 고정 stage 이름 |
| `stage_target_kind` | 성공한 stage의 `agent`·`tool`·`model` 유형 |
| `escalation_count` | 첫 단계 뒤 실제로 시도한 stage 수 |
| `attempted_stage_names` | budget 안에서 실제로 검토한 stage 순서 |

`EscalationRouteExhaustedError.as_log_record()`는 `request_id`, `outcome`, `attempted_stage_names`만 보관합니다. 성공·실패 로그 모두 사용자 `text`, Tool 인수, prompt, raw model output, 인증 값, API 키를 저장하지 않습니다.

## 8. 계약 테스트가 검증하는 내용

`tests/unit/test_volume08_multi_stage_escalation_router.py`는 고정 fixture만 사용해 다음을 검증합니다.

- Agent → Tool → Model의 fixture 순서와 최종 Model 선택
- `escalation_budget=0`일 때 첫 stage만 시도하고 fail closed 하는 동작
- permission, cost, latency 제약을 어떤 stage도 우회하지 못하는 동작
- fixture 누락의 안전 실패
- 성공·소진 로그의 JSON 직렬화 가능성과 사용자 원문 부재
- 음수·불리언 budget, 유형 불일치 stage, 알 수 없는 fixture stage의 거부

## 9. 완료 체크리스트

- [ ] stage마다 고정 대상 이름과 `RouteTargetKind`를 선언했다.
- [ ] 요청 ID별 `EscalationFixture`로 시도 순서를 고정했다.
- [ ] `escalation_budget`을 명시적으로 선언했다.
- [ ] 모든 stage가 capability·permission·cost·latency·health policy를 재검증함을 확인했다.
- [ ] fixture 누락과 budget 소진을 임의 성공으로 대체하지 않았다.
- [ ] 감사 로그에 사용자 원문, prompt, raw output, 비밀값을 넣지 않았다.
- [ ] `uv run pytest tests/unit/test_volume08_multi_stage_escalation_router.py -q`를 외부 호출 없이 실행했다.

## 10. 핵심 정리

다단계 라우팅은 실패 뒤 더 강력하거나 비싼 대상을 선택할 수 있지만, escalation 자체가 권한을 주어서는 안 됩니다. 고정 fixture로 stage 순서를 재현하고, 명시적 budget으로 시도를 제한하며, 모든 stage에서 `PolicyRouter`를 다시 적용하면 Agent·Tool·Model 전환도 결정론적이고 감사 가능한 fail-closed 계약으로 테스트할 수 있습니다.
