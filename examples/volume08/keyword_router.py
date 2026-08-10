"""고정 keyword fixture와 정책 제약을 결합하는 Volume 08 예제."""
from __future__ import annotations

import json
from decimal import Decimal

from ai_platform.router import (
    KeywordRoute,
    KeywordRouter,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingRequest,
    RoutingRequirements,
)


def build_fixture_router() -> KeywordRouter:
    """외부 모델이나 API 없이 동일한 intent·정책 fixture를 구성한다."""
    policy_router = PolicyRouter(
        name="offline-support-policy",
        targets=(
            RouteTarget(
                name="general-agent",
                kind=RouteTargetKind.AGENT,
                capabilities=frozenset({"summarize"}),
                estimated_cost=Decimal("0.001"),
                estimated_latency_ms=40,
            ),
            RouteTarget(
                name="order-support-agent",
                kind=RouteTargetKind.AGENT,
                capabilities=frozenset({"lookup_order", "respond_support"}),
                estimated_cost=Decimal("0.003"),
                estimated_latency_ms=80,
            ),
        ),
    )
    return KeywordRouter(
        name="offline-keyword-intent-router",
        policy_router=policy_router,
        routes=(
            KeywordRoute(
                intent="order_tracking",
                keywords=frozenset({"tracking", "order"}),
                required_capabilities=frozenset({"lookup_order", "respond_support"}),
                confidence=Decimal("0.90"),
            ),
        ),
        minimum_confidence=Decimal("0.80"),
    )


def main() -> None:
    """원문 없이 classifier 및 정책 결정을 단일 JSON 로그로 출력한다."""
    router = build_fixture_router()
    decision = router.route(
        RoutingRequest(
            request_id="lesson-08-keyword-001",
            text="Where is my ORDER tracking update?",
            requirements=RoutingRequirements(
                maximum_cost=Decimal("0.005"),
                maximum_latency_ms=100,
                permitted_target_names=frozenset({"order-support-agent"}),
            ),
        )
    )
    print(json.dumps(decision.as_log_record(), sort_keys=True))


if __name__ == "__main__":
    main()