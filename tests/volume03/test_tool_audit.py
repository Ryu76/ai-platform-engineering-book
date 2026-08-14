"""Volume 03 감사 로그가 승인 경계를 우회하거나 원문 인자를 저장하지 않는지 검사한다."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

import pytest

from ai_platform.tools.audit import (
    InMemoryToolAuditSink,
    ToolAuditOutcome,
    execute_audited,
)
from ai_platform.tools.authorization import (
    ApprovalGrant,
    ToolApprovalRequiredError,
    ToolAuthorizationPolicy,
    ToolRisk,
)
from ai_platform.tools.registry import ToolRegistry, ToolSpec

TEST_SCHEMA: Mapping[str, object] = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}


def _registry(handler: ToolSpec | None = None) -> ToolRegistry:
    if handler is not None:
        return ToolRegistry((handler,))
    return ToolRegistry(
        (
            ToolSpec(
                "reviewed_text",
                "감사 테스트 전용 순수 Tool",
                TEST_SCHEMA,
                lambda arguments: {"text": arguments["text"]},
            ),
        )
    )


def _approval(*, text: str) -> ApprovalGrant:
    return ApprovalGrant.for_request(
        approval_id="approval-001",
        request_id="request-001",
        tool_name="reviewed_text",
        arguments={"text": text},
    )


def test_success_audit_has_minimum_fields_but_never_raw_arguments_or_output() -> None:
    sink = InMemoryToolAuditSink()
    secret_like_text = "do-not-log-this-argument"
    result = execute_audited(
        _registry(),
        request_id="request-001",
        tool_name="reviewed_text",
        arguments={"text": secret_like_text},
        policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.HIGH}),
        approval=_approval(text=secret_like_text),
        audit_sink=sink,
    )

    assert result.output == {"text": secret_like_text}
    assert sink.events == (
        sink.events[0].__class__(
            request_id="request-001",
            tool_name="reviewed_text",
            risk=ToolRisk.HIGH,
            approval_id="approval-001",
            outcome=ToolAuditOutcome.SUCCEEDED,
        ),
    )
    assert secret_like_text not in str(asdict(sink.events[0]))


def test_denied_request_is_logged_before_its_handler_and_has_no_approval_id() -> None:
    calls = 0

    def handler(_: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    sink = InMemoryToolAuditSink()
    registry = _registry(ToolSpec("reviewed_text", "감사 거부 테스트 Tool", TEST_SCHEMA, handler))
    with pytest.raises(ToolApprovalRequiredError, match="human approval is required"):
        execute_audited(
            registry,
            request_id="request-002",
            tool_name="reviewed_text",
            arguments={"text": "blocked-and-not-logged"},
            policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.HIGH}),
            audit_sink=sink,
        )

    assert calls == 0
    assert sink.events[0].outcome is ToolAuditOutcome.DENIED
    assert sink.events[0].risk is ToolRisk.HIGH
    assert sink.events[0].approval_id is None
    assert "blocked-and-not-logged" not in str(asdict(sink.events[0]))


def test_handler_failure_is_distinct_from_authorization_denial() -> None:
    def failing_handler(_: Mapping[str, object]) -> Mapping[str, object]:
        raise RuntimeError("test-only handler failure")

    sink = InMemoryToolAuditSink()
    registry = _registry(
        ToolSpec("reviewed_text", "실패 감사 테스트 Tool", TEST_SCHEMA, failing_handler)
    )
    with pytest.raises(RuntimeError, match="test-only handler failure"):
        execute_audited(
            registry,
            request_id="request-003",
            tool_name="reviewed_text",
            arguments={"text": "not-logged"},
            policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.LOW}),
            audit_sink=sink,
        )

    assert sink.events[0].outcome is ToolAuditOutcome.FAILED


def test_audit_events_are_read_only_snapshots() -> None:
    sink = InMemoryToolAuditSink()
    execute_audited(
        _registry(),
        request_id="request-001",
        tool_name="reviewed_text",
        arguments={"text": "safe"},
        policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.HIGH}),
        approval=_approval(text="safe"),
        audit_sink=sink,
    )

    snapshot = sink.events
    assert isinstance(snapshot, tuple)
    with pytest.raises(AttributeError):
        snapshot.append(snapshot[0])  # type: ignore[attr-defined]
    assert len(sink.events) == 1
