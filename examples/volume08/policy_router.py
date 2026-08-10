"""고정 정책과 fixture만으로 Router 결정을 재현하는 Volume 08 예제."""
from __future__ import annotations

import json
from decimal import Decimal

from ai_platform.router import (
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingRequest,
    RoutingRequirements,
)


def build_fixture_router() -> PolicyRouter:
    """외부 서비스나 실시간 가격표 없이 동일한 Router fixture를 구성한다."""
    return PolicyRouter(
        name="offline-learning-policy",
        targets=(
            RouteTarget(
                name="general-agent",
                kind=RouteTargetKind.AGENT,
                capabilities=frozenset({"summarize", "classify"}),
                estimated_cost=Decimal("0.002"),
                estimated_latency_ms=120,
            ),
            RouteTarget(
                name="research-agent",
                kind=RouteTargetKind.AGENT,
                capabilities=frozenset({"summarize", "retrieve"}),
                estimated_cost=Decimal("0.008"),
                estimated_latency_ms=280,
            ),
            RouteTarget(
                name="offline-summary-model",
                kind=RouteTargetKind.MODEL,
                capabilities=frozenset({"summarize"}),
                estimated_cost=Decimal("0.002"),
                estimated_latency_ms=90,
            ),
        ),
    )


def main() -> None:
    """요청 원문을 로그에 포함하지 않는 고정 라우팅 결정을 출력한다."""
    router = build_fixture_router()
    decision = router.route(
        RoutingRequest(
            request_id="lesson-08-policy-001",
            text="이 문서를 요약해 주세요.",
            requirements=RoutingRequirements(
                required_capabilities=frozenset({"summarize"}),
                maximum_cost=Decimal("0.005"),
                maximum_latency_ms=150,
            ),
        )
    )
    print(json.dumps(decision.as_log_record(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
