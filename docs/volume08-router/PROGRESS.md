# Volume 08 Router 진행 기록

## 2026-08-10 — Tick 1: 결정론적 정책 Router 기반

완료한 범위:

- `RouteTarget`, `RoutingRequirements`, `RoutingRequest`, `RouteDecision` 계약을 추가했습니다.
- capability, 허용 대상, 정적 비용, 정적 지연 시간, 상태 조건을 모두 검사하는 `PolicyRouter`를 추가했습니다.
- 비용 → 지연 시간 → 이름 순의 결정론적 동점 해소와 후보 부재 시 `NoEligibleRouteError` 안전 실패를 구현했습니다.
- 사용자 원문을 포함하지 않는 JSON 직렬화 가능 결정 로그를 구현했습니다.
- 고정 fixture 예제와 외부 호출 없는 단위 테스트를 추가했습니다.
- `01-policy-routing.md` 학습 장을 작성했습니다.

검증 결과:

```text
uv run pytest tests/unit/test_volume08_policy_router.py -q
10 passed in 0.06s

uv run pytest -q
71 passed in 0.81s

uv run python examples/volume08/policy_router.py
{"confidence": "1", "estimated_cost": "0.002", "estimated_latency_ms": "90", "policy_name": "offline-learning-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-policy-001", "target_kind": "model", "target_name": "offline-summary-model"}
```

남은 Volume 08 범위:

- Rule/Keyword/Semantic/LLM Router와 Intent 분류
- confidence threshold, fallback, retry, escalation
- Agent·Tool·Model 다단계 라우팅과 장애 전환
- Router 평가 dataset, routing accuracy 지표, API 및 나머지 학습 장

다음 슬라이스:

- 고정 keyword fixture와 명시적 confidence threshold를 갖는 Rule/Keyword Router를 추가하고, 정책 Router 제약을 통과시키는 경로를 검증합니다.

## 2026-08-10 — Tick 2: confidence threshold를 갖는 결정론적 Keyword Router

완료한 범위:

- 단일 Unicode token keyword, intent별 필수 capability, `Decimal` confidence를 검증하는 `KeywordRoute`를 추가했습니다.
- 명시적 `minimum_confidence`를 적용하고 confidence → 일치 keyword 수 → intent 이름 순으로 rule을 결정론적으로 선택하는 `KeywordRouter`를 추가했습니다.
- threshold 미달 또는 일치 rule 부재 시 fallback을 실행하지 않고 `NoConfidentKeywordRouteError`로 안전 실패하게 했습니다.
- 선택된 intent capability를 기존 요청 capability에 합친 뒤 `PolicyRouter`에 전달하여 허용 대상·상태·비용·지연 시간 제약을 우회하지 못하게 했습니다.
- 원문 없이 classifier 이름, intent, confidence, 일치 keyword와 정책 결정을 남기는 JSON 직렬화 가능 로그를 추가했습니다.
- 고정 fixture 예제, 단위 테스트, `02-keyword-routing.md` 학습 장을 추가했습니다.

검증 결과:

```text
uv run pytest tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py -q
19 passed in 0.10s

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 4 source files

uv run python examples/volume08/keyword_router.py
{"classifier_confidence": "0.90", "classifier_name": "offline-keyword-intent-router", "confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "80", "intent": "order_tracking", "matched_keywords": ["order", "tracking"], "policy_name": "offline-support-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-keyword-001", "target_kind": "agent", "target_name": "order-support-agent"}

uv run pytest -q
80 passed in 0.78s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
```

남은 Volume 08 범위:

- Semantic/LLM Router와 Intent 분류
- fallback, retry, escalation
- Agent·Tool·Model 다단계 라우팅과 장애 전환
- Router 평가 dataset, routing accuracy 지표, API 및 나머지 학습 장

다음 슬라이스:

- 고정 평가 dataset으로 keyword Router의 routing accuracy와 threshold별 안전 실패를 측정하고, 외부 호출 없이 회귀 지표를 검증합니다.

## 2026-08-10 — Tick 3: 고정 Keyword Router 평가 dataset과 accuracy gate

완료한 범위:

- 정상 route와 `NO_CONFIDENT_KEYWORD_ROUTE`·`NO_ELIGIBLE_POLICY_ROUTE` 안전 실패를 명시하는 고정 `KeywordRoutingEvaluationCase`/`KeywordRoutingExpectation` 계약을 추가했습니다.
- route는 intent와 target을 함께 비교하고, 안전 실패는 실패 유형까지 비교하는 결정론적 `evaluate_keyword_router()`를 추가했습니다.
- 빈·중복 dataset과 모호한 기대값을 거부하고, 원문 없이 case ID·집계만 남기는 JSON 직렬화 가능 평가 보고서를 구현했습니다.
- 명시적 `Decimal` threshold를 검사하는 `RoutingQualityGateError` 기반 accuracy gate를 추가했습니다.
- 외부 호출 없는 fixture 예제, 계약 테스트, `03-keyword-router-evaluation.md` 학습 장을 추가했습니다.

