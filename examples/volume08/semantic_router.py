"""고정 semantic score fixture로 정책 경계를 지키는 Volume 08 예제."""

from __future__ import annotations

import json
from decimal import Decimal

from ai_platform.router import (
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingRequest,
    RoutingRequirements,
    SemanticIntentScore,
    SemanticRoute,
    SemanticRouter,
    SemanticScoreFixture,
)


def build_router() -> SemanticRouter:
    """외부 embedding 없이 고정 score fixture와 지원 정책을 구성한다."""
    return SemanticRouter(
        name="offline-semantic-intent-router",
        policy_router=PolicyRouter(
            name="offline-semantic-support-policy",
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
            SemanticRoute(
                intent="order_tracking",
                required_capabilities=frozenset({"lookup_order", "respond"}),
            ),
            SemanticRoute(
                intent="refund_request",
                required_capabilities=frozenset({"issue_refund", "respond"}),
            ),
        ),
        score_fixtures=(
            SemanticScoreFixture(
                request_id="lesson-08-semantic-001",
                intent_scores=(
                    SemanticIntentScore("order_tracking", Decimal("0.93")),
                    SemanticIntentScore("refund_request", Decimal("0.18")),
                ),
            ),
        ),
        minimum_similarity=Decimal("0.80"),
    )


def main() -> None:
    """semantic route 성공의 원문 없는 감사 로그 한 줄을 출력한다."""
    decision = build_router().route(
        RoutingRequest(
            request_id="lesson-08-semantic-001",
            text="private semantic support request",
            requirements=RoutingRequirements(
                maximum_cost=Decimal("0.005"),
                permitted_target_names=frozenset({"offline-order-agent"}),
            ),
        )
    )
    print(json.dumps(decision.as_log_record(), sort_keys=True))


if __name__ == "__main__":
    main()
