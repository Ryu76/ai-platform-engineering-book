"""Volume 08 Router API의 외부 호출 없는 HTTP 계약 테스트."""

import json
from decimal import Decimal

from ai_platform.router import (
    PolicyRouter,
    RouterAPI,
    RouteTarget,
    RouteTargetKind,
)


def _api() -> RouterAPI:
    return RouterAPI(
        policy_router=PolicyRouter(
            name="fixed-api-policy",
            targets=(
                RouteTarget(
                    name="general-agent",
                    kind=RouteTargetKind.AGENT,
                    capabilities=frozenset({"respond"}),
                    estimated_cost=Decimal("0.002"),
                    estimated_latency_ms=80,
                ),
                RouteTarget(
                    name="order-agent",
                    kind=RouteTargetKind.AGENT,
                    capabilities=frozenset({"lookup_order", "respond"}),
                    estimated_cost=Decimal("0.003"),
                    estimated_latency_ms=70,
                ),
            ),
        )
    )


def test_router_api_returns_a_policy_decision_for_a_valid_post_body() -> None:
    response = _api().route_post(
        {
            "request_id": "api-route-001",
            "text": "private order request",
            "requirements": {
                "required_capabilities": ["lookup_order", "respond"],
                "maximum_cost": "0.004",
                "maximum_latency_ms": 80,
                "permitted_target_names": ["order-agent"],
            },
        }
    )

    assert response.status_code == 200
    assert response.body == {
        "outcome": "routed",
        "decision": {
            "request_id": "api-route-001",
            "policy_name": "fixed-api-policy",
            "target_name": "order-agent",
            "target_kind": "agent",
            "reason": "healthy-capability-cost-latency-policy",
            "confidence": "1",
            "estimated_cost": "0.003",
            "estimated_latency_ms": "70",
        },
    }


def test_router_api_rejects_invalid_http_input_without_echoing_text_or_details() -> None:
    secret_text = "customer secret must never be echoed"

    response = _api().route_post(
        {
            "request_id": "api-invalid-001",
            "text": secret_text,
            "requirements": {"maximum_cost": 0.004},
        }
    )

    assert response.status_code == 400
    assert response.body == {
        "outcome": "invalid_routing_request",
        "error_code": "INVALID_ROUTING_REQUEST",
    }
    assert secret_text not in json.dumps(response.body)


def test_router_api_rejects_unknown_fields_and_non_json_policy_types() -> None:
    unknown_field_response = _api().route_post(
        {
            "request_id": "api-unknown-001",
            "text": "private request",
            "unexpected": "customer secret",
        }
    )
    non_json_cost_response = _api().route_post(
        {
            "request_id": "api-cost-001",
            "text": "private request",
            "requirements": {"maximum_cost": Decimal("0.004")},
        }
    )

    assert unknown_field_response.status_code == 400
    assert non_json_cost_response.status_code == 400
    assert unknown_field_response.body["error_code"] == "INVALID_ROUTING_REQUEST"
    assert non_json_cost_response.body["error_code"] == "INVALID_ROUTING_REQUEST"


def test_router_api_fails_closed_when_policy_has_no_eligible_target() -> None:
    secret_text = "restricted customer order details"

    response = _api().route_post(
        {
            "request_id": "api-no-target-001",
            "text": secret_text,
            "requirements": {
                "required_capabilities": ["lookup_order"],
                "permitted_target_names": ["general-agent"],
            },
        }
    )

    assert response.status_code == 422
    assert response.body == {
        "request_id": "api-no-target-001",
        "outcome": "no_eligible_route",
        "error_code": "NO_ELIGIBLE_ROUTE",
    }
    assert secret_text not in json.dumps(response.body)


def test_router_api_response_bodies_are_json_serializable_and_omit_request_text() -> None:
    secret_text = "never write this request body to a response"

    success = _api().route_post(
        {"request_id": "api-json-001", "text": secret_text, "requirements": {}}
    )
    invalid = _api().route_post(
        {
            "request_id": "api-json-invalid-001",
            "text": secret_text,
            "requirements": {"maximum_cost": 0.004},
        }
    )

    assert success.status_code == 200
    assert invalid.status_code == 400
    assert secret_text not in json.dumps(success.body)
    assert secret_text not in json.dumps(invalid.body)
    json.dumps(success.body)
    json.dumps(invalid.body)