검증 결과:

```text
uv run pytest tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py tests/unit/test_volume08_router_evaluation.py -q
29 passed in 0.11s

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py tests/unit/test_volume08_router_evaluation.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 5 source files

uv run python examples/volume08/keyword_router_evaluation.py
{"accuracy": "1", "correct_cases": 4, "correct_safe_failures": 2, "mismatched_case_ids": [], "total_cases": 4}

uv run pytest -q
90 passed in 0.96s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
```

남은 Volume 08 범위:

- Semantic/LLM Router와 Intent 분류
- fallback, retry, escalation
- Agent·Tool·Model 다단계 라우팅과 장애 전환
- API 및 나머지 학습 장

다음 슬라이스:

- policy 제약을 우회하지 않는 명시적 fallback chain과 retry budget을 고정 fixture·안전 실패 계약으로 추가합니다.

## 2026-08-10 — Tick 4: 정책 경계를 보존하는 제한된 fallback retry

완료한 범위:

- 동일한 `RoutingRequest`를 primary와 fallback `PolicyRouter`에 전달하는 `PolicyFallbackRouter`를 추가했습니다. 따라서 fallback도 capability·허용 대상·비용·지연 시간·상태 제약을 우회하지 못합니다.
- primary 우선 및 선언 순서의 결정론적 fallback을 구현하고, primary 뒤에 시도할 fallback 수를 명시적 정수 `retry_budget`으로 제한했습니다.
- 모든 허용 시도가 실패하면 실제 시도 policy 이름만 담은 `FallbackRouteExhaustedError`로 fail closed 하게 했습니다.
- 성공과 안전 실패 모두 사용자 원문 없이 JSON 직렬화 가능한 감사 로그를 제공했습니다.
- 고정 primary/fallback fixture 예제, retry budget·정책 제약·privacy 계약 테스트, `04-policy-fallback.md` 학습 장을 추가했습니다.

검증 결과:

```text
uv run pytest tests/unit/test_volume08_policy_fallback_router.py -q
7 passed in 0.09s

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py tests/unit/test_volume08_router_evaluation.py tests/unit/test_volume08_policy_fallback_router.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 6 source files

uv run python examples/volume08/policy_fallback_router.py
{"attempted_policy_names": ["offline-primary-policy", "offline-fallback-policy"], "confidence": "1", "estimated_cost": "0.002", "estimated_latency_ms": "60", "fallback_count": 1, "fallback_router_name": "offline-support-fallback-router", "policy_name": "offline-fallback-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-fallback-001", "target_kind": "agent", "target_name": "offline-fallback-agent"}

uv run pytest -q
97 passed in 0.80s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
```

남은 Volume 08 범위:

- Semantic/LLM Router와 Intent 분류
- escalation 및 Agent·Tool·Model 다단계 라우팅
- Router API 및 나머지 학습 장

다음 슬라이스:

- 외부 호출 없는 고정 semantic score fixture와 명시적 threshold를 갖는 Semantic Router를 추가하고, policy 경계를 통과하는 경로와 안전 실패를 검증합니다.

## 2026-08-11 — Tick 5: 고정 score fixture 기반 Semantic Router

완료한 범위:

- request ID별 모든 configured intent score를 명시하는 `SemanticIntentScore`/`SemanticScoreFixture` 계약을 추가했습니다. 이 slice는 embedding·LLM·API·네트워크를 호출하지 않습니다.
- 명시적 `minimum_similarity`를 적용하고 similarity → intent 이름 순으로 결정론적으로 선택하는 `SemanticRouter`를 추가했습니다.
- fixture가 없거나 모든 점수가 threshold 미만이면 각각 `NoSemanticScoreFixtureError`와 `NoConfidentSemanticRouteError`로 fail closed 하게 했습니다.
- 선택된 semantic intent capability를 기존 요청 capability에 합친 뒤 `PolicyRouter`에 전달하여 permission·상태·비용·지연 시간 제약을 우회하지 못하게 했습니다.
- 원문 없이 classifier 이름, intent, similarity와 policy 결정만 남기는 JSON 직렬화 가능 로그를 추가했습니다.
- 고정 fixture 예제, 계약 테스트, `05-semantic-routing.md` 학습 장을 추가했습니다.

검증 결과:

