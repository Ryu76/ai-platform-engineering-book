"""Volume 08 정책 Router의 외부 호출 없는 결정론적 계약 테스트."""

from decimal import Decimal

import pytest

from ai_platform.router import (
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
    *,
    capabilities: frozenset[str] = frozenset({"summarize"}),
    cost: str = "0.002",
    latency_ms: int = 100,
    healthy: bool = True,
) -> RouteTarget:
    return RouteTarget(
        name=name,
        kind=RouteTargetKind.AGENT,
        capabilities=capabilities,
        estimated_cost=Decimal(cost),
        estimated_latency_ms=latency_ms,
        healthy=healthy,
    )


def test_policy_router_selects_lowest_cost_then_latency_then_name_deterministically() -> None:
    router = PolicyRouter(
        name="test-policy",
        targets=(
            _target("slower-cheap", latency_ms=200),
            _target("faster-cheap", latency_ms=100),
            _target("more-expensive", cost="0.003", latency_ms=10),
        ),
    )
    request = RoutingRequest(request_id="route-001", text="요약해 주세요.")

    decision = router.route(request)

    assert decision.target.name == "faster-cheap"
    assert decision.confidence == Decimal("1")
    assert decision.reason == "healthy-capability-cost-latency-policy"


def test_policy_router_requires_capability_budget_latency_and_permitted_target() -> None:
    router = PolicyRouter(
        name="constrained-policy",
        targets=(
            _target("no-retrieve", capabilities=frozenset({"summarize"}), cost="0.001"),
            _target(
                "too-expensive",
                capabilities=frozenset({"summarize", "retrieve"}),
                cost="0.020",
                latency_ms=50,
            ),
            _target(
                "too-slow",
                capabilities=frozenset({"summarize", "retrieve"}),
                cost="0.004",
                latency_ms=500,
            ),
            _target(
                "selected",
                capabilities=frozenset({"summarize", "retrieve"}),
                cost="0.004",
                latency_ms=100,
            ),
        ),
    )
    request = RoutingRequest(
        request_id="route-002",
        text="근거를 검색해서 요약해 주세요.",
        requirements=RoutingRequirements(
            required_capabilities=frozenset({"summarize", "retrieve"}),
            maximum_cost=Decimal("0.005"),
            maximum_latency_ms=150,
            permitted_target_names=frozenset({"selected", "too-slow"}),
        ),
    )

    decision = router.route(request)

    assert decision.target.name == "selected"


def test_policy_router_excludes_unhealthy_targets_and_fails_closed_without_match() -> None:
    router = PolicyRouter(
        name="health-policy",
        targets=(_target("unhealthy-but-cheap", healthy=False),),
    )

    with pytest.raises(NoEligibleRouteError, match="no healthy target"):
        router.route(RoutingRequest(request_id="route-003", text="요약해 주세요."))


def test_decision_log_is_serializable_and_omits_user_text() -> None:
    router = PolicyRouter(name="log-policy", targets=(_target("safe-agent"),))
    request = RoutingRequest(request_id="route-004", text="개인 원문은 로그에 남기지 않습니다.")

    record = router.route(request).as_log_record()

    assert record == {
        "request_id": "route-004",
        "policy_name": "log-policy",
        "target_name": "safe-agent",
        "target_kind": "agent",
        "reason": "healthy-capability-cost-latency-policy",
        "confidence": "1",
        "estimated_cost": "0.002",
        "estimated_latency_ms": "100",
    }
    assert request.text not in record.values()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _target("bad-cost", cost="-0.001"),
        lambda: _target("bad-latency", latency_ms=-1),
        lambda: RouteTarget(
            name="no-capabilities",
            kind=RouteTargetKind.TOOL,
            capabilities=frozenset(),
            estimated_cost=Decimal("0"),
            estimated_latency_ms=0,
        ),
        lambda: RoutingRequirements(maximum_cost=Decimal("NaN")),
        lambda: RoutingRequirements(permitted_target_names=frozenset()),
    ],
)
def test_router_contract_rejects_invalid_target_and_requirement_values(factory: object) -> None:
    with pytest.raises(RoutingConfigurationError):
        factory()  # type: ignore[operator]


def test_policy_rejects_duplicate_target_names() -> None:
    with pytest.raises(RoutingConfigurationError, match="unique"):
        PolicyRouter(name="duplicate-policy", targets=(_target("same"), _target("same")))
