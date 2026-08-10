"""고정 dataset으로 Keyword Router accuracy와 안전 실패를 측정하는 Volume 08 예제."""
from __future__ import annotations

import json
from decimal import Decimal

from ai_platform.router import (
    KeywordRoute,
    KeywordRouter,
    KeywordRoutingEvaluationCase,
    KeywordRoutingExpectation,
    KeywordRoutingOutcome,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingRequest,
    RoutingRequirements,
    evaluate_keyword_router,
)


def build_fixture_router() -> KeywordRouter:
    """외부 모델·API 없이 고정 intent와 대상 fixture를 구성한다."""
    return KeywordRouter(
        name="offline-evaluation-keyword-router",
        policy_router=PolicyRouter(
            name="offline-evaluation-policy",
            targets=(
                RouteTarget(
                    name="general-agent",
                    kind=RouteTargetKind.AGENT,
                    capabilities=frozenset({"respond"}),
                    estimated_cost=Decimal("0.001"),
                    estimated_latency_ms=40,
                ),
                RouteTarget(
                    name="order-support-agent",
                    kind=RouteTargetKind.AGENT,
                    capabilities=frozenset({"lookup_order", "respond"}),
                    estimated_cost=Decimal("0.003"),
                    estimated_latency_ms=80,
                ),
                RouteTarget(
                    name="refund-support-agent",
                    kind=RouteTargetKind.AGENT,
                    capabilities=frozenset({"issue_refund", "respond"}),
                    estimated_cost=Decimal("0.004"),
                    estimated_latency_ms=90,
                ),
            ),
        ),
        routes=(
            KeywordRoute(
                intent="order_tracking",
                keywords=frozenset({"order", "tracking"}),
                required_capabilities=frozenset({"lookup_order", "respond"}),
                confidence=Decimal("0.90"),
            ),
            KeywordRoute(
                intent="refund_request",
                keywords=frozenset({"refund"}),
                required_capabilities=frozenset({"issue_refund", "respond"}),
                confidence=Decimal("0.85"),
            ),
        ),
        minimum_confidence=Decimal("0.80"),
    )


def build_evaluation_dataset() -> tuple[KeywordRoutingEvaluationCase, ...]:
    """정상 route와 두 안전 실패를 포함하는 재현 가능한 dataset을 반환한다."""
    return (
        KeywordRoutingEvaluationCase(
            case_id="order-route",
            request=RoutingRequest(request_id="evaluation-001", text="ORDER tracking please"),
            expected=KeywordRoutingExpectation(
                outcome=KeywordRoutingOutcome.ROUTE,
                intent="order_tracking",
                target_name="order-support-agent",
            ),
        ),
        KeywordRoutingEvaluationCase(
            case_id="refund-route",
            request=RoutingRequest(request_id="evaluation-002", text="refund please"),
            expected=KeywordRoutingExpectation(
                outcome=KeywordRoutingOutcome.ROUTE,
                intent="refund_request",
                target_name="refund-support-agent",
            ),
        ),
        KeywordRoutingEvaluationCase(
            case_id="unknown-safe-failure",
            request=RoutingRequest(request_id="evaluation-003", text="hello there"),
            expected=KeywordRoutingExpectation(
                outcome=KeywordRoutingOutcome.NO_CONFIDENT_KEYWORD_ROUTE
            ),
        ),
        KeywordRoutingEvaluationCase(
            case_id="permission-safe-failure",
            request=RoutingRequest(
                request_id="evaluation-004",
                text="refund please",
                requirements=RoutingRequirements(
                    permitted_target_names=frozenset({"general-agent"})
                ),
            ),
            expected=KeywordRoutingExpectation(
                outcome=KeywordRoutingOutcome.NO_ELIGIBLE_POLICY_ROUTE
            ),
        ),
    )


def main() -> None:
    """accuracy gate를 통과한 원문 없는 평가 요약 JSON을 출력한다."""
    report = evaluate_keyword_router(build_fixture_router(), build_evaluation_dataset())
    report.require_minimum_accuracy(Decimal("1"))
    print(json.dumps(report.as_log_record(), sort_keys=True))


if __name__ == "__main__":
    main()