```text
uv run pytest tests/unit/test_volume08_semantic_router.py -q
8 passed in 0.07s

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py tests/unit/test_volume08_router_evaluation.py tests/unit/test_volume08_policy_fallback_router.py tests/unit/test_volume08_semantic_router.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 7 source files

uv run python examples/volume08/semantic_router.py
{"classifier_name": "offline-semantic-intent-router", "confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "70", "intent": "order_tracking", "policy_name": "offline-semantic-support-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-semantic-001", "semantic_similarity": "0.93", "target_kind": "agent", "target_name": "offline-order-agent"}

uv run pytest -q
105 passed in 0.92s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
```

남은 Volume 08 범위:

- LLM Router와 intent 분류
- escalation 및 Agent·Tool·Model 다단계 라우팅
- Router API 및 나머지 학습 장

다음 슬라이스:

- 고정 LLM classifier response fixture와 명시적 confidence threshold를 갖는 LLM Router를 추가하고, semantic·policy 경계를 우회하지 않는 경로와 안전 실패를 검증합니다.

## 2026-08-11 — Tick 6: 고정 response fixture 기반 LLM Router

완료한 범위:

- 요청 ID별 검토된 intent label과 `Decimal` confidence만 보관하는 `LLMClassifierResponseFixture`/`LLMRoute` 계약을 추가했습니다. 이 slice는 LLM·API·네트워크를 호출하지 않으며 prompt·raw response를 저장하지 않습니다.
- 명시적 `minimum_confidence`를 적용하고, fixture 누락은 `NoLLMClassifierResponseFixtureError`, threshold 미달은 `NoConfidentLLMRouteError`로 fail closed 하게 했습니다.
- fixture intent가 configured route에 속하는지, fixture request ID가 유일한지 검증해 모호하거나 알려지지 않은 classifier 결과를 router 생성 시 거부했습니다.
- 선택된 LLM intent capability를 기존 요청 capability에 합친 뒤 `PolicyRouter`에 전달하여 permission·상태·비용·지연 시간 제약을 우회하지 못하게 했습니다.
- 원문·prompt·raw output 없이 classifier 이름, intent, classifier confidence와 policy 결정만 남기는 JSON 직렬화 가능 로그를 추가했습니다.
- 고정 fixture 예제, 계약 테스트, `06-llm-routing.md` 학습 장을 추가했습니다.

검증 결과:

```text
uv run pytest tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py tests/unit/test_volume08_router_evaluation.py tests/unit/test_volume08_policy_fallback_router.py tests/unit/test_volume08_semantic_router.py tests/unit/test_volume08_llm_router.py -q
53 passed in 0.19s

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py tests/unit/test_volume08_router_evaluation.py tests/unit/test_volume08_policy_fallback_router.py tests/unit/test_volume08_semantic_router.py tests/unit/test_volume08_llm_router.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 8 source files

uv run python examples/volume08/llm_router.py
{"classifier_name": "offline-llm-intent-router", "confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "70", "intent": "order_tracking", "llm_classifier_confidence": "0.92", "policy_name": "offline-llm-support-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-llm-001", "target_kind": "agent", "target_name": "offline-order-agent"}

uv run pytest -q
114 passed in 1.03s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
```

남은 Volume 08 범위:

- escalation 및 Agent·Tool·Model 다단계 라우팅
- Router API 및 나머지 학습 장

다음 슬라이스:

- 고정 escalation fixture와 명시적 escalation budget을 갖는 다단계 Agent·Tool·Model Router를 추가하고, 모든 단계가 policy 제약을 재검증하는 안전 실패를 검증합니다.

## 2026-08-11 — Tick 7: 고정 escalation fixture 기반 Agent·Tool·Model 다단계 Router

완료한 범위:

- 요청 ID별 stage 순서만 보관하는 `EscalationFixture`와 stage의 대상 유형·허용 대상을 검증하는 `RoutingStage`를 추가했습니다. 이 slice는 Agent·Tool·Model·API·네트워크를 호출하지 않습니다.
- `MultiStageEscalationRouter`가 Agent → Tool → Model의 fixture 순서를 따르고, 첫 stage 뒤 최대 시도 수를 명시적 정수 `escalation_budget`으로 제한하게 했습니다.
- 각 stage에서 원래 capability·허용 대상·비용·지연 시간 제약을 보존한 뒤 stage 대상 집합과 교집합을 만들고 `PolicyRouter`에 재검증하게 했습니다. 따라서 escalation은 permission·cost·latency·health 제약을 우회하지 못합니다.
- fixture 누락은 `NoEscalationFixtureError`, budget 안의 모든 stage 실패는 실제 시도 stage만 보관하는 `EscalationRouteExhaustedError`로 fail closed 하게 했습니다.
- stage의 policy 소속, Agent·Tool·Model 유형 일치, stage/fixture의 중복 없는 계약을 생성 시 검증했습니다. 성공·실패 감사 로그는 사용자 원문 없이 JSON 직렬화 가능합니다.
- 고정 fixture 예제, 계약 테스트, `07-multi-stage-escalation.md` 학습 장을 추가했습니다.

