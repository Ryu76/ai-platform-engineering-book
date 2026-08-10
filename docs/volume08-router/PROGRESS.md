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
