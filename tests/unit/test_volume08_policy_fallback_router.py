"""Volume 08 policy fallback Router의 외부 호출 없는 결정론적 계약 테스트."""
import json
from decimal import Decimal

import pytest

from ai_platform.router import (
    FallbackRouteExhaustedError,
    PolicyFallbackRouter,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
)


def _target(
    name: str,
    *,
    cost: str = "0.001",
    healthy: bool = True,
) -> RouteTarget:
    return RouteTarget(
        name=name,
        kind=RouteTargetKind.AGENT,
        capabilities=frozenset({"respond"}),
        estimated_cost=Decimal(cost),
        estimated_latency_ms=50,
        healthy=healthy,
    )


def _policy(name: str, target: RouteTarget) -> PolicyRouter:
    return PolicyRouter(name=name, targets=(target,))


def test_fallback_uses_declared_order_and_preserves_request_policy_constraints() -> None:
    router = PolicyFallbackRouter(
        name="support-fallback-router",
        primary_router=_policy("primary-policy", _target("primary-agent")),
        fallback_routers=(
            _policy("first-fallback-policy", _target("first-fallback-agent")),
            _policy("second-fallback-policy", _target("second-fallback-agent")),
        ),
        retry_budget=2,
    )
    request = RoutingRequest(
        request_id="fallback-001",
        text="private customer request",
        requirements=RoutingRequirements(
            required_capabilities=frozenset({"respond"}),
            permitted_target_names=frozenset({"second-fallback-agent"}),
        ),
    )

    decision = router.route(request)

    assert decision.target.name == "second-fallback-agent"
    assert decision.policy_decision.policy_name == "second-fallback-policy"
    assert decision.attempted_policy_names == (
        "primary-policy",
        "first-fallback-policy",
        "second-fallback-policy",
    )
    assert decision.fallback_count == 2


def test_fallback_retry_budget_limits_attempts_and_fails_closed() -> None:
    router = PolicyFallbackRouter(
        name="bounded-fallback-router",
        primary_router=_policy("primary-policy", _target("primary-agent")),
        fallback_routers=(
            _policy("available-fallback-policy", _target("available-fallback-agent")),
        ),
        retry_budget=0,
    )
    request = RoutingRequest(
        request_id="fallback-002",
        text="private budget request",
        requirements=RoutingRequirements(
            permitted_target_names=frozenset({"available-fallback-agent"})
        ),
    )

    with pytest.raises(FallbackRouteExhaustedError) as error:
        router.route(request)

    assert error.value.attempted_policy_names == ("primary-policy",)


def test_fallback_does_not_bypass_cost_or_permission_constraints() -> None:
    router = PolicyFallbackRouter(
        name="constrained-fallback-router",
        primary_router=_policy("primary-policy", _target("primary-agent", cost="0.010")),
        fallback_routers=(
            _policy("fallback-policy", _target("fallback-agent", cost="0.009")),
        ),
        retry_budget=1,
    )
    request = RoutingRequest(
        request_id="fallback-003",
        text="private constrained request",
        requirements=RoutingRequirements(
            maximum_cost=Decimal("0.005"),
            permitted_target_names=frozenset({"fallback-agent"}),
        ),
    )

    with pytest.raises(FallbackRouteExhaustedError) as error:
        router.route(request)

    assert error.value.attempted_policy_names == ("primary-policy", "fallback-policy")


def test_fallback_success_and_exhaustion_logs_are_json_serializable_and_omit_request_text() -> None:
    secret_text = "do not write this customer secret"
    successful_router = PolicyFallbackRouter(
        name="logging-fallback-router",
        primary_router=_policy("unhealthy-primary", _target("unhealthy-agent", healthy=False)),
        fallback_routers=(
            _policy("healthy-fallback", _target("healthy-agent")),
        ),
        retry_budget=1,
    )
    request = RoutingRequest(request_id="fallback-004", text=secret_text)

    success_record = successful_router.route(request).as_log_record()

    assert success_record["fallback_router_name"] == "logging-fallback-router"
    assert success_record["fallback_count"] == 1
    assert success_record["attempted_policy_names"] == ["unhealthy-primary", "healthy-fallback"]
    assert secret_text not in json.dumps(success_record)
    json.dumps(success_record)

    exhausted_router = PolicyFallbackRouter(
        name="exhausted-fallback-router",
        primary_router=_policy("unhealthy-primary", _target("unhealthy-agent", healthy=False)),
        fallback_routers=(),
        retry_budget=0,
    )
    with pytest.raises(FallbackRouteExhaustedError) as error:
        exhausted_router.route(request)

    assert error.value.as_log_record() == {
        "request_id": "fallback-004",
        "outcome": "no_eligible_fallback_route",
        "attempted_policy_names": ["unhealthy-primary"],
    }
    assert secret_text not in json.dumps(error.value.as_log_record())
    json.dumps(error.value.as_log_record())


@pytest.mark.parametrize(
    "factory",
    [
        lambda: PolicyFallbackRouter(
            name="bad-budget-router",
            primary_router=_policy("primary-policy", _target("primary-agent")),
            fallback_routers=(),
            retry_budget=True,
        ),
        lambda: PolicyFallbackRouter(
            name="bad-budget-router",
            primary_router=_policy("primary-policy", _target("primary-agent")),
            fallback_routers=(),
            retry_budget=-1,
        ),
        lambda: PolicyFallbackRouter(
            name="duplicate-policy-router",
            primary_router=_policy("same-policy", _target("primary-agent")),
            fallback_routers=(
                _policy("same-policy", _target("fallback-agent")),
            ),
            retry_budget=1,
        ),
    ],
)
def test_fallback_router_rejects_invalid_retry_budget_and_ambiguous_policy_names(
    factory: object,
) -> None:
    with pytest.raises(RoutingConfigurationError):
        factory()  # type: ignore[operator]
