# Router 미니 프로젝트: 고정 fixture로 지원 요청 제어면 조합하기

## 1. 학습 목표

이 미니 프로젝트에서는 Volume 08에서 만든 정책(Policy), Rule, Keyword, Semantic, LLM, fallback, multi-stage escalation, Router API 계약을 하나의 고정 요청 집합으로 조합합니다. 학습자는 각 Router가 다른 분류 방법을 쓰더라도 최종 대상 선택은 항상 capability, allowlist, 비용, 지연 시간, health 정책을 통과해야 한다는 점을 확인할 수 있어야 합니다.

## 2. 왜 조합 검증이 필요한가

각 Router의 단위 테스트만 통과해도 조합 과정에서 문제가 생길 수 있습니다.

- 분류 Router마다 서로 다른 target 또는 정책 제약을 사용해 동작 의미가 달라질 수 있습니다.
- fallback이나 escalation이 정상 경로보다 넓은 권한을 얻을 수 있습니다.
- API adapter가 Python Router의 결정과 다른 응답을 만들 수 있습니다.
- 로그를 합치는 과정에서 사용자 원문을 다시 기록할 수 있습니다.

`RouterMiniProject`는 실제 Agent, Tool, Model, embedding, LLM, HTTP 서버를 실행하지 않습니다. 대신 사전 검토한 fixture와 로컬 `PolicyRouter`만 사용해 이 경계를 반복 가능하게 검증합니다.

## 3. 동작 구조

```text
고정 요청 ID 집합
  │
  ├── mini-policy-001 ───────► PolicyRouter ───────────────► Agent
  ├── mini-rule-001 ─────────► RuleRouter ─────► PolicyRouter ► Agent
  ├── mini-keyword-001 ──────► KeywordRouter ─► PolicyRouter ► Agent
  ├── mini-semantic-001 ─────► Semantic fixture ─► PolicyRouter ► Agent
  ├── mini-llm-001 ──────────► LLM response fixture ─► PolicyRouter ► Agent
  ├── mini-fallback-001 ─────► unhealthy primary ─► fallback PolicyRouter ► Agent
  ├── mini-escalation-001 ───► Agent ─► Tool ─► Model stage PolicyRouter
  └── mini-api-001 ──────────► strict JSON API ─► PolicyRouter ► Agent

모든 성공 결과 ───────────────────────────────────────────► 원문 없는 JSON audit report
```

각 분류 fixture는 request ID와 intent·score만 보관합니다. 원문, prompt, raw LLM output, API 키는 fixture와 report에 넣지 않습니다. fallback은 최대 한 번, escalation은 첫 stage 뒤 최대 두 번만 시도하도록 명시적으로 제한됩니다.

## 4. 실습 환경

- 실행 위치: 저장소 루트의 활성화된 Anaconda PowerShell Prompt
- Python 환경: `ai-platform-engineering-book` Conda 환경
- 외부 서비스: 필요 없음
- API 키와 환경 변수: 필요 없음

> [!WARNING]
> 이 실습의 `LLMRouter`는 실제 LLM을 호출하지 않습니다. 고정 classifier response fixture를 학습용으로 재생합니다. 실제 서비스에서 fixture를 모델 응답으로 바꿀 때도 confidence threshold, schema 검증, 정책 재검증, 원문 없는 로그 계약을 먼저 유지해야 합니다.

## 5. 단계별 실습

```bash
# 실행 위치: 저장소 루트
python examples/volume08/router_mini_project.py
pytest tests/unit/test_volume08_router_mini_project.py -q
```

첫 명령은 여덟 Router 경로의 canonical strict JSON report 한 줄을 출력합니다. `render_audit_report()`는 출력 직전에 전체 경로 집합, field allowlist, 경로별 원문 비노출을 다시 검사하고 key를 정렬한 compact JSON만 반환합니다. 두 번째 명령은 target, fallback 순서, escalation 순서, API 응답, 결정론성, 원문 비노출을 검사합니다. 두 명령 모두 네트워크 연결이나 live API를 사용하지 않습니다.

