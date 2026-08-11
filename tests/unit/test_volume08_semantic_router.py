"""Volume 08 Semantic Router의 외부 호출 없는 결정론적 계약 테스트."""

import json
from decimal import Decimal

import pytest

from ai_platform.router import (
    NoConfidentSemanticRouteError,
    NoEligibleRouteError,
    NoSemanticScoreFixtureError,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
    SemanticIntentScore,
    SemanticRoute,
    SemanticRouter,
    SemanticScoreFixture,
)


def _target(name: str, capabilities: frozenset[str]) -> RouteTarget:
    return RouteTarget(
        name=name,
        kind=RouteTargetKind.AGENT,
        capabilities=capabilities,
        estimated_cost=Decimal("0.003"),
        estimated_latency_ms=70,
    )


def _router(*, minimum_similarity: str = "0.80") -> SemanticRouter:
    return SemanticRouter(
        name="fixed-semantic-router",
        policy_router=PolicyRouter(
            name="fixed-semantic-policy",
            targets=(
                _target("general-agent", frozenset({"respond"})),
                _target("order-agent", frozenset({"lookup_order", "respond"})),
                _target("refund-agent", frozenset({"issue_refund", "respond"})),
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
                request_id="semantic-001",
                intent_scores=(
                    SemanticIntentScore("order_tracking", Decimal("0.91")),
                    SemanticIntentScore("refund_request", Decimal("0.20")),
                ),
            ),
            SemanticScoreFixture(
                request_id="semantic-tie-001",
                intent_scores=(
                    SemanticIntentScore("order_tracking", Decimal("0.90")),
                    SemanticIntentScore("refund_request", Decimal("0.90")),
                ),
            ),
            SemanticScoreFixture(
                request_id="semantic-low-001",
                intent_scores=(
                    SemanticIntentScore("order_tracking", Decimal("0.79")),
                    SemanticIntentScore("refund_request", Decimal("0.60")),
                ),
            ),
        ),
        minimum_similarity=Decimal(minimum_similarity),
    )


def test_semantic_router_selects_fixed_highest_score_and_preserves_policy_constraints() -> None:
    decision = _router().route(
        RoutingRequest(
            request_id="semantic-001",
            text="private order-like request",
            requirements=RoutingRequirements(
                maximum_cost=Decimal("0.004"),
                maximum_latency_ms=80,
                permitted_target_names=frozenset({"order-agent"}),
            ),
        )
    )

    assert decision.intent == "order_tracking"
    assert decision.similarity == Decimal("0.91")
    assert decision.target.name == "order-agent"


def test_semantic_router_resolves_equal_scores_by_intent_name_deterministically() -> None:
    decision = _router().route(
        RoutingRequest(request_id="semantic-tie-001", text="private ambiguous request")
    )

    assert decision.intent == "order_tracking"
    assert decision.target.name == "order-agent"


def test_semantic_router_fails_closed_for_missing_fixture_and_below_threshold() -> None:
    with pytest.raises(NoSemanticScoreFixtureError, match="no semantic score fixture"):
        _router().route(RoutingRequest(request_id="semantic-missing-001", text="private request"))

    with pytest.raises(NoConfidentSemanticRouteError, match="similarity threshold"):
        _router().route(RoutingRequest(request_id="semantic-low-001", text="private request"))


def test_semantic_router_does_not_bypass_policy_permissions_or_capability_requirements() -> None:
    request = RoutingRequest(
        request_id="semantic-001",
        text="private restricted request",
        requirements=RoutingRequirements(permitted_target_names=frozenset({"general-agent"})),
    )

    with pytest.raises(NoEligibleRouteError, match="no healthy target"):
        _router().route(request)


def test_semantic_decision_log_is_json_serializable_and_omits_request_text() -> None:
    secret_text = "do not log this customer secret"
    record = (
        _router().route(RoutingRequest(request_id="semantic-001", text=secret_text)).as_log_record()
    )

    assert record["classifier_name"] == "fixed-semantic-router"
    assert record["intent"] == "order_tracking"
    assert record["semantic_similarity"] == "0.91"
    assert secret_text not in json.dumps(record)
    json.dumps(record)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SemanticIntentScore("bad-score", Decimal("1.01")),
        lambda: SemanticRouter(
            name="missing-score-router",
            policy_router=PolicyRouter(
                name="single-policy",
                targets=(_target("single-agent", frozenset({"respond"})),),
            ),
            routes=(SemanticRoute("single", frozenset({"respond"})),),
            score_fixtures=(
                SemanticScoreFixture(
                    request_id="missing-score-001",
                    intent_scores=(SemanticIntentScore("other", Decimal("0.90")),),
                ),
            ),
            minimum_similarity=Decimal("0.80"),
        ),
        lambda: SemanticRouter(
            name="bad-threshold-router",
            policy_router=PolicyRouter(
                name="single-policy",
                targets=(_target("single-agent", frozenset({"respond"})),),
            ),
            routes=(SemanticRoute("single", frozenset({"respond"})),),
            score_fixtures=(
                SemanticScoreFixture(
                    request_id="bad-threshold-001",
                    intent_scores=(SemanticIntentScore("single", Decimal("0.90")),),
                ),
            ),
            minimum_similarity=Decimal("NaN"),
        ),
    ],
)
def test_semantic_router_rejects_invalid_or_incomplete_fixed_fixtures(factory: object) -> None:
    with pytest.raises(RoutingConfigurationError):
        factory()  # type: ignore[operator]
