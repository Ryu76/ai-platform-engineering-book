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
    SemanticEmbeddingFixture,
    SemanticIntentEmbedding,
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


def test_semantic_router_calculates_local_cosine_similarity_from_fixed_embeddings() -> None:
    router = SemanticRouter(
        name="fixed-embedding-semantic-router",
        policy_router=PolicyRouter(
            name="fixed-embedding-semantic-policy",
            targets=(
                _target("order-agent", frozenset({"lookup_order", "respond"})),
                _target("refund-agent", frozenset({"issue_refund", "respond"})),
            ),
        ),
        routes=(
            SemanticRoute("order_tracking", frozenset({"lookup_order", "respond"})),
            SemanticRoute("refund_request", frozenset({"issue_refund", "respond"})),
        ),
        embedding_fixtures=(
            SemanticEmbeddingFixture(
                request_id="semantic-embedding-001",
                query_embedding=(Decimal("3"), Decimal("4")),
                intent_embeddings=(
                    SemanticIntentEmbedding("order_tracking", (Decimal("3"), Decimal("4"))),
                    SemanticIntentEmbedding("refund_request", (Decimal("4"), Decimal("3"))),
                ),
            ),
        ),
        minimum_similarity=Decimal("0.80"),
    )

    decision = router.route(
        RoutingRequest(
            request_id="semantic-embedding-001",
            text="private embedding request",
            requirements=RoutingRequirements(permitted_target_names=frozenset({"order-agent"})),
        )
    )

    assert decision.intent == "order_tracking"
    assert decision.similarity == Decimal("1")
    assert decision.target.name == "order-agent"


def test_semantic_router_resolves_equal_scores_by_intent_name_deterministically() -> None:
    decision = _router().route(
        RoutingRequest(request_id="semantic-tie-001", text="private ambiguous request")
    )

    assert decision.intent == "order_tracking"
    assert decision.target.name == "order-agent"


def test_semantic_router_resolves_equal_local_cosine_scores_by_intent_name() -> None:
    router = SemanticRouter(
        name="fixed-embedding-tie-router",
        policy_router=PolicyRouter(
            name="fixed-embedding-tie-policy",
            targets=(
                _target("order-agent", frozenset({"lookup_order", "respond"})),
                _target("refund-agent", frozenset({"issue_refund", "respond"})),
            ),
        ),
        routes=(
            SemanticRoute("refund_request", frozenset({"issue_refund", "respond"})),
            SemanticRoute("order_tracking", frozenset({"lookup_order", "respond"})),
        ),
        embedding_fixtures=(
            SemanticEmbeddingFixture(
                request_id="semantic-embedding-tie-001",
                query_embedding=(Decimal("1"), Decimal("1")),
                intent_embeddings=(
                    SemanticIntentEmbedding("refund_request", (Decimal("0"), Decimal("1"))),
                    SemanticIntentEmbedding("order_tracking", (Decimal("1"), Decimal("0"))),
                ),
            ),
        ),
        minimum_similarity=Decimal("0.70"),
    )

    decision = router.route(
        RoutingRequest(
            request_id="semantic-embedding-tie-001",
            text="private embedding tie request",
            requirements=RoutingRequirements(permitted_target_names=frozenset({"order-agent"})),
        )
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


def test_semantic_router_rejects_mixed_fixture_modes_and_embedding_dimension_mismatches() -> None:
    policy_router = PolicyRouter(
        name="single-policy",
        targets=(_target("single-agent", frozenset({"respond"})),),
    )
    route = SemanticRoute("single", frozenset({"respond"}))
    score_fixture = SemanticScoreFixture(
        request_id="score-001",
        intent_scores=(SemanticIntentScore("single", Decimal("0.90")),),
    )
    embedding_fixture = SemanticEmbeddingFixture(
        request_id="embedding-001",
        query_embedding=(Decimal("1"),),
        intent_embeddings=(SemanticIntentEmbedding("single", (Decimal("1"),)),),
    )

    with pytest.raises(RoutingConfigurationError, match="but not both"):
        SemanticRouter(
            name="mixed-fixture-router",
            policy_router=policy_router,
            routes=(route,),
            score_fixtures=(score_fixture,),
            embedding_fixtures=(embedding_fixture,),
            minimum_similarity=Decimal("0.80"),
        )
    with pytest.raises(RoutingConfigurationError, match="share one dimension"):
        SemanticRouter(
            name="dimension-mismatch-router",
            policy_router=policy_router,
            routes=(route,),
            embedding_fixtures=(
                SemanticEmbeddingFixture(
                    request_id="mismatch-001",
                    query_embedding=(Decimal("1"), Decimal("1")),
                    intent_embeddings=(SemanticIntentEmbedding("single", (Decimal("1"),)),),
                ),
            ),
            minimum_similarity=Decimal("0.80"),
        )


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