감사 record allowlist와 원문 부분 문자열 비노출 계약만 별도로 확인하려면 다음 명령을 실행합니다.

```bash
# 실행 위치: 저장소 루트
pytest tests/unit/test_volume08_router_audit.py -q
```

## 6. 코드 설명

`src/ai_platform/router/mini_project.py`의 `build_router_mini_project()`는 다음 고정 계약을 구성합니다.

1. `PolicyRouter`는 일반 지원 Agent와 더 비싼 Model 중 정책상 가장 적합한 Agent를 고릅니다.
2. `RuleRouter`는 검증된 `billing` capability에 일치하는 `billing-support` rule의 `refund` capability를 추가하고, billing Agent를 정책으로 재검증합니다.
3. `KeywordRouter`는 `order`, `tracking` keyword와 `0.90` confidence를 `0.80` threshold에 대조한 후 주문 Agent의 capability를 정책에 추가합니다.
4. `SemanticRouter`는 `refund`의 `0.93` score fixture를 `0.85` threshold에 대조한 후 환불 Agent를 정책으로 재검증합니다.
5. `LLMRouter`는 `priority_support`의 `0.92` response fixture를 `0.85` threshold에 대조하고 우선 지원 Agent를 정책으로 재검증합니다.
6. `PolicyFallbackRouter`는 unhealthy primary를 먼저 기록하고, 같은 요청 제약으로 healthy fallback Agent를 한 번만 시도합니다.
7. `MultiStageEscalationRouter`는 허용된 Model만 남기는 요청 제약을 그대로 보존하며 unhealthy Agent와 Tool 뒤 Model stage를 선택합니다.
8. `RouterAPI`는 strict JSON body를 기존 `PolicyRouter`에 한 번 전달하고 `200` body만 report에 포함합니다.

`RouterMiniProject.run()`은 모든 성공 결과에 각 Router의 `as_log_record()`를 사용합니다. 이 메서드는 대상 이름, 정책 이름, 비용, 지연 시간, confidence처럼 조사에 필요한 최소 메타데이터만 반환합니다. 반환 직전에는 `validate_router_audit_report()`가 고정된 여덟 report 경로의 누락·추가를 fail closed 하고, 각 경로가 자기 Router에 정해진 정확한 field schema와 **값 타입·의미 범위·고정 request ID**를 따르는지도 확인합니다. 따라서 다른 경로의 정상 audit record를 복사해 붙이는 cross-route replay도 export 전에 거부됩니다. decision의 값은 공백 전용이 아닌 문자열이어야 하고, `confidence`·classifier confidence·similarity는 `0`~`1`의 유한한 decimal 문자열, 비용은 0 이상의 유한한 decimal 문자열, 지연 시간은 0 이상의 정수 decimal 문자열이어야 합니다. `target_kind`와 stage target kind는 `agent`·`tool`·`model`만 허용합니다. keyword·fallback·escalation의 순서 정보는 중복·공백 전용 항목이 없는 비어 있지 않은 문자열 `list`여야 하며, budget counter는 부울이 아닌 0 이상의 정수여야 합니다. API는 `100`~`599` 정수 status code, 비어 있지 않은 `outcome`, 같은 문자열·의미 범위·고정 request ID의 중첩 decision 계약을 유지합니다. 따라서 예를 들어 Policy record에 Rule field를 섞거나, `confidence`를 숫자나 `1` 초과 문자열로 바꾸거나, 비용을 음수로 만들거나, 순서 목록에 중복된 policy 이름을 넣거나, 다른 경로의 `request_id`를 넣거나, API의 중첩 `decision`에서 필수 decision field를 빼면 거부됩니다. 이어 각 경로의 `validate_router_audit_record()`가 field allowlist, **strict JSON** 직렬화 가능 여부, 해당 요청 원문의 부분 문자열 비노출을 다시 검사합니다. `render_audit_report()`는 이 결과를 `serialize_router_audit_report()`로 다시 검증한 뒤 key 정렬·compact separator·`allow_nan=False`를 적용한 canonical JSON 한 줄로 내보냅니다. 따라서 Python의 `NaN`, `Infinity`, `-Infinity`처럼 기본 `json.dumps()`가 관대하게 허용할 수 있는 비표준 숫자도 거부하고, 검증 뒤 dict가 변경된 경우에도 export 경계에서 fail closed 합니다. 새 경로나 field를 추가할 때에는 이 경계를 넓히기 전에 해당 값이 운영 조사에 꼭 필요한지와 민감 정보가 아닌지를 검토해야 합니다.

