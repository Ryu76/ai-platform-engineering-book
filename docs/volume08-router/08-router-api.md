# Router API: 고정 PolicyRouter를 안전한 HTTP 계약으로 노출하기

## 1. 학습 목표

이 장에서는 외부 HTTP 서버, API, 네트워크를 실행하지 않고 `PolicyRouter`를 `POST /routes`의 요청·응답 계약으로 변환합니다. 학습자는 JSON 입력을 검증하고, 정책 결정을 JSON 응답으로 반환하며, 입력 오류와 정책상 대상 부재를 서로 다른 상태 코드로 fail closed 할 수 있어야 합니다.

## 2. 왜 Router API 경계가 필요한가

Router 자체는 `RoutingRequest`와 `RouteDecision`이라는 Python 계약을 사용합니다. 웹 클라이언트는 JSON과 HTTP 상태 코드만 이해합니다. 경계를 명확히 하지 않으면 다음 문제가 생길 수 있습니다.

- 문자열 비용을 부동소수점으로 바꾸면서 정밀도와 검증 규칙이 흐려진다.
- 잘못된 입력의 validation detail이나 사용자 원문이 응답에 그대로 포함된다.
- 대상이 없을 때 임의 fallback이나 성공 응답을 만들어 정책 실패를 숨긴다.
- 웹 계층이 capability, permission, cost, latency 정책을 다시 구현해 Router와 달라진다.

이 실습의 `RouterAPI`는 JSON을 기존 `RoutingRequest`로 한 번만 변환하고 실제 선택은 기존 `PolicyRouter`에만 위임합니다.

## 3. 로컬 HTTP 계약

이 구현은 프레임워크 독립적입니다. `route_post(payload)`는 웹 프레임워크가 JSON body로 넘길 값과 HTTP로 반환할 값을 `RouterAPIResponse`로 표현합니다. 실제 FastAPI 서버, socket, API 키, 환경 변수, 네트워크 호출은 없습니다.

```text
POST /routes JSON body
        │
        ▼
Pydantic strict schema validation
        │
        ▼
RoutingRequest / RoutingRequirements
        │
        ▼
PolicyRouter (capability · permission · cost · latency · health)
        │
        ▼
RouterAPIResponse(status_code, JSON body)
```

`RouterAPIResponse.status_code`와 `body`를 이후 웹 프레임워크 adapter가 그대로 HTTP 응답으로 사용할 수 있습니다. policy 선택 로직을 API layer에 복제하지 않는 것이 핵심입니다.

## 4. 요청과 응답 형식

`POST /routes` body는 다음 JSON 원시 타입만 받습니다. 알 수 없는 필드는 거부합니다.

```json
{
  "request_id": "lesson-08-api-001",
  "text": "주문 상태를 알려 주세요.",
  "requirements": {
    "required_capabilities": ["lookup_order", "respond"],
    "maximum_cost": "0.004",
    "maximum_latency_ms": 80,
    "permitted_target_names": ["offline-order-agent"]
  }
}
```

| 필드 | 형식 | 설명 |
|---|---|---|
| `request_id` | 비어 있지 않은 문자열 | 결정과 안전 실패를 추적하는 식별자 |
| `text` | 비어 있지 않은 문자열 | Router에만 전달되며 응답·결정 로그에는 포함하지 않음 |
| `required_capabilities` | 문자열 배열 | 대상이 모두 지원해야 하는 기능 |
| `maximum_cost` | 문자열 또는 생략 | `Decimal`으로 안전하게 변환하는 최대 비용 |
| `maximum_latency_ms` | 정수 또는 생략 | 최대 지연 시간 |
| `permitted_target_names` | 문자열 배열 또는 생략 | 선택 가능한 대상 이름을 더 좁히는 allowlist |

성공은 `200`과 원문 없는 `RouteDecision.as_log_record()`를 반환합니다.

```json
{
  "outcome": "routed",
  "decision": {
    "request_id": "lesson-08-api-001",
    "policy_name": "offline-router-api-policy",
    "target_name": "offline-order-agent",
    "target_kind": "agent",
    "reason": "healthy-capability-cost-latency-policy",
    "confidence": "1",
    "estimated_cost": "0.003",
    "estimated_latency_ms": "70"
  }
}
```

## 5. 안전 실패 계약

| 조건 | 상태 코드 | `error_code` | 응답 원칙 |
|---|---:|---|---|
| schema, 타입, Decimal, policy 제한 입력이 잘못됨 | `400` | `INVALID_ROUTING_REQUEST` | validation detail, 원문, 알 수 없는 필드를 반환하지 않음 |
| 입력은 유효하지만 정상이고 정책을 만족하는 대상이 없음 | `422` | `NO_ELIGIBLE_ROUTE` | `request_id`와 고정 오류 코드만 반환하고 임의 대상을 선택하지 않음 |

`422`는 `PolicyRouter`의 `NoEligibleRouteError`를 받았다는 뜻입니다. API layer는 fallback, retry, escalation을 자동으로 추가하지 않습니다. 그런 동작은 별도의 명시적 Router 계약에서만 허용해야 합니다.

