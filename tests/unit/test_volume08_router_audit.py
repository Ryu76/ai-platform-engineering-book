"""Volume 08 Router 감사 record allowlist·privacy 계약 테스트."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ai_platform.router import UnsafeRouterAuditRecordError, validate_router_audit_record
from ai_platform.router.mini_project import build_router_mini_project


def test_mini_project_records_pass_the_audit_allowlist_without_request_text() -> None:
    report = build_router_mini_project().run()

    for record in report.values():
        validate_router_audit_record(
            record,
            sensitive_values=(
                "private general support request",
                "private billing rule request",
                "private order tracking request",
                "private refund request",
                "private priority request",
                "private fallback request",
                "private escalation request",
                "private API order request",
            ),
        )


def test_audit_record_rejects_unknown_fields_before_they_can_leak_input() -> None:
    with pytest.raises(UnsafeRouterAuditRecordError, match="unsafe field"):
        validate_router_audit_record(
            {"request_id": "audit-unknown-001", "request_text": "customer secret"},
            sensitive_values=("customer secret",),
        )


def test_audit_record_rejects_sensitive_text_even_under_an_allowed_field() -> None:
    with pytest.raises(UnsafeRouterAuditRecordError, match="sensitive value"):
        validate_router_audit_record(
            {"request_id": "audit-private-001", "reason": "customer secret was routed"},
            sensitive_values=("customer secret",),
        )


def test_audit_record_rejects_non_json_values_and_invalid_sensitive_inputs() -> None:
    with pytest.raises(UnsafeRouterAuditRecordError, match="non-JSON value"):
        validate_router_audit_record(
            {"request_id": "audit-decimal-001", "confidence": Decimal("1")}
        )
    with pytest.raises(UnsafeRouterAuditRecordError, match="nonempty strings"):
        validate_router_audit_record({"request_id": "audit-empty-001"}, sensitive_values=("",))
    with pytest.raises(UnsafeRouterAuditRecordError, match="iterable of strings"):
        validate_router_audit_record(
            {"request_id": "audit-string-001"}, sensitive_values="private input"
        )


def test_audit_record_allows_safe_nested_router_api_response() -> None:
    validate_router_audit_record(
        {
            "status_code": 200,
            "body": {
                "outcome": "routed",
                "decision": {
                    "request_id": "audit-api-001",
                    "policy_name": "audit-policy",
                    "target_name": "audit-agent",
                    "target_kind": "agent",
                    "reason": "policy",
                    "confidence": "1",
                    "estimated_cost": "0.001",
                    "estimated_latency_ms": "50",
                },
            },
        },
        sensitive_values=("private input",),
    )
