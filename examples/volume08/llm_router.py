"""고정 LLM classifier response fixture로 정책 경계를 지키는 Volume 08 예제."""
from __future__ import annotations

import json
from decimal import Decimal

from ai_platform.router import (
    LLMClassifierResponseFixture,
    LLMRoute,
    LLMRouter,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingRequest,
    RoutingRequirements,
)


def build_router() -> LLMRouter:
    """외부 LLM 호출 없이 검토된 response fixture와 지원 정책을 구성한다."""
    return LLMRouter(
        name="offline-llm-intent-router",
        policy_router=PolicyRouter(
            name="offline-llm-support-policy",
            targets=(
                RouteTarget(
                    name="offline-refund-agent",
                    kind=RouteTargetKind.AGENT,
                    capabilities=frozenset({"issue_refund", "respond"}),
                    estimated_cost=Decimal("0.004"),
                    estimated_latency_ms=75,
                ),
                RouteTarget(
                    name="offline-order-agent",
                    kind=RouteTargetKind.AGENT,
                    capabilities=frozenset({"lookup_order", "respond"}),
                    estimated_cost=Decimal("0.003"),
                    estimated_latency_ms=70,
                ),
            ),
        ),
        routes=(
            LLMRoute(
                intent="order_tracking",
                required_capabilities=frozenset({"lookup_order", "respond"}),
            ),
            LLMRoute(
                intent="refund_request",
                required_capabilities=frozenset({"issue_refund", "respond"}),
            ),
        ),
        response_fixtures=(
            LLMClassifierResponseFixture(
                request_id="lesson-08-llm-001",
                intent="order_tracking",
                confidence=Decimal("0.92"),
            ),
        ),
        minimum_confidence=Decimal("0.80"),
    )


def main() -> None:
    """LLM route 성공의 원문 없는 감사 로그 한 줄을 출력한다."""
    decision = build_router().route(
        RoutingRequest(
            request_id="lesson-08-llm-001",
            text="private LLM classifier request",
            requirements=RoutingRequirements(
                maximum_cost=Decimal("0.005"),
                permitted_target_names=frozenset({"offline-order-agent"}),
            ),
        )
    )
    print(json.dumps(decision.as_log_record(), sort_keys=True))


if __name__ == "__main__":
    main()
