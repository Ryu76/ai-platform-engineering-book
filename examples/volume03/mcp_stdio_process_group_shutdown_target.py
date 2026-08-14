"""MCP STDIO child-owned POSIX group shutdown intent를 in-memory fake sender로만 확인한다."""

from __future__ import annotations

from ai_platform.mcp.host import McpStdioHostAllowlist, McpStdioServerSpec
from ai_platform.mcp.process_group import (
    McpStdioGroupShutdownPhase,
    McpStdioGroupShutdownTarget,
    McpStdioIsolatedChildGroup,
    McpStdioProcessPlatform,
    send_mcp_stdio_group_shutdown_target,
)


class OfflineGroupShutdownSender:
    """OS signal, process group 또는 Job Object 없이 target snapshot만 기록한다."""

    def __init__(self) -> None:
        self.targets: list[McpStdioGroupShutdownTarget] = []

    def send(self, target: McpStdioGroupShutdownTarget) -> None:
        """메모리 목록에 typed intent만 넣고 외부 action은 수행하지 않는다."""
        self.targets.append(target)


def main() -> None:
    """allowlisted plan과 trusted fake fixture로 one-shot graceful intent를 만든다."""
    plan = McpStdioHostAllowlist(
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
    group = McpStdioIsolatedChildGroup(
        platform=McpStdioProcessPlatform.POSIX,
        child_pid=4120,
        isolation_owner_pid=4120,
        shutdown_scope_id=4120,
    )
    sender = OfflineGroupShutdownSender()

    target = send_mcp_stdio_group_shutdown_target(
        plan, group, McpStdioGroupShutdownPhase.GRACEFUL, sender
    )
    print(f"server_name: {target.server_name}")
    print(f"platform: {target.platform}")
    print(f"target_kind: {target.target_kind}")
    print(f"phase: {target.phase}")
    print(f"offline_sender_calls: {len(sender.targets)}")


if __name__ == "__main__":
    main()
