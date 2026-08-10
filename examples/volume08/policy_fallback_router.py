"""고정 정책 fixture로 제한된 fallback retry를 검증하는 Volume 08 예제."""
from __future__ import annotations

import json
from decimal import Decimal

from ai_platform.router import (
    PolicyFallbackRouter,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingRequest,
    RoutingRequirements,
)


def _target(name: str, *, healthy: bool) -> RouteTarget:
    """외부 서비스 없이 상태가 고정된 Agent 대상을 만든다."""
    return RouteTarget(
        name=name,
        kind=RouteTargetKind.AGENT,
        capabilities=frozenset({"respond"}),
        estimated_cost=Decimal("0.002"),
        estimated_latency_ms=60,
        healthy=healthy,
    )


def build_router() -> PolicyFallbackRouter:
    """비정상 primary와 정상 fallback을 명시적인 순서로 구성한다."""
    return PolicyFallbackRouter(
        name="offline-support-fallback-router",
        primary_router=PolicyRouter(
            name="offline-primary-policy",
            targets=(_target("offline-primary-agent", healthy=False),),
        ),
        fallback_routers=(
            PolicyRouter(
                name="offline-fallback-policy",
                targets=(_target("offline-fallback-agent", healthy=True),),
            ),
        ),
        retry_budget=1,
    )


def main() -> None:
    """fallback 성공의 원문 없는 감사 로그 한 줄을 출력한다."""
    decision = build_router().route(
        RoutingRequest(
            request_id="lesson-08-fallback-001",
            text="private support request",
            requirements=RoutingRequirements(
                required_capabilities=frozenset({"respond"}),
                permitted_target_names=frozenset({"offline-fallback-agent"}),
            ),
        )
    )
    print(json.dumps(decision.as_log_record(), sort_keys=True))


if __name__ == "__main__":
    main()