## 7. 정상 실행 결과

출력에는 다음 값이 포함됩니다. JSON key 순서는 `sort_keys=True` 때문에 고정됩니다.

```text
"policy": {"target_name": "mini-policy-agent", ...}
"rule": {"rule_name": "billing-support", "target_name": "mini-rule-billing-agent", ...}
"keyword": {"intent": "order_tracking", "target_name": "mini-order-agent", ...}
"semantic": {"semantic_similarity": "0.93", "target_name": "mini-refund-agent", ...}
"llm": {"llm_classifier_confidence": "0.92", "target_name": "mini-priority-agent", ...}
"fallback": {"attempted_policy_names": ["mini-primary-policy", "mini-fallback-policy"], ...}
"escalation": {"attempted_stage_names": ["mini-agent-stage", "mini-tool-stage", "mini-model-stage"], ...}
"api": {"status_code": 200, "body": {"outcome": "routed", ...}}
```

정확한 전체 출력은 `examples/volume08/router_mini_project.py`를 실행해 확인합니다. `test_volume08_router_mini_project.py`는 같은 report를 두 번 실행해 완전히 동일한지 확인합니다.

## 8. 오류 해결

| 증상 | 원인 | 확인과 해결 |
|---|---|---|
| `NoConfident...RouteError` | fixture score 또는 confidence가 threshold보다 낮음 | 해당 Router의 fixture ID, intent, threshold를 함께 확인하고 임의 fallback을 추가하지 않음 |
| `FallbackRouteExhaustedError` | primary와 retry budget 안의 fallback 모두 정책 조건을 통과하지 못함 | health, allowlist, capability, cost, latency 및 retry budget을 확인 |
| `EscalationRouteExhaustedError` | stage 교집합이 비었거나 budget 안에 healthy target이 없음 | request allowlist와 stage target의 교집합, stage 순서, escalation budget을 확인 |
| API가 `400` 또는 `422` | JSON schema가 틀렸거나 policy상 대상이 없음 | `08-router-api.md`의 strict body와 `NO_ELIGIBLE_ROUTE` 계약을 확인 |
| `UnsafeRouterAuditRecordError` | allowlist 밖 field, route별 고정 schema 또는 값 타입·의미 범위와 다른 값(예: 문자열 `confidence` 대신 숫자 또는 `1` 초과 값, 음수 비용, 소수 지연 시간, `list` 대신 tuple, 공백 전용·중복 순서 항목, counter의 `true`), strict JSON이 아닌 값(`NaN`/`Infinity` 포함), 원문 부분 문자열, 또는 export 전 변경된 report가 포함됨 | `as_log_record()`를 사용하고, confidence·similarity를 `0`~`1` 유한 decimal 문자열로, 비용을 0 이상의 유한 decimal 문자열로, 지연 시간을 0 이상의 정수 문자열로 복원합니다. 순서 field에서는 공백을 제거한 고유 이름만 한 번씩 기록합니다. API 중첩 decision에도 같은 범위를 적용합니다. field를 추가하기 전 민감 정보와 해당 route schema·값 타입·범위를 함께 검토한 뒤 audit 테스트의 예상 계약을 갱신합니다. |
| report에 원문이 포함됨 | 새 로그를 직접 조립하면서 request text를 추가함 | `as_log_record()`와 audit validator를 사용하고 privacy 회귀 테스트를 추가 |

