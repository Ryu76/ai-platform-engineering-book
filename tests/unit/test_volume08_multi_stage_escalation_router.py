"""Volume 08 다단계 escalation Router의 외부 호출 없는 결정론적 계약 테스트."""

import json
from decimal import Decimal

import pytest

from ai_platform.router import (
    EscalationFixture,
    EscalationRouteExhaustedError,
    MultiStageEscalationRouter,
    NoEscalationFixtureError,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
    RoutingStage,
)


def _target(
    name: str,
    kind: RouteTargetKind,
    *,
    cost: str,
    latency_ms: int,
    healthy: bool = True,
) -> RouteTarget:
    return RouteTarget(
        name=name,
        kind=kind,
        capabilities=frozenset({"respond"}),
        estimated_cost=Decimal(cost),
        estimated_latency_ms=latency_ms,
        healthy=healthy,
    )


def _stage(
    name: str,
    target: RouteTarget,
) -> RoutingStage:
    return RoutingStage(
        name=name,
        target_kind=target.kind,
        policy_router=PolicyRouter(name=f"{name}-policy", targets=(target,)),
        permitted_target_names=frozenset({target.name}),
    )


def _router(
    *,
    agent_healthy: bool = False,
    tool_healthy: bool = False,
    escalation_budget: int = 2,
) -> MultiStageEscalationRouter:
    return MultiStageEscalationRouter(
        name="fixed-multi-stage-router",
        stages=(
            _stage(
                "agent-stage",
                _target(
                    "triage-agent",
                    RouteTargetKind.AGENT,
                    cost="0.001",
                    latency_ms=40,
                    healthy=agent_healthy,
                ),
            ),
            _stage(
                "tool-stage",
                _target(
                    "order-tool",
                    RouteTargetKind.TOOL,
                    cost="0.002",
                    latency_ms=60,
                    healthy=tool_healthy,
                ),
            ),
            _stage(
                "model-stage",
                _target(
                    "summary-model",
                    RouteTargetKind.MODEL,
                    cost="0.004",
                    latency_ms=90,
                ),
            ),
        ),
        escalation_fixtures=(
            EscalationFixture(
                request_id="escalation-001",
                stage_names=("agent-stage", "tool-stage", "model-stage"),
            ),
        ),
        escalation_budget=escalation_budget,
    )


def test_multi_stage_router_uses_fixed_agent_tool_model_order_with_policy_rechecks() -> None:
    decision = _router().route(
        RoutingRequest(
            request_id="escalation-001",
            text="private multi-stage request",
            requirements=RoutingRequirements(
                required_capabilities=frozenset({"respond"}),
                maximum_cost=Decimal("0.005"),
                maximum_latency_ms=100,
                permitted_target_names=frozenset({"summary-model"}),
            ),
        )
    )

    assert decision.stage_name == "model-stage"
    assert decision.target_kind is RouteTargetKind.MODEL
    assert decision.target.name == "summary-model"
    assert decision.attempted_stage_names == ("agent-stage", "tool-stage", "model-stage")
    assert decision.escalation_count == 2


def test_multi_stage_router_limits_escalation_attempts_and_fails_closed() -> None:
    router = _router(escalation_budget=0)

    with pytest.raises(EscalationRouteExhaustedError) as error:
        router.route(RoutingRequest(request_id="escalation-001", text="private budget request"))

    assert error.value.attempted_stage_names == ("agent-stage",)


def test_multi_stage_router_does_not_bypass_permission_cost_or_latency_constraints() -> None:
    router = _router(agent_healthy=True, tool_healthy=True)
    request = RoutingRequest(
        request_id="escalation-001",
        text="private restricted request",
        requirements=RoutingRequirements(
            maximum_cost=Decimal("0.003"),
            maximum_latency_ms=80,
            permitted_target_names=frozenset({"summary-model"}),
        ),
    )

    with pytest.raises(EscalationRouteExhaustedError) as error:
        router.route(request)

    assert error.value.attempted_stage_names == ("agent-stage", "tool-stage", "model-stage")


def test_multi_stage_router_fails_closed_for_missing_fixture() -> None:
    with pytest.raises(NoEscalationFixtureError, match="no escalation fixture"):
        _router().route(RoutingRequest(request_id="escalation-missing-001", text="private request"))


def test_multi_stage_success_and_exhaustion_logs_are_json_serializable_and_omit_request_text() -> (
    None
):
    secret_text = "do not log this customer secret"
    success_record = (
        _router()
        .route(RoutingRequest(request_id="escalation-001", text=secret_text))
        .as_log_record()
    )

    assert success_record["multi_stage_router_name"] == "fixed-multi-stage-router"
    assert success_record["stage_name"] == "model-stage"
    assert success_record["stage_target_kind"] == "model"
    assert success_record["escalation_count"] == 2
    assert secret_text not in json.dumps(success_record)
    json.dumps(success_record)

    with pytest.raises(EscalationRouteExhaustedError) as error:
        _router(escalation_budget=0).route(
            RoutingRequest(request_id="escalation-001", text=secret_text)
        )

    assert error.value.as_log_record() == {
        "request_id": "escalation-001",
        "outcome": "no_eligible_escalation_route",
        "attempted_stage_names": ["agent-stage"],
    }
    assert secret_text not in json.dumps(error.value.as_log_record())
    json.dumps(error.value.as_log_record())


@pytest.mark.parametrize(
    "factory",
    [
        lambda: MultiStageEscalationRouter(
            name="bad-budget-router",
            stages=(
                _stage(
                    "agent-stage", _target("agent", RouteTargetKind.AGENT, cost="0", latency_ms=1)
                ),
            ),
            escalation_fixtures=(EscalationFixture("bad-budget-001", ("agent-stage",)),),
            escalation_budget=True,
        ),
        lambda: RoutingStage(
            name="mismatched-kind-stage",
            target_kind=RouteTargetKind.TOOL,
            policy_router=PolicyRouter(
                name="agent-policy",
                targets=(_target("agent", RouteTargetKind.AGENT, cost="0", latency_ms=1),),
            ),
            permitted_target_names=frozenset({"agent"}),
        ),
        lambda: MultiStageEscalationRouter(
            name="unknown-stage-router",
            stages=(
                _stage(
                    "agent-stage", _target("agent", RouteTargetKind.AGENT, cost="0", latency_ms=1)
                ),
            ),
            escalation_fixtures=(EscalationFixture("unknown-stage-001", ("missing-stage",)),),
            escalation_budget=0,
        ),
    ],
)
def test_multi_stage_router_rejects_invalid_budget_or_ambiguous_stage_contracts(
    factory: object,
) -> None:
    with pytest.raises(RoutingConfigurationError):
        factory()  # type: ignore[operator]
