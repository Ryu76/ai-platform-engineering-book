"""Volume 03 MCP STDIO child-owned process group shutdown intent를 검증한다."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_platform.mcp.host import McpStdioHostAllowlist, McpStdioHostLaunchPlan, McpStdioServerSpec
from ai_platform.mcp.process_group import (
    McpStdioGroupShutdownPhase,
    McpStdioGroupShutdownTargetKind,
    McpStdioIsolatedChildGroup,
    McpStdioProcessGroupError,
    McpStdioProcessPlatform,
    prepare_mcp_stdio_group_shutdown_target,
    send_mcp_stdio_group_shutdown_target,
)


def _plan() -> McpStdioHostLaunchPlan:
    return McpStdioHostAllowlist(
        (
            McpStdioServerSpec(
                name="safe-echo",
                argv=("volume03-safe-echo-server", "--stdio"),
                max_stdout_bytes=16_384,
                max_stderr_bytes=4_096,
                shutdown_grace_seconds=2.0,
                restart_limit=0,
            ),
        )
    ).prepare_launch("safe-echo")


class _RecordingSender:
    def __init__(self) -> None:
        self.targets: list[object] = []

    def send(self, target: object) -> None:
        self.targets.append(target)


def test_posix_child_owned_process_group_sends_one_graceful_typed_target() -> None:
    sender = _RecordingSender()
    group = McpStdioIsolatedChildGroup(
        platform=McpStdioProcessPlatform.POSIX,
        child_pid=4120,
        isolation_owner_pid=4120,
        shutdown_scope_id=4120,
    )

    target = send_mcp_stdio_group_shutdown_target(
        _plan(), group, McpStdioGroupShutdownPhase.GRACEFUL, sender
    )

    assert target.server_name == "safe-echo"
    assert target.target_kind is McpStdioGroupShutdownTargetKind.POSIX_PROCESS_GROUP
    assert target.shutdown_scope_id == 4120
    assert target.phase is McpStdioGroupShutdownPhase.GRACEFUL
    assert sender.targets == [target]


def test_windows_child_owned_job_scope_sends_one_force_typed_target() -> None:
    sender = _RecordingSender()
    group = McpStdioIsolatedChildGroup(
        platform=McpStdioProcessPlatform.WINDOWS,
        child_pid=733,
        isolation_owner_pid=733,
        shutdown_scope_id=91_001,
    )

    target = send_mcp_stdio_group_shutdown_target(
        _plan(), group, McpStdioGroupShutdownPhase.FORCE, sender
    )

    assert target.target_kind is McpStdioGroupShutdownTargetKind.WINDOWS_JOB
    assert target.shutdown_scope_id == 91_001
    assert target.phase is McpStdioGroupShutdownPhase.FORCE
    assert sender.targets == [target]


def test_foreign_group_owner_is_rejected_before_any_sender_call() -> None:
    sender = _RecordingSender()

    with pytest.raises(McpStdioProcessGroupError, match="not owned"):
        McpStdioIsolatedChildGroup(
            platform=McpStdioProcessPlatform.WINDOWS,
            child_pid=733,
            isolation_owner_pid=734,
            shutdown_scope_id=91_001,
        )

    assert sender.targets == []


def test_posix_group_not_led_by_child_is_rejected_before_any_sender_call() -> None:
    sender = _RecordingSender()

    with pytest.raises(McpStdioProcessGroupError, match="leader does not match"):
        McpStdioIsolatedChildGroup(
            platform=McpStdioProcessPlatform.POSIX,
            child_pid=4120,
            isolation_owner_pid=4120,
            shutdown_scope_id=4121,
        )

    assert sender.targets == []


def test_unsupported_platform_is_rejected_before_any_sender_call() -> None:
    sender = _RecordingSender()

    with pytest.raises(McpStdioProcessGroupError, match="platform is unsupported"):
        McpStdioIsolatedChildGroup(
            platform="darwin",  # type: ignore[arg-type]
            child_pid=4120,
            isolation_owner_pid=4120,
            shutdown_scope_id=4120,
        )

    assert sender.targets == []


def test_invalid_launch_plan_never_reaches_sender() -> None:
    sender = _RecordingSender()
    group = McpStdioIsolatedChildGroup(
        platform=McpStdioProcessPlatform.POSIX,
        child_pid=4120,
        isolation_owner_pid=4120,
        shutdown_scope_id=4120,
    )

    with pytest.raises(McpStdioProcessGroupError, match="launch plan is invalid"):
        send_mcp_stdio_group_shutdown_target(
            object(),
            group,
            McpStdioGroupShutdownPhase.GRACEFUL,
            sender,  # type: ignore[arg-type]
        )

    assert sender.targets == []


def test_invalid_shutdown_phase_never_reaches_sender() -> None:
    sender = _RecordingSender()
    group = McpStdioIsolatedChildGroup(
        platform=McpStdioProcessPlatform.POSIX,
        child_pid=4120,
        isolation_owner_pid=4120,
        shutdown_scope_id=4120,
    )

    with pytest.raises(McpStdioProcessGroupError, match="shutdown phase is invalid"):
        send_mcp_stdio_group_shutdown_target(_plan(), group, "stop", sender)  # type: ignore[arg-type]

    assert sender.targets == []


@pytest.mark.parametrize("bad_pid", (0, -1, True, "4120"))
def test_invalid_group_identity_is_rejected(bad_pid: object) -> None:
    with pytest.raises(McpStdioProcessGroupError, match="child pid is invalid"):
        McpStdioIsolatedChildGroup(
            platform=McpStdioProcessPlatform.POSIX,
            child_pid=bad_pid,  # type: ignore[arg-type]
            isolation_owner_pid=4120,
            shutdown_scope_id=4120,
        )


def test_sender_failure_is_hidden_without_retry_or_escalation() -> None:
    class _FailingSender:
        def __init__(self) -> None:
            self.calls = 0

        def send(self, target: object) -> None:
            del target
            self.calls += 1
            raise RuntimeError("private platform signal detail")

    sender = _FailingSender()
    group = McpStdioIsolatedChildGroup(
        platform=McpStdioProcessPlatform.POSIX,
        child_pid=4120,
        isolation_owner_pid=4120,
        shutdown_scope_id=4120,
    )

    with pytest.raises(McpStdioProcessGroupError, match="shutdown request failed") as error:
        send_mcp_stdio_group_shutdown_target(
            _plan(), group, McpStdioGroupShutdownPhase.FORCE, sender
        )

    assert "private platform signal detail" not in str(error.value)
    assert sender.calls == 1


def test_prepared_target_is_immutable_and_requires_platform_matching_kind() -> None:
    group = McpStdioIsolatedChildGroup(
        platform=McpStdioProcessPlatform.POSIX,
        child_pid=4120,
        isolation_owner_pid=4120,
        shutdown_scope_id=4120,
    )
    target = prepare_mcp_stdio_group_shutdown_target(
        _plan(), group, McpStdioGroupShutdownPhase.GRACEFUL
    )

    with pytest.raises(FrozenInstanceError):
        target.phase = McpStdioGroupShutdownPhase.FORCE  # type: ignore[misc]
    with pytest.raises(McpStdioProcessGroupError, match="target kind is invalid"):
        type(target)(
            server_name="safe-echo",
            platform=McpStdioProcessPlatform.POSIX,
            target_kind=McpStdioGroupShutdownTargetKind.WINDOWS_JOB,
            shutdown_scope_id=4120,
            phase=McpStdioGroupShutdownPhase.GRACEFUL,
        )
