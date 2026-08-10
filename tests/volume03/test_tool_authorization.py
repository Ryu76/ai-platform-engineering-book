"""Volume 03 위험도·사람 승인이 allowlist와 Schema를 우회하지 않는지 검사한다."""
from __future__ import annotations

from collections.abc import Mapping

import pytest

from ai_platform.tools.authorization import (
    ApprovalGrant,
    ToolApprovalMismatchError,
    ToolApprovalRequiredError,
    ToolAuthorizationError,
    ToolAuthorizationPolicy,
    ToolRisk,
    execute_authorized,
)
from ai_platform.tools.registry import (
    ToolArgumentsError,
    ToolNotAllowedError,
    ToolRegistry,
    ToolSpec,
)

TEST_SCHEMA: Mapping[str, object] = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}


def _grant(*, request_id: str = "request-1", text: str = "approved") -> ApprovalGrant:
    return ApprovalGrant.for_request(
        approval_id="approval-1",
        request_id=request_id,
        tool_name="reviewed_text",
        arguments={"text": text},
    )


def test_high_risk_tool_executes_only_after_its_exact_request_is_approved() -> None:
    calls = 0

    def handler(arguments: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return {"text": arguments["text"]}

    registry = ToolRegistry(
        (ToolSpec("reviewed_text", "순수 승인 경계 테스트 Tool", TEST_SCHEMA, handler),)
    )
    result = execute_authorized(
        registry,
        request_id="request-1",
        tool_name="reviewed_text",
        arguments={"text": "approved"},
        policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.HIGH}),
        approval=_grant(),
    )

    assert result.output == {"text": "approved"}
    assert calls == 1


def test_high_risk_tool_without_approval_never_reaches_its_handler() -> None:
    calls = 0

    def handler(_: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    registry = ToolRegistry(
        (ToolSpec("reviewed_text", "순수 승인 경계 테스트 Tool", TEST_SCHEMA, handler),)
    )
    with pytest.raises(ToolApprovalRequiredError, match="human approval is required"):
        execute_authorized(
            registry,
            request_id="request-1",
            tool_name="reviewed_text",
            arguments={"text": "blocked"},
            policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.HIGH}),
        )

    assert calls == 0


@pytest.mark.parametrize(
    ("request_id", "arguments", "message"),
    [
        ("request-2", {"text": "approved"}, "does not match"),
        ("request-1", {"text": "changed"}, "does not match"),
    ],
)
def test_approval_cannot_be_reused_for_a_different_request_or_arguments(
    request_id: str, arguments: dict[str, object], message: str
) -> None:
    calls = 0

    def handler(_: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    registry = ToolRegistry(
        (ToolSpec("reviewed_text", "순수 승인 경계 테스트 Tool", TEST_SCHEMA, handler),)
    )
    with pytest.raises(ToolApprovalMismatchError, match=message):
        execute_authorized(
            registry,
            request_id=request_id,
            tool_name="reviewed_text",
            arguments=arguments,
            policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.HIGH}),
            approval=_grant(),
        )

    assert calls == 0


def test_approval_never_bypasses_allowlist_or_schema_validation() -> None:
    calls = 0

    def handler(_: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    registry = ToolRegistry(
        (ToolSpec("reviewed_text", "순수 승인 경계 테스트 Tool", TEST_SCHEMA, handler),)
    )
    policy = ToolAuthorizationPolicy({"reviewed_text": ToolRisk.HIGH})

    with pytest.raises(ToolArgumentsError, match="unexpected argument: path"):
        execute_authorized(
            registry,
            request_id="request-1",
            tool_name="reviewed_text",
            arguments={"text": "approved", "path": "not-used"},
            policy=policy,
            approval=_grant(),
        )
    with pytest.raises(ToolNotAllowedError, match="not allowlisted: delete_file"):
        execute_authorized(
            registry,
            request_id="request-1",
            tool_name="delete_file",
            arguments={"text": "approved"},
            policy=policy,
            approval=_grant(),
        )

    assert calls == 0


def test_low_risk_tool_needs_no_approval_but_missing_risk_policy_is_denied() -> None:
    registry = ToolRegistry(
        (
            ToolSpec(
                "reviewed_text",
                "순수 승인 경계 테스트 Tool",
                TEST_SCHEMA,
                lambda arguments: {"text": arguments["text"]},
            ),
        )
    )
    assert execute_authorized(
        registry,
        request_id="request-1",
        tool_name="reviewed_text",
        arguments={"text": "low-risk"},
        policy=ToolAuthorizationPolicy({"reviewed_text": ToolRisk.LOW}),
    ).output == {"text": "low-risk"}

    with pytest.raises(ToolAuthorizationError, match="no authorization policy"):
        execute_authorized(
            registry,
            request_id="request-1",
            tool_name="reviewed_text",
            arguments={"text": "blocked"},
            policy=ToolAuthorizationPolicy({"other_tool": ToolRisk.LOW}),
        )
