"""Volume 08 Router 미니 프로젝트의 외부 호출 없는 조합 계약 테스트."""

import json

from ai_platform.router.mini_project import build_router_mini_project


def test_router_mini_project_combines_every_fixed_router_with_expected_targets() -> None:
    report = build_router_mini_project().run()

    assert set(report) == {
        "policy",
        "keyword",
        "semantic",
        "llm",
        "fallback",
        "escalation",
        "api",
    }
    assert report["policy"]["target_name"] == "mini-policy-agent"
    assert report["keyword"]["target_name"] == "mini-order-agent"
    assert report["keyword"]["intent"] == "order_tracking"
    assert report["semantic"]["target_name"] == "mini-refund-agent"
    assert report["semantic"]["semantic_similarity"] == "0.93"
    assert report["llm"]["target_name"] == "mini-priority-agent"
    assert report["llm"]["llm_classifier_confidence"] == "0.92"
    assert report["fallback"]["target_name"] == "mini-fallback-agent"
    assert report["fallback"]["attempted_policy_names"] == [
        "mini-primary-policy",
        "mini-fallback-policy",
    ]
    assert report["escalation"]["target_name"] == "mini-summary-model"
    assert report["escalation"]["attempted_stage_names"] == [
        "mini-agent-stage",
        "mini-tool-stage",
        "mini-model-stage",
    ]
    assert report["api"] == {
        "status_code": 200,
        "body": {
            "outcome": "routed",
            "decision": {
                "request_id": "mini-api-001",
                "policy_name": "mini-api-policy",
                "target_name": "mini-api-order-agent",
                "target_kind": "agent",
                "reason": "healthy-capability-cost-latency-policy",
                "confidence": "1",
                "estimated_cost": "0.003",
                "estimated_latency_ms": "70",
            },
        },
    }


def test_router_mini_project_is_deterministic_and_logs_no_request_text() -> None:
    first_report = build_router_mini_project().run()
    second_report = build_router_mini_project().run()
    serialized_report = json.dumps(first_report, sort_keys=True)

    assert first_report == second_report
    for private_text in (
        "private general support request",
        "private order tracking request",
        "private refund request",
        "private priority request",
        "private fallback request",
        "private escalation request",
        "private API order request",
    ):
        assert private_text not in serialized_report
    json.dumps(first_report)
