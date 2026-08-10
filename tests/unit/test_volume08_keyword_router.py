"""Volume 08 keyword Router의 외부 호출 없는 결정론적 계약 테스트."""
import json
from decimal import Decimal

import pytest

from ai_platform.router import (
    KeywordRoute,
    KeywordRouter,
    NoConfidentKeywordRouteError,
    NoEligibleRouteError,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
)


def _target(
    name: str,
    capabilities: frozenset[str],
    *,
    cost: str = "0.001",
    latency_ms: int = 50,
) -> RouteTarget:
    return RouteTarget(
        name=name,
        kind=RouteTargetKind.AGENT,
        capabilities=capabilities,
        estimated_cost=Decimal(cost),
        estimated_latency_ms=latency_ms,
    )


def _router(*, minimum_confidence: str = "0.80") -> KeywordRouter:
    return KeywordRouter(
        name="fixed-keyword-router",
        policy_router=PolicyRouter(
            name="fixed-policy",
            targets=(
                _target("cheap-general", frozenset({"respond"}), latency_ms=10),
                _target(
                    "order-agent",
                    frozenset({"lookup_order", "respond"}),
                    cost="0.003",
                    latency_ms=70,
                ),
                _target(
                    "refund-agent",
                    frozenset({"issue_refund", "respond"}),
                    cost="0.004",
                    latency_ms=80,
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
        minimum_confidence=Decimal(minimum_confidence),
    )


def test_keyword_router_casefolds_tokens_and_routes_intent_through_policy_constraints() -> None:
    decision = _router().route(
        RoutingRequest(
            request_id="keyword-001",
            text="ORDER tracking, please.",
            requirements=RoutingRequirements(
                maximum_cost=Decimal("0.005"),
                maximum_latency_ms=100,
                permitted_target_names=frozenset({"order-agent"}),
            ),
        )
    )

    assert decision.intent == "order_tracking"
    assert decision.matched_keywords == ("order", "tracking")
    assert decision.confidence == Decimal("0.90")
    assert decision.target.name == "order-agent"


def test_keyword_router_prefers_confidence_then_keyword_match_count() -> None:
    policy_router = PolicyRouter(
        name="priority-policy",
        targets=(_target("shared-agent", frozenset({"respond"})),),
    )
    router = KeywordRouter(
        name="priority-router",
        policy_router=policy_router,
        routes=(
            KeywordRoute(
                intent="high_confidence",
                keywords=frozenset({"urgent"}),
                required_capabilities=frozenset({"respond"}),
                confidence=Decimal("0.91"),
            ),
            KeywordRoute(
                intent="more_keyword_matches",
                keywords=frozenset({"refund", "urgent"}),
                required_capabilities=frozenset({"respond"}),
                confidence=Decimal("0.90"),
            ),
        ),
        minimum_confidence=Decimal("0.80"),
    )

    decision = router.route(RoutingRequest(request_id="keyword-priority-001", text="urgent refund"))

    assert decision.intent == "high_confidence"

    equal_confidence_router = KeywordRouter(
        name="match-count-router",
        policy_router=policy_router,
        routes=(
            KeywordRoute(
                intent="one_match",
                keywords=frozenset({"urgent"}),
                required_capabilities=frozenset({"respond"}),
                confidence=Decimal("0.90"),
            ),
            KeywordRoute(
                intent="two_matches",
                keywords=frozenset({"refund", "urgent"}),
                required_capabilities=frozenset({"respond"}),
                confidence=Decimal("0.90"),
            ),
        ),
        minimum_confidence=Decimal("0.80"),
    )

    equal_confidence_decision = equal_confidence_router.route(
        RoutingRequest(request_id="keyword-priority-002", text="urgent refund")
    )

    assert equal_confidence_decision.intent == "two_matches"


def test_keyword_router_uses_deterministic_confidence_match_count_and_intent_order() -> None:
    policy_router = PolicyRouter(
        name="tie-policy",
        targets=(_target("shared-agent", frozenset({"a", "b", "respond"})),),
    )
    router = KeywordRouter(
        name="tie-router",
        policy_router=policy_router,
        routes=(
            KeywordRoute(
                intent="zeta",
                keywords=frozenset({"zeta"}),
                required_capabilities=frozenset({"respond"}),
                confidence=Decimal("0.90"),
            ),
            KeywordRoute(
                intent="alpha",
                keywords=frozenset({"alpha"}),
                required_capabilities=frozenset({"respond"}),
                confidence=Decimal("0.90"),
            ),
        ),
        minimum_confidence=Decimal("0.80"),
    )

    decision = router.route(RoutingRequest(request_id="keyword-002", text="zeta alpha"))

    assert decision.intent == "alpha"


def test_keyword_router_rejects_low_confidence_and_substring_only_matches() -> None:
    router = _router(minimum_confidence="0.95")

    with pytest.raises(NoConfidentKeywordRouteError, match="confidence threshold"):
        router.route(RoutingRequest(request_id="keyword-003", text="refund please"))

    with pytest.raises(NoConfidentKeywordRouteError, match="confidence threshold"):
        _router().route(RoutingRequest(request_id="keyword-004", text="refunding please"))


def test_keyword_router_does_not_bypass_policy_permissions_or_capability_requirements() -> None:
    request = RoutingRequest(
        request_id="keyword-005",
        text="refund please",
        requirements=RoutingRequirements(permitted_target_names=frozenset({"cheap-general"})),
    )

    with pytest.raises(NoEligibleRouteError, match="no healthy target"):
        _router().route(request)


def test_keyword_decision_log_is_json_serializable_and_omits_request_text() -> None:
    request = RoutingRequest(request_id="keyword-006", text="refund my secret")

    record = _router().route(request).as_log_record()

    assert record["classifier_name"] == "fixed-keyword-router"
    assert record["intent"] == "refund_request"
    assert record["classifier_confidence"] == "0.85"
    assert record["matched_keywords"] == ["refund"]
    assert request.text not in json.dumps(record)
    json.dumps(record)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: KeywordRoute(
            intent="bad phrase",
            keywords=frozenset({"two words"}),
            required_capabilities=frozenset({"respond"}),
            confidence=Decimal("0.8"),
        ),
        lambda: KeywordRoute(
            intent="bad confidence",
            keywords=frozenset({"keyword"}),
            required_capabilities=frozenset({"respond"}),
            confidence=Decimal("1.01"),
        ),
        lambda: KeywordRouter(
            name="bad threshold",
            policy_router=PolicyRouter(
                name="single-policy",
                targets=(_target("single", frozenset({"respond"})),),
            ),
            routes=(
                KeywordRoute(
                    intent="single",
                    keywords=frozenset({"single"}),
                    required_capabilities=frozenset({"respond"}),
                    confidence=Decimal("0.8"),
                ),
            ),
            minimum_confidence=Decimal("NaN"),
        ),
    ],
)
def test_keyword_router_rejects_ambiguous_or_invalid_fixture_values(factory: object) -> None:
    with pytest.raises(RoutingConfigurationError):
        factory()  # type: ignore[operator]