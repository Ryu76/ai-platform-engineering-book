"""Volume 03 MCP STDIO host의 shell-free allowlisted launch plan을 검증한다."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_platform.mcp.host import (
    McpStdioHostAllowlist,
    McpStdioHostError,
    McpStdioServerSpec,
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
