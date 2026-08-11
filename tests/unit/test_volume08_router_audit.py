"""Volume 08 Router 감사 record allowlist·privacy 계약 테스트."""

from __future__ import annotations

import json
from decimal import Decimal
from math import inf, nan

import pytest

from ai_platform.router import (
    UnsafeRouterAuditRecordError,
    serialize_router_audit_report,
    validate_router_audit_record,
    validate_router_audit_report,
)
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


def test_audit_record_rejects_non_strict_json_values_and_invalid_sensitive_inputs() -> None:
    with pytest.raises(UnsafeRouterAuditRecordError, match="non-JSON value"):
        validate_router_audit_record(
            {"request_id": "audit-decimal-001", "confidence": Decimal("1")}
        )
    for unsafe_float in (nan, inf, -inf):
        with pytest.raises(UnsafeRouterAuditRecordError, match="strict JSON serializable"):
            validate_router_audit_record(
                {"request_id": "audit-non-finite-001", "confidence": unsafe_float}
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


def test_mini_project_report_requires_all_and_only_configured_paths() -> None:
    report = build_router_mini_project().run()
    request_texts = _mini_project_request_texts()

    validate_router_audit_report(report, sensitive_values_by_route=request_texts)

    with pytest.raises(UnsafeRouterAuditRecordError, match="exactly the configured"):
        validate_router_audit_report(
            {name: record for name, record in report.items() if name != "api"},
            sensitive_values_by_route={
                name: values for name, values in request_texts.items() if name != "api"
            },
        )
    with pytest.raises(UnsafeRouterAuditRecordError, match="exactly the configured"):
        validate_router_audit_report(
            report,
            sensitive_values_by_route={**request_texts, "unexpected": ("private",)},
        )


def test_mini_project_report_rejects_non_mapping_records_and_route_specific_leaks() -> None:
    report = build_router_mini_project().run()
    request_texts = _mini_project_request_texts()
    malformed_report = {**report, "policy": "not-a-record"}
    with pytest.raises(UnsafeRouterAuditRecordError, match="record must be a mapping"):
        validate_router_audit_report(malformed_report, sensitive_values_by_route=request_texts)
    leaked_report = {
        **report,
        "policy": {**report["policy"], "reason": "private general support request"},
    }
    with pytest.raises(UnsafeRouterAuditRecordError, match="sensitive value"):
        validate_router_audit_report(leaked_report, sensitive_values_by_route=request_texts)


def test_mini_project_report_rejects_missing_or_cross_route_audit_fields() -> None:
    report = build_router_mini_project().run()
    request_texts = _mini_project_request_texts()

    with pytest.raises(UnsafeRouterAuditRecordError, match="configured route schema"):
        validate_router_audit_report(
            {
                **report,
                "policy": {
                    key: value for key, value in report["policy"].items() if key != "target_name"
                },
            },
            sensitive_values_by_route=request_texts,
        )
    with pytest.raises(UnsafeRouterAuditRecordError, match="configured route schema"):
        validate_router_audit_report(
            {**report, "policy": {**report["policy"], "rule_name": "billing-support"}},
            sensitive_values_by_route=request_texts,
        )


def test_mini_project_report_rejects_malformed_nested_api_audit_schema() -> None:
    report = build_router_mini_project().run()

    with pytest.raises(UnsafeRouterAuditRecordError, match="configured route schema"):
        validate_router_audit_report(
            {
                **report,
                "api": {
                    **report["api"],
                    "body": {"outcome": "routed", "decision": {"request_id": "mini-api-001"}},
                },
            },
            sensitive_values_by_route=_mini_project_request_texts(),
        )


def test_mini_project_report_rejects_wrong_route_specific_audit_value_types() -> None:
    report = build_router_mini_project().run()
    request_texts = _mini_project_request_texts()

    invalid_reports = (
        {**report, "policy": {**report["policy"], "confidence": 1}},
        {**report, "keyword": {**report["keyword"], "matched_keywords": ("order",)}},
        {**report, "keyword": {**report["keyword"], "matched_keywords": [" "]}},
        {
            **report,
            "fallback": {
                **report["fallback"],
                "attempted_policy_names": ["mini-primary-policy", "mini-primary-policy"],
            },
        },
        {**report, "fallback": {**report["fallback"], "fallback_count": True}},
        {**report, "escalation": {**report["escalation"], "attempted_stage_names": []}},
        {**report, "api": {**report["api"], "status_code": True}},
        {
            **report,
            "api": {
                **report["api"],
                "body": {**report["api"]["body"], "outcome": ""},
            },
        },
    )
    for invalid_report in invalid_reports:
        with pytest.raises(UnsafeRouterAuditRecordError, match="route value types"):
            validate_router_audit_report(invalid_report, sensitive_values_by_route=request_texts)


def test_mini_project_report_rejects_invalid_semantic_audit_values() -> None:
    report = build_router_mini_project().run()
    request_texts = _mini_project_request_texts()

    invalid_reports = (
        {**report, "policy": {**report["policy"], "confidence": "not-a-probability"}},
        {**report, "semantic": {**report["semantic"], "semantic_similarity": "1.01"}},
        {**report, "fallback": {**report["fallback"], "estimated_cost": "-0.001"}},
        {**report, "policy": {**report["policy"], "estimated_latency_ms": "70.5"}},
        {**report, "escalation": {**report["escalation"], "stage_target_kind": "queue"}},
        {
            **report,
            "api": {
                **report["api"],
                "body": {
                    **report["api"]["body"],
                    "decision": {**report["api"]["body"]["decision"], "confidence": "1.01"},
                },
            },
        },
    )
    for invalid_report in invalid_reports:
        with pytest.raises(UnsafeRouterAuditRecordError, match="route value types"):
            validate_router_audit_report(invalid_report, sensitive_values_by_route=request_texts)


def test_audit_report_serializer_revalidates_and_emits_canonical_strict_json() -> None:
    report = build_router_mini_project().run()
    request_texts = _mini_project_request_texts()

    serialized_report = serialize_router_audit_report(
        report, sensitive_values_by_route=request_texts
    )

    assert serialized_report == serialize_router_audit_report(
        report, sensitive_values_by_route=request_texts
    )
    assert serialized_report == json.dumps(
        report,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    with pytest.raises(UnsafeRouterAuditRecordError, match="unsafe field"):
        serialize_router_audit_report(
            {**report, "policy": {**report["policy"], "request_text": "customer secret"}},
            sensitive_values_by_route=request_texts,
        )


def _mini_project_request_texts() -> dict[str, tuple[str]]:
    """고정 report 경로와 대응하는 원문 fixture를 반환한다."""
    return {
        "policy": ("private general support request",),
        "rule": ("private billing rule request",),
        "keyword": ("private order tracking request",),
        "semantic": ("private refund request",),
        "llm": ("private priority request",),
        "fallback": ("private fallback request",),
        "escalation": ("private escalation request",),
        "api": ("private API order request",),
    }
