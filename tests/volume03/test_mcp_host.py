"""Volume 03 MCP STDIO host의 shell-free allowlisted launch plan을 검증한다."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_platform.mcp.host import (
    McpStdioHostAllowlist,
    McpStdioHostError,
    McpStdioHostLaunchPlan,
    McpStdioServerSpec,
    shutdown_mcp_stdio_child,
)


def _safe_server(*, name: str = "safe-echo") -> McpStdioServerSpec:
    return McpStdioServerSpec(
        name=name,
        argv=("volume03-safe-echo-server", "--stdio"),
        max_stdout_bytes=16_384,
        max_stderr_bytes=4_096,
        shutdown_grace_seconds=2.0,
        restart_limit=0,
    )


def test_allowlisted_server_returns_immutable_static_shell_free_launch_plan() -> None:
    allowlist = McpStdioHostAllowlist((_safe_server(),))

    plan = allowlist.prepare_launch("safe-echo")

    assert plan.server_name == "safe-echo"
    assert plan.argv == ("volume03-safe-echo-server", "--stdio")
    assert plan.max_stdout_bytes == 16_384
    assert plan.max_stderr_bytes == 4_096
    assert plan.shutdown_grace_seconds == 2.0
    assert plan.restart_limit == 0
    with pytest.raises(FrozenInstanceError):
        plan.restart_limit = 3  # type: ignore[misc]


def test_public_launch_plan_constructor_keeps_the_same_finite_budget_validation() -> None:
    with pytest.raises(McpStdioHostError, match="shutdown_grace_seconds"):
        McpStdioHostLaunchPlan(
            server_name="safe-echo",
            argv=("volume03-safe-echo-server", "--stdio"),
            max_stdout_bytes=16_384,
            max_stderr_bytes=4_096,
            shutdown_grace_seconds=0.0,
            restart_limit=0,
        )


def test_allowlist_rejects_unknown_or_non_string_server_selector_without_leaking_commands() -> None:
    allowlist = McpStdioHostAllowlist((_safe_server(),))

    for selector in ("other-server", "safe-echo ", 1):
        with pytest.raises(McpStdioHostError, match="not allowlisted"):
            allowlist.prepare_launch(selector)  # type: ignore[arg-type]


def test_allowlist_rejects_duplicate_or_mutable_server_configuration() -> None:
    with pytest.raises(McpStdioHostError, match="duplicate"):
        McpStdioHostAllowlist((_safe_server(), _safe_server()))
    with pytest.raises(McpStdioHostError, match="non-empty tuple"):
        McpStdioHostAllowlist(())
    with pytest.raises(McpStdioHostError, match="non-empty tuple"):
        McpStdioHostAllowlist([_safe_server()])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"name": "Safe-Echo"}, "server name"),
        ({"name": "-safe-echo"}, "server name"),
        ({"argv": "volume03-safe-echo-server --stdio"}, "argv must be a tuple"),
        ({"argv": ("volume03-safe-echo-server\n--stdio",)}, "argv arguments"),
        ({"max_stdout_bytes": 1023}, "max_stdout_bytes"),
        ({"max_stderr_bytes": True}, "max_stderr_bytes"),
        ({"shutdown_grace_seconds": float("inf")}, "shutdown_grace_seconds"),
        ({"shutdown_grace_seconds": 0.0}, "shutdown_grace_seconds"),
        ({"restart_limit": 4}, "restart_limit"),
        ({"restart_limit": True}, "restart_limit"),
    ),
)
def test_server_spec_rejects_unbounded_or_ambiguous_host_configuration(
    changes: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "name": "safe-echo",
        "argv": ("volume03-safe-echo-server", "--stdio"),
        "max_stdout_bytes": 16_384,
        "max_stderr_bytes": 4_096,
        "shutdown_grace_seconds": 2.0,
        "restart_limit": 0,
    }
    values.update(changes)

    with pytest.raises(McpStdioHostError, match=message):
        McpStdioServerSpec(**values)  # type: ignore[arg-type]


def test_server_names_are_the_reviewable_static_allowlist_order() -> None:
    allowlist = McpStdioHostAllowlist(
        (_safe_server(name="safe-echo"), _safe_server(name="safe-case"))
    )

    assert allowlist.server_names() == ("safe-echo", "safe-case")


class _FakeChild:
    """OS process 대신 shutdown call order만 기록하는 injected test double이다."""

    def __init__(self, *, poll_result: int | None, wait_results: list[int | None]) -> None:
        self.poll_result = poll_result
        self.wait_results = wait_results
        self.actions: list[str] = []
        self.wait_timeouts: list[float] = []

    def poll(self) -> int | None:
        self.actions.append("poll")
        return self.poll_result

    def terminate(self) -> None:
        self.actions.append("terminate")

    def wait(self, timeout: float) -> int | None:
        self.actions.append("wait")
        self.wait_timeouts.append(timeout)
        return self.wait_results.pop(0)

    def kill(self) -> None:
        self.actions.append("kill")


def _shutdown_plan() -> McpStdioHostLaunchPlan:
    return McpStdioHostAllowlist((_safe_server(),)).prepare_launch("safe-echo")


def test_shutdown_returns_existing_exit_without_sending_any_stop_signal() -> None:
    child = _FakeChild(poll_result=17, wait_results=[])

    result = shutdown_mcp_stdio_child(_shutdown_plan(), child)

    assert result.exit_code == 17
    assert result.termination_requested is False
    assert result.force_killed is False
    assert child.actions == ["poll"]


def test_shutdown_requests_graceful_stop_once_and_uses_plan_grace_period() -> None:
    child = _FakeChild(poll_result=None, wait_results=[0])

    result = shutdown_mcp_stdio_child(_shutdown_plan(), child)

    assert result.server_name == "safe-echo"
    assert result.exit_code == 0
    assert result.termination_requested is True
    assert result.force_killed is False
    assert child.actions == ["poll", "terminate", "wait"]
    assert child.wait_timeouts == [2.0]


def test_shutdown_force_kills_once_only_after_grace_period_expires() -> None:
    child = _FakeChild(poll_result=None, wait_results=[None, -9])

    result = shutdown_mcp_stdio_child(_shutdown_plan(), child)

    assert result.exit_code == -9
    assert result.termination_requested is True
    assert result.force_killed is True
    assert child.actions == ["poll", "terminate", "wait", "kill", "wait"]
    assert child.wait_timeouts == [2.0, 0.0]


def test_shutdown_rejects_child_that_remains_alive_after_force_kill() -> None:
    child = _FakeChild(poll_result=None, wait_results=[None, None])

    with pytest.raises(McpStdioHostError, match="did not exit"):
        shutdown_mcp_stdio_child(_shutdown_plan(), child)

    assert child.actions == ["poll", "terminate", "wait", "kill", "wait"]


@pytest.mark.parametrize("bad_exit_code", (True, "zero"))
def test_shutdown_rejects_ambiguous_child_exit_code(bad_exit_code: object) -> None:
    child = _FakeChild(poll_result=bad_exit_code, wait_results=[])  # type: ignore[arg-type]

    with pytest.raises(McpStdioHostError, match="invalid exit code"):
        shutdown_mcp_stdio_child(_shutdown_plan(), child)


class _PollFailingChild(_FakeChild):
    def poll(self) -> int | None:
        raise RuntimeError("internal process detail")


def test_shutdown_hides_child_adapter_exception_detail() -> None:
    child = _PollFailingChild(poll_result=None, wait_results=[])

    with pytest.raises(McpStdioHostError, match="child poll failed") as error:
        shutdown_mcp_stdio_child(_shutdown_plan(), child)

    assert "internal process detail" not in str(error.value)
