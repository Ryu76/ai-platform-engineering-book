"""Volume 08 LLM Router의 외부 호출 없는 결정론적 계약 테스트."""
import json
from decimal import Decimal

import pytest

from ai_platform.router import (
    LLMClassifierResponseFixture,
    LLMRoute,
    LLMRouter,
    NoConfidentLLMRouteError,
    NoEligibleRouteError,
    NoLLMClassifierResponseFixtureError,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
)


def _target(name: str, capabilities: frozenset[str]) -> RouteTarget:
    return RouteTarget(
        name=name,
        kind=RouteTargetKind.AGENT,
        capabilities=capabilities,
        estimated_cost=Decimal("0.003"),
        estimated_latency_ms=70,
    )


def _router(*, minimum_confidence: str = "0.80") -> LLMRouter:
    return LLMRouter(
        name="fixed-llm-router",
        policy_router=PolicyRouter(
            name="fixed-llm-policy",
            targets=(
                _target("general-agent", frozenset({"respond"})),
                _target("order-agent", frozenset({"lookup_order", "respond"})),
                _target("refund-agent", frozenset({"issue_refund", "respond"})),
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
                request_id="llm-001",
                intent="order_tracking",
                confidence=Decimal("0.92"),
            ),
            LLMClassifierResponseFixture(
                request_id="llm-refund-001",
                intent="refund_request",
                confidence=Decimal("0.90"),
            ),
            LLMClassifierResponseFixture(
                request_id="llm-low-001",
                intent="order_tracking",
                confidence=Decimal("0.79"),
            ),
        ),
        minimum_confidence=Decimal(minimum_confidence),
    )


def test_llm_router_selects_fixed_label_and_preserves_policy_constraints() -> None:
    decision = _router().route(
        RoutingRequest(
            request_id="llm-001",
            text="private LLM-classified request",
            requirements=RoutingRequirements(
                maximum_cost=Decimal("0.004"),
                maximum_latency_ms=80,
                permitted_target_names=frozenset({"order-agent"}),
            ),
        )
    )

    assert decision.intent == "order_tracking"
    assert decision.confidence == Decimal("0.92")
    assert decision.target.name == "order-agent"


def test_llm_router_routes_each_reviewed_fixture_without_prompt_or_network() -> None:
    decision = _router().route(
        RoutingRequest(request_id="llm-refund-001", text="private refund-like request")
    )

    assert decision.intent == "refund_request"
    assert decision.target.name == "refund-agent"


def test_llm_router_fails_closed_for_missing_fixture_and_low_confidence() -> None:
    with pytest.raises(
        NoLLMClassifierResponseFixtureError, match="no LLM classifier response fixture"
    ):
        _router().route(RoutingRequest(request_id="llm-missing-001", text="private request"))

    with pytest.raises(NoConfidentLLMRouteError, match="confidence threshold"):
        _router().route(RoutingRequest(request_id="llm-low-001", text="private request"))


def test_llm_router_does_not_bypass_policy_permissions_or_capability_requirements() -> None:
    request = RoutingRequest(
        request_id="llm-001",
        text="private restricted request",
        requirements=RoutingRequirements(permitted_target_names=frozenset({"general-agent"})),
    )

    with pytest.raises(NoEligibleRouteError, match="no healthy target"):
        _router().route(request)


def test_llm_decision_log_is_json_serializable_and_omits_request_text() -> None:
    secret_text = "do not log this customer secret"
    record = _router().route(
        RoutingRequest(request_id="llm-001", text=secret_text)
    ).as_log_record()

    assert record["classifier_name"] == "fixed-llm-router"
    assert record["intent"] == "order_tracking"
    assert record["llm_classifier_confidence"] == "0.92"
    assert secret_text not in json.dumps(record)
    json.dumps(record)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: LLMClassifierResponseFixture("bad-score", "known", Decimal("1.01")),
        lambda: LLMRouter(
            name="unknown-intent-router",
            policy_router=PolicyRouter(
                name="single-policy",
                targets=(_target("single-agent", frozenset({"respond"})),),
            ),
            routes=(LLMRoute("single", frozenset({"respond"})),),
            response_fixtures=(
                LLMClassifierResponseFixture("unknown-001", "unknown", Decimal("0.90")),
            ),
            minimum_confidence=Decimal("0.80"),
        ),
        lambda: LLMRouter(
            name="duplicate-fixture-router",
            policy_router=PolicyRouter(
                name="single-policy",
                targets=(_target("single-agent", frozenset({"respond"})),),
            ),
            routes=(LLMRoute("single", frozenset({"respond"})),),
            response_fixtures=(
                LLMClassifierResponseFixture("duplicate-001", "single", Decimal("0.90")),
                LLMClassifierResponseFixture("duplicate-001", "single", Decimal("0.80")),
            ),
            minimum_confidence=Decimal("0.80"),
        ),
        lambda: _router(minimum_confidence="NaN"),
    ],
)
def test_llm_router_rejects_invalid_or_ambiguous_fixed_fixtures(factory: object) -> None:
    with pytest.raises(RoutingConfigurationError):
        factory()  # type: ignore[operator]
