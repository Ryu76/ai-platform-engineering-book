"""고정 escalation fixture로 Agent·Tool·Model 정책 경계를 지키는 Volume 08 예제."""

from __future__ import annotations

import json
from decimal import Decimal

from ai_platform.router import (
    EscalationFixture,
    MultiStageEscalationRouter,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingRequest,
    RoutingRequirements,
    RoutingStage,
)


def build_router() -> MultiStageEscalationRouter:
    """외부 호출 없이 고정 Agent·Tool·Model stage와 escalation fixture를 구성한다."""
    return MultiStageEscalationRouter(
        name="offline-support-escalation-router",
        stages=(
            RoutingStage(
                name="agent-stage",
                target_kind=RouteTargetKind.AGENT,
                policy_router=PolicyRouter(
                    name="offline-agent-policy",
                    targets=(
                        RouteTarget(
                            name="offline-triage-agent",
                            kind=RouteTargetKind.AGENT,
                            capabilities=frozenset({"respond"}),
                            estimated_cost=Decimal("0.001"),
                            estimated_latency_ms=40,
                            healthy=False,
                        ),
                    ),
                ),
                permitted_target_names=frozenset({"offline-triage-agent"}),
            ),
            RoutingStage(
                name="tool-stage",
                target_kind=RouteTargetKind.TOOL,
                policy_router=PolicyRouter(
                    name="offline-tool-policy",
                    targets=(
                        RouteTarget(
                            name="offline-order-tool",
                            kind=RouteTargetKind.TOOL,
                            capabilities=frozenset({"respond"}),
                            estimated_cost=Decimal("0.002"),
                            estimated_latency_ms=60,
                            healthy=False,
                        ),
                    ),
                ),
                permitted_target_names=frozenset({"offline-order-tool"}),
            ),
            RoutingStage(
                name="model-stage",
                target_kind=RouteTargetKind.MODEL,
                policy_router=PolicyRouter(
                    name="offline-model-policy",
                    targets=(
                        RouteTarget(
                            name="offline-summary-model",
                            kind=RouteTargetKind.MODEL,
                            capabilities=frozenset({"respond"}),
                            estimated_cost=Decimal("0.004"),
                            estimated_latency_ms=90,
                        ),
                    ),
                ),
                permitted_target_names=frozenset({"offline-summary-model"}),
            ),
        ),
        escalation_fixtures=(
            EscalationFixture(
                request_id="lesson-08-escalation-001",
                stage_names=("agent-stage", "tool-stage", "model-stage"),
            ),
        ),
        escalation_budget=2,
    )


def main() -> None:
    """세 stage를 고정 순서로 정책 재검증한 성공 감사 로그 한 줄을 출력한다."""
    decision = build_router().route(
        RoutingRequest(
            request_id="lesson-08-escalation-001",
            text="private multi-stage routing request",
            requirements=RoutingRequirements(
                required_capabilities=frozenset({"respond"}),
                maximum_cost=Decimal("0.005"),
                maximum_latency_ms=100,
                permitted_target_names=frozenset({"offline-summary-model"}),
            ),
        )
    )
    print(json.dumps(decision.as_log_record(), sort_keys=True))


if __name__ == "__main__":
    main()
