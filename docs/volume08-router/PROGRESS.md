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
