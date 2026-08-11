"""Volume 08의 명시적 capability Rule Router 고정 fixture 예제."""

from __future__ import annotations

import json
from decimal import Decimal

from ai_platform.router import (
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingRequest,
    RoutingRequirements,
    RuleRoute,
    RuleRouter,
)


def main() -> None:
    """외부 API·네트워크 없이 billing rule과 policy 재검증 결과를 출력한다."""
    router = RuleRouter(
        name="offline-rule-router",
        policy_router=PolicyRouter(
            name="offline-rule-policy",
            targets=(
                RouteTarget(
                    name="offline-billing-agent",
                    kind=RouteTargetKind.AGENT,
                    capabilities=frozenset({"billing", "refund", "respond"}),
                    estimated_cost=Decimal("0.003"),
                    estimated_latency_ms=70,
                ),
            ),
        ),
        routes=(
            RuleRoute(
                name="billing-support",
                required_request_capabilities=frozenset({"billing"}),
                added_required_capabilities=frozenset({"refund", "respond"}),
                priority=10,
            ),
        ),
    )
    decision = router.route(
        RoutingRequest(
            request_id="lesson-08-rule-001",
            text="private billing support request",
            requirements=RoutingRequirements(
                required_capabilities=frozenset({"billing"}),
                maximum_cost=Decimal("0.004"),
                maximum_latency_ms=80,
                permitted_target_names=frozenset({"offline-billing-agent"}),
            ),
        )
    )
    print(json.dumps(decision.as_log_record(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