검증 결과:

```text
uv run pytest tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py tests/unit/test_volume08_router_evaluation.py tests/unit/test_volume08_policy_fallback_router.py tests/unit/test_volume08_semantic_router.py tests/unit/test_volume08_llm_router.py tests/unit/test_volume08_multi_stage_escalation_router.py -q
61 passed in 0.30s

uv run ruff format --check src/ai_platform/router/escalation.py src/ai_platform/router/policy.py src/ai_platform/router/__init__.py examples/volume08/multi_stage_escalation_router.py tests/unit/test_volume08_multi_stage_escalation_router.py
5 files already formatted

uv run ruff check src/ai_platform/router/escalation.py src/ai_platform/router/policy.py src/ai_platform/router/__init__.py examples/volume08/multi_stage_escalation_router.py tests/unit/test_volume08_multi_stage_escalation_router.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 9 source files

uv run python examples/volume08/multi_stage_escalation_router.py
{"attempted_stage_names": ["agent-stage", "tool-stage", "model-stage"], "confidence": "1", "escalation_count": 2, "estimated_cost": "0.004", "estimated_latency_ms": "90", "multi_stage_router_name": "offline-support-escalation-router", "policy_name": "offline-model-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-escalation-001", "stage_name": "model-stage", "stage_target_kind": "model", "target_kind": "model", "target_name": "offline-summary-model"}

uv run pytest -q
122 passed in 0.88s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
```

남은 Volume 08 범위:

- Router API 구현 및 API 학습 장

다음 슬라이스:

- 고정 policy/router fixture를 HTTP 요청·응답 계약으로만 변환하는 로컬 Router API를 추가하고, API 입력 검증·안전 실패·원문 없는 결정 로그를 검증합니다.

## 2026-08-11 — Tick 8: 고정 PolicyRouter 기반 로컬 Router API 계약

완료한 범위:

- strict Pydantic JSON schema를 사용하는 `RouterAPI`/`RouterAPIResponse`를 추가했습니다. 이 adapter는 실제 HTTP 서버·API·네트워크를 실행하지 않고 `POST /routes`의 body·status code·JSON body 계약만 표현합니다.
- `maximum_cost`는 JSON number가 아닌 문자열만 받아 `Decimal`로 변환하고, 알 수 없는 필드·비 JSON 타입·기존 `RoutingRequest` 정책 제한 위반을 `400 INVALID_ROUTING_REQUEST`로 fail closed 하게 했습니다.
- 유효 요청은 기존 `PolicyRouter`에 한 번만 위임합니다. 따라서 API 계층도 capability·허용 대상·비용·지연 시간·health 제약을 재구현하거나 완화하지 않습니다.
- policy상 대상이 없으면 임의 fallback 없이 `422 NO_ELIGIBLE_ROUTE`를 반환합니다. 성공과 두 실패 body 모두 원문·validation detail·알 수 없는 입력 값을 포함하지 않습니다.
- 고정 policy fixture 예제, 입력 검증·안전 실패·privacy·JSON 직렬화 계약 테스트, `08-router-api.md` 학습 장을 추가했습니다.

검증 결과:

```text
uv run ruff format --check src/ai_platform/router/api.py src/ai_platform/router/__init__.py examples/volume08/router_api.py tests/unit/test_volume08_router_api.py
4 files already formatted

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_policy_router.py tests/unit/test_volume08_keyword_router.py tests/unit/test_volume08_router_evaluation.py tests/unit/test_volume08_policy_fallback_router.py tests/unit/test_volume08_semantic_router.py tests/unit/test_volume08_llm_router.py tests/unit/test_volume08_multi_stage_escalation_router.py tests/unit/test_volume08_router_api.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 10 source files

uv run pytest tests/unit/test_volume08_router_api.py -q
5 passed in 0.27s

uv run python examples/volume08/router_api.py
{"body": {"decision": {"confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "70", "policy_name": "offline-router-api-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-api-001", "target_kind": "agent", "target_name": "offline-order-agent"}, "outcome": "routed"}, "status_code": 200}

uv run pytest -q
127 passed in 1.14s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
```

PRD DoD 상태:

- `VOLUME08_COMPLETE=true`는 추가하지 않았습니다. Volume별 미니 프로젝트, 학습자 체크리스트, 다음 Volume 인계 정리, Glossary 항목이 아직 PRD Volume DoD를 충족하지 않습니다. 이 tick의 허용 범위에는 공유 `docs/glossary.md` 수정도 포함되지 않습니다.

다음 슬라이스:

- 고정 policy·keyword·semantic·LLM·fallback·escalation fixture를 한 요청 집합에 조합하는 Volume 08 미니 프로젝트와 Volume 범위 학습자 체크리스트를 추가하고, 전체 로컬 회귀를 검증합니다.

