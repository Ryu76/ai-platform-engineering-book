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