## 9. 응용 실습과 과제

### 응용 실습

1. Policy Router에 같은 capability를 가진 더 저렴한 target을 추가하고 비용 → 지연 시간 → 이름 동점 해소가 유지되는지 확인합니다.
2. Semantic fixture score를 `0.84`로 바꾸고 `NoConfidentSemanticRouteError`를 예상하는 테스트를 작성합니다.
3. escalation request의 allowlist에 Model 외 target을 추가해도 stage fixture 순서와 budget이 변경되지 않는지 확인합니다.

### 과제

- **기본:** `mini-policy-001`에 최대 비용과 최대 지연 시간을 더 좁힌 고정 request를 추가하고 예상 target을 테스트합니다.
- **응용:** LLM fixture가 없는 request ID의 안전 실패를 report와 분리된 오류 audit record로 설계합니다. prompt나 raw response를 기록하지 마세요.
- **심화:** 이 미니 프로젝트의 Router 결과를 Volume 09 workflow state의 입력으로 변환하는 adapter를 설계합니다. adapter는 `target_name`, `target_kind`, `request_id`만 전달하고 policy·classifier 원문을 다시 평가하지 않아야 합니다.

## 10. 다음 Volume 인계

Volume 09 LangGraph는 이 Volume의 결과를 다음처럼 입력으로 사용할 수 있습니다.

| 인계 항목 | 계약 | 유지해야 하는 경계 |
|---|---|---|
| 선택 결과 | `RouteDecision` 또는 각 합성 decision의 `target` | workflow가 Router 정책을 재구현하거나 완화하지 않음 |
| 추적 ID | `request_id` | workflow state와 감사 로그의 상관관계에만 사용하고 원문으로 대체하지 않음 |
| 감사 로그 | `as_log_record()`의 JSON 가능 dict | prompt, raw classifier output, 사용자 원문을 state 또는 로그에 추가하지 않음 |
| 안전 실패 | `NoEligibleRouteError`의 하위 예외 | fallback·escalation budget 밖에서 자동 재시도하지 않고 명시적 error node로 전달 |

## 11. 완료 체크리스트

- [ ] 여덟 Router 경로가 하나의 고정 request ID 집합에서 실행된다.
- [ ] Rule, Keyword, Semantic, LLM 분류 결과가 각각 PolicyRouter의 capability·allowlist·cost·latency·health 검사를 통과한다.
- [ ] fallback의 retry budget과 escalation의 budget이 명시적이며 제한되어 있다.
- [ ] Agent, Tool, Model stage가 fixture 순서와 target kind를 보존한다.
- [ ] API 결과가 strict JSON 계약 뒤 기존 policy 결정을 사용한다.
- [ ] report는 route별 고정 field schema와 값 타입·범위·request ID(`0`~`1` confidence/similarity 문자열, 0 이상 비용·정수 지연 시간 문자열, Agent·Tool·Model target kind, 중복·공백 전용 항목이 없는 문자열 `list`, 정수 counter, HTTP status code), audit field allowlist, strict JSON 직렬화 검사를 통과하며 사용자 원문, prompt, raw classifier output, 비밀 값, `NaN`/`Infinity`, 다른 경로의 audit record 재사용을 포함하지 않는다.
- [ ] 예제와 `test_volume08_router_mini_project.py`를 외부 호출 없이 실행했다.
- [ ] Volume 09에 전달할 decision·audit·안전 실패 계약을 확인했다.

## 12. 핵심 정리

Router 제어면은 분류 방식이 늘어나도 정책 경계를 하나로 유지해야 합니다. 이 미니 프로젝트는 고정 fixture로 여러 Router를 함께 실행하지만, 어느 경로도 비용, 지연 시간, capability, health, 허용 대상 정책을 우회하지 않습니다. 다음 workflow 단계는 이 결정 결과를 소비할 수 있지만 Router를 다시 선택하거나 원문을 로그에 복원해서는 안 됩니다.