## 2026-08-11 — Tick 9: 고정 fixture Router 미니 프로젝트와 학습자 체크리스트

완료한 범위:

- `RouterMiniProject`와 `build_router_mini_project()`를 추가하여 Policy, Keyword, Semantic, LLM, fallback, Agent·Tool·Model escalation, strict Router API를 하나의 고정 request ID 집합으로 조합했습니다. 모든 path는 live Agent·Tool·Model·LLM·embedding·HTTP API·네트워크를 호출하지 않습니다.
- Keyword·Semantic·LLM path는 분류 결과 capability를 policy에 재검증하고, fallback은 unhealthy primary 뒤 한 번의 fallback만 시도하며, escalation은 허용된 Model로 좁혀진 원래 정책 제약을 보존한 채 Agent → Tool → Model fixture 순서를 따릅니다.
- `router_mini_project.py` 예제와 조합 계약 테스트를 추가했습니다. 테스트는 일곱 경로의 예상 target·intent·attempt 순서·API 응답, 두 실행 간 결정론성, JSON 직렬화, 사용자 원문 비노출을 검증합니다.
- `09-router-mini-project.md`에 조합 구조, 실행 절차, 오류 해결, 응용 과제, Volume 09 workflow 인계 계약을 작성하고, `checklist.md`에 Volume 범위 학습자 체크리스트를 추가했습니다.
- README의 전체 재실행 명령을 18개로 확장하고 미니 프로젝트·체크리스트 링크를 연결했습니다.

검증 결과:

```text
uv run ruff format --check src/ai_platform/router/mini_project.py src/ai_platform/router/__init__.py examples/volume08/router_mini_project.py tests/unit/test_volume08_router_mini_project.py
4 files already formatted

uv run ruff check .
All checks passed!

uv run mypy src
Success: no issues found in 18 source files

uv run pytest tests/unit/test_volume08_router_mini_project.py -q
2 passed in 0.29s

uv run python examples/volume08/router_mini_project.py
일곱 경로(`policy`, `keyword`, `semantic`, `llm`, `fallback`, `escalation`, `api`)의 JSON report 출력; 예상 target과 attempt 순서는 아래 조합 테스트에서 검증

uv run pytest -q
129 passed in 1.22s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과

uv run python scripts/check_secrets.py
비밀값 검사 통과
```

PRD DoD 상태:

- Volume별 미니 프로젝트, 학습자 체크리스트, 다음 Volume 인계 정리는 완료했습니다.
- 공유 `docs/glossary.md`의 Volume 08 주요 용어 추가는 아직 남았습니다. 사용자 지시의 변경 허용 범위가 `docs/volume08-router/`, `examples/volume08/`, Volume 08 tests, `src/ai_platform/router/`로 한정되어 공유 Glossary는 수정하지 않았습니다.
- 따라서 `VOLUME08_COMPLETE=true`는 추가하지 않았고 cron self-pause도 수행하지 않았습니다.

다음 슬라이스:

- 허용 범위가 공유 Glossary까지 확장되면 Volume 08 Router 주요 용어를 `docs/glossary.md`에 추가하고, 전체 Volume DoD를 다시 검증한 뒤에만 완료 marker와 self-pause를 처리합니다.

## 2026-08-11 — Tick 10: 명시적 capability Rule Router와 미니 프로젝트 조합

완료한 범위:

- PRD의 Rule-based Router 필수 실습을 명시적으로 충족하는 `RuleRoute`/`RuleRouter`를 추가했습니다. rule은 신뢰된 request capability가 일치할 때만 추가 capability를 요구하며, 최종 대상 선택은 항상 `PolicyRouter`에 재검증을 위임합니다.
- 일치 rule은 priority 내림차순 → rule 이름 오름차순으로 결정론적으로 선택합니다. rule 미일치는 `NoMatchingRuleRouteError`, policy상 대상 부재는 기존 `NoEligibleRouteError`로 fail closed 합니다.
- 고정 billing fixture 예제와 priority·동점 해소·정책 allowlist 거부·안전 실패·JSON·원문 비노출 계약 테스트를 추가했습니다. live Agent·Tool·Model·LLM·API·네트워크 호출은 하지 않습니다.
- Rule path를 `RouterMiniProject`에 추가해 고정 request ID 여덟 개의 조합 report에서 rule target과 privacy를 함께 회귀 검증했습니다.
- `10-rule-routing.md` 학습 장, README 학습 순서·스무 개 재실행 명령, 학습자 체크리스트, 미니 프로젝트 문서를 갱신했습니다.

검증 결과:

