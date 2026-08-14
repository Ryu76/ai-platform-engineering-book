"""Volume 03 MCP dispatcher가 parser 이후 실행 경계를 우회하지 않는지 검사한다."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from threading import Event

import pytest

from ai_platform.mcp.dispatcher import McpDispatchError, dispatch_mcp_tool_call
from ai_platform.mcp.requests import McpCallRequestError
from ai_platform.tools.audit import InMemoryToolAuditSink, ToolAuditOutcome
from ai_platform.tools.authorization import (
    ToolApprovalRequiredError,
    ToolAuthorizationPolicy,
    ToolRisk,
)
from ai_platform.tools.execution import (
    RetryableToolError,
    ToolExecutionPolicy,
    ToolExecutionTimeoutError,
)
from ai_platform.tools.registry import ToolRegistry, ToolSpec

TEXT_SCHEMA: Mapping[str, object] = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}


def _dispatch(
    registry: ToolRegistry,
    *,
    raw_request: str,
    policy: ToolAuthorizationPolicy,
    sink: InMemoryToolAuditSink,
) -> object:
    return dispatch_mcp_tool_call(
        registry,
        request_id="mcp-request-001",
        raw_request=raw_request,
        authorization_policy=policy,
        execution_policy=ToolExecutionPolicy(timeout_seconds=0.5, max_attempts=2),
        audit_sink=sink,
    )


def test_dispatcher_revalidates_then_retries_a_reviewed_pure_tool_and_audits_once() -> None:
    attempts = 0

    def retry_once(arguments: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RetryableToolError("test-only transient failure")
        return {"text": arguments["text"]}

    registry = ToolRegistry(
        (
            ToolSpec(
                "reviewed_text", "재시도 dispatcher 테스트용 순수 Tool", TEXT_SCHEMA, retry_once
            ),
        )
    )
    sink = InMemoryToolAuditSink()

    result = _dispatch(
        registry,
        raw_request='{"name": "reviewed_text", "arguments": {"text": "safe"}}',
        policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.LOW}),
        sink=sink,
    )

    assert result.output == {"text": "safe"}
    assert attempts == 2
    assert sink.events[0].outcome is ToolAuditOutcome.SUCCEEDED
    assert sink.events[0].request_id == "mcp-request-001"
    assert "safe" not in str(asdict(sink.events[0]))


def test_dispatcher_requires_approval_before_any_high_risk_handler_call_and_audits_denial() -> None:
    calls = 0

    def handler(_: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    registry = ToolRegistry(
        (ToolSpec("reviewed_text", "승인 dispatcher 테스트용 순수 Tool", TEXT_SCHEMA, handler),)
    )
    sink = InMemoryToolAuditSink()

    with pytest.raises(ToolApprovalRequiredError, match="human approval is required"):
        _dispatch(
            registry,
            raw_request='{"name": "reviewed_text", "arguments": {"text": "not-logged"}}',
            policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.HIGH}),
            sink=sink,
        )

    assert calls == 0
    assert sink.events[0].outcome is ToolAuditOutcome.DENIED
    assert "not-logged" not in str(asdict(sink.events[0]))


def test_dispatcher_records_timeout_as_failed_and_releases_test_worker() -> None:
    started = Event()
    release = Event()

    def blocked_handler(_: Mapping[str, object]) -> Mapping[str, object]:
        started.set()
        release.wait(timeout=0.5)
        return {"ok": True}

    registry = ToolRegistry(
        (
            ToolSpec(
                "reviewed_text",
                "timeout dispatcher 테스트용 순수 Tool",
                TEXT_SCHEMA,
                blocked_handler,
            ),
        )
    )
    sink = InMemoryToolAuditSink()

    with pytest.raises(ToolExecutionTimeoutError, match="tool execution timed out"):
        dispatch_mcp_tool_call(
            registry,
            request_id="mcp-request-timeout",
            raw_request='{"name": "reviewed_text", "arguments": {"text": "safe"}}',
            authorization_policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.LOW}),
            execution_policy=ToolExecutionPolicy(timeout_seconds=0.01),
            audit_sink=sink,
        )
    release.set()

    assert started.is_set()
    assert sink.events[0].outcome is ToolAuditOutcome.FAILED


def test_dispatcher_rejects_invalid_transport_intent_before_audit_or_handler() -> None:
    calls = 0

    def handler(_: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    registry = ToolRegistry(
        (ToolSpec("reviewed_text", "parser dispatcher 테스트용 순수 Tool", TEXT_SCHEMA, handler),)
    )
    sink = InMemoryToolAuditSink()

    with pytest.raises(McpCallRequestError, match="unexpected key: id"):
        _dispatch(
            registry,
            raw_request=(
                '{"name": "reviewed_text", "arguments": {"text": "ignored"}, "id": "untrusted"}'
            ),
            policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.LOW}),
            sink=sink,
        )

    assert calls == 0
    assert sink.events == ()
    with pytest.raises(McpDispatchError, match="request_id must be a non-empty string"):
        dispatch_mcp_tool_call(
            registry,
            request_id=" ",
            raw_request='{"name": "reviewed_text", "arguments": {"text": "ignored"}}',
            authorization_policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.LOW}),
            execution_policy=ToolExecutionPolicy(timeout_seconds=0.5),
            audit_sink=sink,
        )
