"""고정 PolicyRouter를 로컬 HTTP 요청·응답 계약으로 변환하는 Volume 08 예제."""

from __future__ import annotations

import json
from decimal import Decimal

from ai_platform.router import PolicyRouter, RouterAPI, RouteTarget, RouteTargetKind


def build_fixture_api() -> RouterAPI:
    """외부 HTTP 서버나 서비스 없이 재현 가능한 Router API fixture를 구성한다."""
    return RouterAPI(
        policy_router=PolicyRouter(
            name="offline-router-api-policy",
            targets=(
                RouteTarget(
                    name="offline-order-agent",
                    kind=RouteTargetKind.AGENT,
                    capabilities=frozenset({"lookup_order", "respond"}),
                    estimated_cost=Decimal("0.003"),
                    estimated_latency_ms=70,
                ),
            ),
        )
    )


def main() -> None:
    """고정 JSON POST body의 상태 코드와 원문 없는 decision 응답을 출력한다."""
    response = build_fixture_api().route_post(
        {
            "request_id": "lesson-08-api-001",
            "text": "주문 상태를 알려 주세요.",
            "requirements": {
                "required_capabilities": ["lookup_order", "respond"],
                "maximum_cost": "0.004",
                "maximum_latency_ms": 80,
                "permitted_target_names": ["offline-order-agent"],
            },
        }
    )
    print(
        json.dumps(
            {"status_code": response.status_code, "body": response.body},
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