```text
uv run pytest tests/unit/test_volume08_*.py -q
75 passed in 0.84s

uv run ruff format --check src/ai_platform/router/rule.py src/ai_platform/router/mini_project.py src/ai_platform/router/__init__.py examples/volume08/rule_router.py tests/unit/test_volume08_rule_router.py tests/unit/test_volume08_router_mini_project.py
6 files already formatted

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 12 source files

uv run python examples/volume08/rule_router.py
{"confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "70", "policy_name": "offline-rule-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-rule-001", "rule_name": "billing-support", "rule_router_name": "offline-rule-router", "target_kind": "agent", "target_name": "offline-billing-agent"}

uv run pytest -q
136 passed in 1.30s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
```

PRD DoD 상태:

- Volume 08의 명시적 Rule-based Router 필수 실습, Router 미니 프로젝트, 학습자 체크리스트, 다음 Volume 인계 문서는 완료했습니다.
- 공유 `docs/glossary.md`의 Volume 08 주요 용어 추가만 남았습니다. 사용자 지시의 변경 허용 범위가 `docs/volume08-router/`, `examples/volume08/`, Volume 08 tests, `src/ai_platform/router/`로 한정되어 공유 Glossary는 수정하지 않았습니다.
- 따라서 `VOLUME08_COMPLETE=true`는 추가하지 않았고 cron self-pause도 수행하지 않았습니다.

다음 슬라이스:

- 허용 범위가 공유 Glossary까지 확장되면 Volume 08 Router 주요 용어를 `docs/glossary.md`에 추가하고, 전체 Volume DoD를 다시 검증한 뒤에만 완료 marker와 self-pause를 처리합니다.

## 2026-08-11 — Tick 11: Volume 08 범위 formatting 회귀 정리와 완료 경계 재검증

완료한 범위:

- Volume 08 전용 source, example, unit test 전체에 `ruff format`을 적용했습니다. 이전 slice에서 개별 신규 파일은 format 검사를 통과했지만, 범위 전체 검사에서는 기존 18개 파일이 현재 formatter 규칙과 불일치했습니다.
- 형식 변경만 적용했으며 Router 정책, 고정 fixture, 결정 결과, 외부 호출 경계는 변경하지 않았습니다.
- 고정 fixture 미니 프로젝트가 policy, rule, keyword, semantic, LLM, fallback, escalation, API 여덟 경로를 계속 결정론적으로 출력하고 원문을 report에 포함하지 않음을 재실행으로 확인했습니다.

검증 결과:

```text
uv run ruff format --check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
32 files already formatted

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 12 source files

uv run pytest tests/unit/test_volume08_*.py -q
75 passed in 0.59s

uv run pytest -q
136 passed in 1.13s

uv run python examples/volume08/router_mini_project.py
고정 여덟 경로의 JSON report 출력; 모든 예상 target·intent·attempt 순서는 조합 테스트에서 검증

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
```

PRD DoD 상태:

- 허용된 Volume 08 Router 범위의 구현·예제·테스트·학습자 체크리스트·미니 프로젝트·문서 검증은 모두 재검증했습니다.
- 공유 `docs/glossary.md`에 Volume 08 핵심 용어를 추가하는 PRD 범위는 여전히 남아 있습니다. 현재 사용자 지시는 해당 공유 문서 변경을 금지하므로 이 tick에서는 수정하지 않았습니다.
- 따라서 `VOLUME08_COMPLETE=true`를 추가하거나 cron을 self-pause하지 않았습니다.

## 2026-08-11 — Tick 12: 허용 범위 완료 경계 재검증

완료한 범위:

- 허용된 Volume 08 Router source, 예제, 단위 테스트가 현재 formatter·lint·정적 타입 검사와 Volume 전용 회귀를 계속 통과함을 재검증했습니다.
- 고정 fixture 미니 프로젝트를 재실행하여 policy, rule, keyword, semantic, LLM, fallback, Agent·Tool·Model escalation, strict API의 여덟 경로가 외부 호출 없이 JSON 결정 report를 생성함을 확인했습니다.
- 전체 로컬 회귀와 문서·링크·코드 블록·비밀값 검사를 재실행했습니다. 정책 경계, 결정론성, 원문 비노출 계약에 대한 source 변경은 필요하지 않았습니다.

검증 결과:

```text
uv run ruff format --check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
32 files already formatted

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 12 source files

uv run pytest tests/unit/test_volume08_*.py -q
75 passed in 0.71s

uv run python examples/volume08/router_mini_project.py
고정 여덟 경로의 JSON report 출력; policy, rule, keyword, semantic, LLM, fallback, escalation, API 모두 결정론적으로 성공

uv run pytest -q
136 passed in 1.07s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
```

PRD DoD 상태:

