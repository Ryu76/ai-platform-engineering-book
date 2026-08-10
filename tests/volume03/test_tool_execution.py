"""Volume 03 Tool timeout/retry가 기존 allowlist 경계를 우회하지 않는지 검사한다."""
from __future__ import annotations

from collections.abc import Mapping
from threading import Event

import pytest

from ai_platform.tools.execution import (
    RetryableToolError,
    ToolExecutionPolicy,
    ToolExecutionTimeoutError,
    ToolRetryExhaustedError,
    execute_with_policy,
)
from ai_platform.tools.registry import (
    ToolArgumentsError,
    ToolNotAllowedError,
    ToolRegistry,
    ToolRegistryError,
    ToolSpec,
)

TEST_SCHEMA: Mapping[str, object] = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}


def test_retryable_pure_handler_succeeds_within_its_bounded_attempts() -> None:
    attempts = 0

    def flaky_handler(arguments: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RetryableToolError("test-only temporary failure")
        return {"text": arguments["text"]}

    tool = ToolSpec("flaky_text", "순수한 테스트 전용 재시도 Tool", TEST_SCHEMA, flaky_handler)

    result = execute_with_policy(
        ToolRegistry((tool,)),
        tool_name="flaky_text",
        arguments={"text": "stable"},
        policy=ToolExecutionPolicy(timeout_seconds=0.5, max_attempts=3),
    )

    assert result.output == {"text": "stable"}
    assert attempts == 3


def test_non_retryable_validation_and_allowlist_errors_are_not_retried() -> None:
    calls = 0

    def handler(_: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    registry = ToolRegistry((ToolSpec("guarded", "검증 경계 테스트 Tool", TEST_SCHEMA, handler),))
    policy = ToolExecutionPolicy(timeout_seconds=0.5, max_attempts=3)

    with pytest.raises(ToolArgumentsError, match="unexpected argument: path"):
        execute_with_policy(
            registry,
            tool_name="guarded",
            arguments={"text": "safe", "path": "not-used"},
            policy=policy,
        )
    with pytest.raises(ToolNotAllowedError, match="not allowlisted: delete_file"):
        execute_with_policy(
            registry,
            tool_name="delete_file",
            arguments={"text": "safe"},
            policy=policy,
        )

    assert calls == 0


def test_timeout_returns_without_retrying_an_unfinished_handler() -> None:
    started = Event()
    release = Event()

    def slow_handler(_: Mapping[str, object]) -> Mapping[str, object]:
        started.set()
        assert release.wait(timeout=1)
        return {"text": "released"}

    slow_tool = ToolSpec(
        "slow_text", "timeout 테스트 전용 순수 Tool", TEST_SCHEMA, slow_handler
    )
    registry = ToolRegistry((slow_tool,))

    with pytest.raises(ToolExecutionTimeoutError, match="timed out"):
        execute_with_policy(
            registry,
            tool_name="slow_text",
            arguments={"text": "safe"},
            policy=ToolExecutionPolicy(timeout_seconds=0.01, max_attempts=3),
        )

    assert started.is_set()
    release.set()


def test_retry_exhaustion_and_invalid_policies_are_rejected() -> None:
    def always_retryable(_: Mapping[str, object]) -> Mapping[str, object]:
        raise RetryableToolError("test-only temporary failure")

    registry = ToolRegistry(
        (ToolSpec("always_flaky", "계속 일시 실패하는 테스트 Tool", TEST_SCHEMA, always_retryable),)
    )
    with pytest.raises(ToolRetryExhaustedError, match="after 2 attempt"):
        execute_with_policy(
            registry,
            tool_name="always_flaky",
            arguments={"text": "safe"},
            policy=ToolExecutionPolicy(timeout_seconds=0.5, max_attempts=2),
        )
    with pytest.raises(ToolRegistryError, match="positive finite"):
        ToolExecutionPolicy(timeout_seconds=0)
    with pytest.raises(ToolRegistryError, match="from 1 through 3"):
        ToolExecutionPolicy(timeout_seconds=0.5, max_attempts=4)