> [!WARNING]
> Pydantic validation error에는 입력 조각이 들어 있을 수 있습니다. 이 실습은 그 detail을 HTTP body로 되돌려주지 않습니다. 사용자 `text`, prompt, API 키, 인증 헤더를 오류 메시지나 decision log에 넣지 마세요.

## 6. 고정 fixture 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume08/router_api.py
uv run pytest tests/unit/test_volume08_router_api.py -q
```

첫 명령은 실제 서버를 열지 않고 고정 JSON body를 처리합니다. 정상 출력은 다음과 같습니다.

```text
{"body": {"decision": {"confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "70", "policy_name": "offline-router-api-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-api-001", "target_kind": "agent", "target_name": "offline-order-agent"}, "outcome": "routed"}, "status_code": 200}
```

## 7. 코드 설명

`_RoutingRequestPayload`와 `_RoutingRequirementsPayload`는 strict Pydantic schema입니다. JSON 문자열만 `maximum_cost`로 허용한 뒤 `Decimal`로 변환하므로 binary float가 API 계약에 섞이지 않습니다.

`RouterAPI.route_post()`는 다음 순서를 고정합니다.

1. body를 strict schema와 기존 `RoutingRequest` 계약으로 검증한다.
2. 입력 오류면 detail 없이 `400 INVALID_ROUTING_REQUEST`를 반환한다.
3. 유효한 요청만 `PolicyRouter.route()`에 전달한다.
4. policy가 대상 부재로 실패하면 `422 NO_ELIGIBLE_ROUTE`를 반환한다.
5. 성공하면 기존 정책 결정 로그만 `200` body에 넣는다.

따라서 API는 정책을 완화하거나 선택 결과를 재계산하지 않습니다.

## 8. 오류 해결

| 증상 | 원인 | 확인과 해결 |
|---|---|---|
| `400 INVALID_ROUTING_REQUEST` | `maximum_cost`가 숫자 JSON이거나 허용되지 않은 필드가 있음 | 비용을 `"0.004"` 같은 문자열로 전달하고 body 필드 이름을 확인 |
| `422 NO_ELIGIBLE_ROUTE` | capability, allowlist, cost, latency, health 중 하나가 대상과 맞지 않음 | 고정 fixture target과 `requirements`의 교집합을 확인 |
| 응답에 원문이 보임 | API adapter가 `text`나 validation detail을 직접 추가함 | `RouterAPIResponse.body`에는 `as_log_record()`와 고정 오류 코드만 사용 |
| 실제 서버가 필요함 | 이 장의 범위를 넘어 웹 transport를 붙이려 함 | 먼저 이 로컬 계약 테스트를 통과시키고 다음 integration slice에서 서버 adapter를 추가 |

## 9. 응용 실습과 과제

### 응용 실습

1. `permitted_target_names`를 생략한 body와 하나의 대상만 허용한 body를 각각 실행해 policy 선택이 어떻게 좁아지는지 확인합니다.
2. `maximum_cost`를 JSON number로 바꾸어 `400`이 되는 이유를 설명합니다.
3. `422` 응답에서 policy 이름이나 사용자 원문을 추가하지 않고도 운영자가 조사할 수 있는 최소 로그 필드를 설계합니다.

### 과제

- **기본:** `RouterAPI` 테스트에 빈 `text`와 빈 `permitted_target_names`의 `400` 사례를 추가합니다.
- **응용:** 별도 `KeywordRouter` adapter를 설계하되 confidence 미달을 새 고정 오류 코드로 매핑하고 policy 제약을 그대로 보존합니다.
- **심화:** 프레임워크 adapter의 access log와 `RouterAPIResponse.body`를 분리하고, 어떤 필드도 API 키·prompt·원문을 포함하지 않는 회귀 테스트를 작성합니다.

## 10. 완료 체크리스트

- [ ] 요청 body를 strict JSON schema로 검증했다.
- [ ] 비용은 JSON number가 아니라 `Decimal` 문자열 계약으로 받는다.
- [ ] API layer가 policy capability·permission·cost·latency·health 검사를 재구현하거나 완화하지 않는다.
- [ ] 입력 오류는 `400 INVALID_ROUTING_REQUEST`로 fail closed 한다.
- [ ] 대상 부재는 `422 NO_ELIGIBLE_ROUTE`로 fail closed 한다.
- [ ] 성공·실패 body에서 사용자 원문과 validation detail을 제외했다.
- [ ] 고정 fixture 예제와 `test_volume08_router_api.py`를 외부 호출 없이 실행했다.

## 11. 핵심 정리

Router API는 Router 선택을 웹 계층으로 옮기는 기능이 아닙니다. strict JSON 검증 뒤 기존 policy 계약을 한 번 호출하고, 성공에는 원문 없는 decision log를, 실패에는 최소 오류 코드만 반환하는 경계입니다. 이 구조는 후속 HTTP framework adapter를 붙여도 Router의 결정론성, 정책 경계, privacy 계약을 유지하게 합니다.