- 허용된 Volume 08 Router 범위의 구현, 예제, 테스트, 미니 프로젝트, 학습자 체크리스트, 다음 Volume 인계 문서는 검증 완료 상태입니다.
- 공유 `docs/glossary.md`에 Volume 08 핵심 용어를 추가하는 PRD 항목은 현재 사용자 지시의 변경 허용 범위 밖입니다. 해당 파일은 수정하지 않았습니다.
- 따라서 PRD DoD가 아직 완전하지 않아 `VOLUME08_COMPLETE=true`를 추가하거나 cron을 self-pause하지 않았습니다.

## 2026-08-11 — Tick 13: Router 감사 record allowlist와 원문 비노출 회귀

완료한 범위:

- `validate_router_audit_record()`와 `UnsafeRouterAuditRecordError`를 추가했습니다. validator는 결정·API audit record의 재귀 field allowlist, JSON 직렬화 가능 여부, 해당 요청 원문의 부분 문자열 비노출을 확인합니다.
- `RouterMiniProject.run()`의 policy, rule, keyword, semantic, LLM, fallback, escalation, API 여덟 결과를 반환 직전에 각 요청 원문과 함께 validator로 확인하게 했습니다. 따라서 새 report field나 원문 반사값은 미니 프로젝트 경계에서 fail closed 합니다.
- allowlist 밖 field, 허용 field 안의 원문, non-JSON 값, 잘못된 sensitive value 입력과 안전한 중첩 Router API body를 고정 fixture unit test로 검증했습니다.
- 미니 프로젝트 문서·README·학습자 체크리스트에 audit 검사 명령, 오류 해결, field 확장 시 검토 경계를 추가했습니다. 외부 Agent·Tool·Model·LLM·embedding·HTTP API·네트워크 호출은 하지 않았습니다.

검증 결과:

```text
uv run ruff format --check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
34 files already formatted

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 13 source files

uv run pytest tests/unit/test_volume08_*.py -q
80 passed in 0.51s

uv run pytest -q
141 passed in 1.10s

uv run python examples/volume08/router_mini_project.py
고정 여덟 경로의 JSON report 출력; audit allowlist와 각 fixture 원문 비노출 검사를 통과

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
```

PRD DoD 상태:

- 허용된 Volume 08 Router 범위의 구현, 예제, 테스트, 미니 프로젝트, 학습자 체크리스트, 다음 Volume 인계 문서는 검증 완료 상태입니다.
- 공유 `docs/glossary.md`에 Volume 08 핵심 용어를 추가하는 PRD 항목은 현재 사용자 지시의 변경 허용 범위 밖입니다. 해당 파일은 수정하지 않았습니다.
- 따라서 PRD DoD가 아직 완전하지 않아 `VOLUME08_COMPLETE=true`를 추가하거나 cron을 self-pause하지 않았습니다.

## 2026-08-11 — Tick 14: strict JSON Router audit 경계

완료한 범위:

- `validate_router_audit_record()`의 JSON 검증을 `allow_nan=False` strict mode로 강화했습니다. 이에 따라 Python 기본 encoder가 관대하게 출력할 수 있는 `NaN`, `Infinity`, `-Infinity`를 감사 record에서 fail closed 합니다.
- 고정 audit fixture 테스트가 `Decimal` 같은 JSON 외 객체뿐 아니라 세 가지 비유한 float 값을 모두 `UnsafeRouterAuditRecordError`로 거부함을 검증합니다.
- 미니 프로젝트 문서와 학습자 체크리스트에 strict JSON 경계, 오류 해결 방법, 완료 조건을 반영했습니다. Router fixture, 정책 선택, 외부 호출 경계에는 변경이 없습니다.

검증 결과:

```text
uv run ruff format --check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
34 files already formatted

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 13 source files

uv run pytest tests/unit/test_volume08_router_audit.py tests/unit/test_volume08_router_mini_project.py -q
7 passed in 0.65s

uv run pytest tests/unit/test_volume08_*.py -q
80 passed in 0.78s

uv run pytest -q
141 passed in 1.99s

uv run python examples/volume08/router_mini_project.py
고정 여덟 경로의 strict JSON audit report 출력; 외부 호출 없음

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
```

PRD DoD 상태:

- 허용된 Volume 08 Router 범위의 구현, 예제, 테스트, 미니 프로젝트, 학습자 체크리스트, 다음 Volume 인계 문서는 검증 완료 상태입니다.
- 공유 `docs/glossary.md`에 Volume 08 핵심 용어를 추가하는 PRD 항목은 현재 사용자 지시의 변경 허용 범위 밖입니다. 해당 파일은 수정하지 않았습니다.
- 따라서 PRD DoD가 아직 완전하지 않아 `VOLUME08_COMPLETE=true`를 추가하거나 cron을 self-pause하지 않았습니다.

## 2026-08-11 — Tick 15: 고정 미니 프로젝트 audit report 완전성 경계

