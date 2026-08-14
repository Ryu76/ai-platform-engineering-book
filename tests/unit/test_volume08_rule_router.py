"""Volume 08 Rule Router의 외부 호출 없는 결정론적 계약 테스트."""

import json
from decimal import Decimal

import pytest

from ai_platform.router import (
    NoEligibleRouteError,
    NoMatchingRuleRouteError,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
    RuleRoute,
    RuleRouter,
)


def _target(name: str, capabilities: frozenset[str]) -> RouteTarget:
    return RouteTarget(
        name=name,
        kind=RouteTargetKind.AGENT,
        capabilities=capabilities,
        estimated_cost=Decimal("0.002"),
        estimated_latency_ms=60,
    )


def _router() -> RuleRouter:
    return RuleRouter(
        name="fixed-rule-router",
        policy_router=PolicyRouter(
            name="fixed-rule-policy",
            targets=(
                _target("general-agent", frozenset({"respond", "support"})),
                _target("billing-agent", frozenset({"billing", "refund", "respond", "support"})),
            ),
        ),
        routes=(
            RuleRoute(
                name="billing-support",
                required_request_capabilities=frozenset({"billing"}),
                added_required_capabilities=frozenset({"refund"}),
                priority=20,
            ),
            RuleRoute(
                name="general-support",
                required_request_capabilities=frozenset({"support"}),
                added_required_capabilities=frozenset({"respond"}),
                priority=10,
            ),
        ),
    )


def test_rule_router_selects_highest_priority_matching_rule_then_rechecks_policy() -> None:
    decision = _router().route(
        RoutingRequest(
            request_id="rule-001",
            text="private billing support request",
            requirements=RoutingRequirements(
                required_capabilities=frozenset({"billing", "support"}),
                permitted_target_names=frozenset({"billing-agent"}),
            ),
        )
    )

    assert decision.rule_name == "billing-support"
    assert decision.target.name == "billing-agent"


def test_rule_router_breaks_equal_priority_ties_by_rule_name_not_declaration_order() -> None:
    router = RuleRouter(
        name="tie-rule-router",
        policy_router=PolicyRouter(
            name="tie-rule-policy",
            targets=(_target("shared-agent", frozenset({"respond", "alpha", "support", "zeta"})),),
        ),
        routes=(
            RuleRoute(
                name="zeta-rule",
                required_request_capabilities=frozenset({"support"}),
                added_required_capabilities=frozenset({"zeta"}),
                priority=10,
            ),
            RuleRoute(
                name="alpha-rule",
                required_request_capabilities=frozenset({"support"}),
                added_required_capabilities=frozenset({"alpha"}),
                priority=10,
            ),
        ),
    )

    decision = router.route(
        RoutingRequest(
            request_id="rule-002",
            text="private support request",
            requirements=RoutingRequirements(required_capabilities=frozenset({"support"})),
        )
    )

    assert decision.rule_name == "alpha-rule"


def test_rule_router_fails_closed_for_no_matching_rule_or_policy_denial() -> None:
    with pytest.raises(NoMatchingRuleRouteError, match="no rule route matches"):
        _router().route(
            RoutingRequest(
                request_id="rule-003",
                text="private unmatched request",
                requirements=RoutingRequirements(required_capabilities=frozenset({"technical"})),
            )
        )

    with pytest.raises(NoEligibleRouteError, match="no healthy target"):
        _router().route(
            RoutingRequest(
                request_id="rule-004",
                text="private denied billing request",
                requirements=RoutingRequirements(
                    required_capabilities=frozenset({"billing"}),
                    permitted_target_names=frozenset({"general-agent"}),
                ),
            )
        )


def test_rule_route_decision_log_is_json_serializable_and_omits_request_text() -> None:
    request = RoutingRequest(
        request_id="rule-005",
        text="private billing secret",
        requirements=RoutingRequirements(required_capabilities=frozenset({"billing"})),
    )

    record = _router().route(request).as_log_record()

    assert record["rule_router_name"] == "fixed-rule-router"
    assert record["rule_name"] == "billing-support"
    assert request.text not in json.dumps(record)
    json.dumps(record)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RuleRoute(
            name="empty-match",
            required_request_capabilities=frozenset(),
            added_required_capabilities=frozenset({"respond"}),
            priority=1,
        ),
        lambda: RuleRoute(
            name="boolean-priority",
            required_request_capabilities=frozenset({"support"}),
            added_required_capabilities=frozenset({"respond"}),
            priority=True,
        ),
        lambda: RuleRouter(
            name="duplicate-rules",
            policy_router=PolicyRouter(
                name="duplicate-rule-policy",
                targets=(_target("only-agent", frozenset({"respond", "support"})),),
            ),
            routes=(
                RuleRoute(
                    name="same",
                    required_request_capabilities=frozenset({"support"}),
                    added_required_capabilities=frozenset({"respond"}),
                    priority=1,
                ),
                RuleRoute(
                    name="same",
                    required_request_capabilities=frozenset({"billing"}),
                    added_required_capabilities=frozenset({"respond"}),
                    priority=2,
                ),
            ),
        ),
    ],
)
def test_rule_router_rejects_invalid_or_ambiguous_configuration(factory: object) -> None:
    with pytest.raises(RoutingConfigurationError):
        factory()  # type: ignore[operator]