완료한 범위:

- `validate_router_audit_report()`를 추가해 미니 프로젝트 aggregate report가 Policy, Rule, Keyword, Semantic, LLM, fallback, escalation, API의 고정 여덟 경로를 빠짐없이, 추가 경로 없이 포함하는지 fail closed 하게 했습니다.
- 각 경로의 record는 기존 strict JSON field allowlist 검사를 재사용하고, 해당 경로의 고정 request 원문만으로 부분 문자열 비노출을 검증합니다. 따라서 report 조립 단계에서 경로가 누락되거나 새 경로·원문이 섞여도 반환 전에 거부됩니다.
- 정상 report, 경로 누락·추가, record가 아닌 값, 경로별 원문 누출의 결정론적 fixture 회귀 테스트를 추가했습니다. 미니 프로젝트는 외부 Agent·Tool·Model·LLM·embedding·HTTP API·네트워크를 호출하지 않습니다.
- 미니 프로젝트 문서와 학습자 체크리스트를 aggregate report의 완전성 계약에 맞춰 갱신했습니다.

검증 결과:

```text
uv run ruff format --check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
34 files already formatted

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 13 source files

uv run pytest tests/unit/test_volume08_router_audit.py tests/unit/test_volume08_router_mini_project.py -q
9 passed in 0.59s

uv run python examples/volume08/router_mini_project.py
고정 여덟 경로의 strict JSON audit report 출력; aggregate 경로 완전성 및 원문 비노출 검사를 통과, 외부 호출 없음

uv run pytest tests/unit/test_volume08_*.py -q
82 passed in 0.54s

uv run pytest -q
143 passed in 1.28s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
```

PRD DoD 상태:

- 허용된 Volume 08 Router 범위의 구현, 예제, 테스트, 미니 프로젝트, 학습자 체크리스트, 다음 Volume 인계 문서는 검증 완료 상태입니다.
- 공유 `docs/glossary.md`에 Volume 08 핵심 용어를 추가하는 PRD 항목은 현재 사용자 지시의 변경 허용 범위 밖입니다. 해당 파일은 수정하지 않았습니다.
- 따라서 PRD DoD가 아직 완전하지 않아 `VOLUME08_COMPLETE=true`를 추가하거나 cron을 self-pause하지 않았습니다.

## 2026-08-11 — Tick 16: canonical strict JSON Router audit export 경계

완료한 범위:

- `serialize_router_audit_report()`를 추가해 고정 여덟 경로의 aggregate report를 export 직전에 다시 검증한 뒤, `allow_nan=False`, key 정렬, compact separator를 적용한 결정론적 strict JSON 한 줄만 반환하게 했습니다.
- `RouterMiniProject.render_audit_report()`와 미니 프로젝트 예제가 이 export 경계를 사용하게 했습니다. 따라서 검증이 끝난 mutable report가 출력 전에 변경되더라도 public serializer 경계에서 field allowlist·경로 완전성·경로별 원문 비노출을 다시 fail closed 검증합니다.
- 고정 fixture 계약 테스트로 canonical serialization의 두 번 실행 동일성, 표준 strict JSON 출력 일치, export 전 삽입된 unsafe field 거부를 검증했습니다.
- 미니 프로젝트 문서, README, 학습자 체크리스트에 canonical export와 재검증 경계를 반영했습니다. live Agent·Tool·Model·LLM·embedding·HTTP API·네트워크 호출은 하지 않았습니다.

검증 결과:

```text
uv run ruff format --check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
34 files already formatted

uv run ruff check src/ai_platform/router examples/volume08 tests/unit/test_volume08_*.py
All checks passed!

uv run mypy src/ai_platform/router
Success: no issues found in 13 source files

uv run pytest tests/unit/test_volume08_router_audit.py tests/unit/test_volume08_router_mini_project.py -q
11 passed in 0.74s

uv run pytest tests/unit/test_volume08_*.py -q
84 passed in 0.59s

uv run python examples/volume08/router_mini_project.py
고정 여덟 경로의 canonical strict JSON audit report 출력; export 직전 재검증 통과, 외부 호출 없음

uv run pytest -q
145 passed in 1.17s

uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
```

PRD DoD 상태:

- 허용된 Volume 08 Router 범위의 구현, 예제, 테스트, 미니 프로젝트, 학습자 체크리스트, 다음 Volume 인계 문서는 검증 완료 상태입니다.
- PRD Volume DoD의 공유 `docs/glossary.md` 핵심 용어 항목은 현재 사용자 지시의 변경 허용 범위 밖입니다. 해당 파일은 수정하지 않았습니다.
- 따라서 PRD DoD가 아직 완전하지 않아 `VOLUME08_COMPLETE=true`를 추가하거나 cron을 self-pause하지 않았습니다.
