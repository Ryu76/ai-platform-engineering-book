"""Allowlisted MCP STDIO child factory 경계를 in-memory fake로만 확인한다."""
from __future__ import annotations

from typing import Literal

from ai_platform.mcp.host import (
    McpStdioChildProcess,
    McpStdioHostAllowlist,
    McpStdioServerSpec,
    start_mcp_stdio_child,
)


class OfflineChild(McpStdioChildProcess):
    """실제 process, pipe, signal 없이 최소 child contract만 구현한다."""

    def poll(self) -> int | None:
        return 0

    def terminate(self) -> None:
        return None

    def wait(self, timeout: float) -> int | None:
        del timeout
        return 0

    def kill(self) -> None:
        return None


class OfflineFactory:
    """OS process 대신 host가 전달한 고정 launch 값만 보관한다."""

    def __init__(self) -> None:
        self.argv: tuple[str, ...] = ()
        self.shell: Literal[False] = False

    def start(
        self,
        *,
        argv: tuple[str, ...],
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        shell: Literal[False],
    ) -> McpStdioChildProcess:
        del max_stdout_bytes, max_stderr_bytes
        self.argv = argv
        self.shell = shell
        return OfflineChild()


def main() -> None:
    """allowlisted plan이 fake factory에 고정 argv와 shell=False만 전달함을 출력한다."""
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
    factory = OfflineFactory()

    child = start_mcp_stdio_child(plan, factory)
    print(f"server_name: {plan.server_name}")
    print(f"argv: {' '.join(factory.argv)}")
    print(f"shell: {factory.shell}")
    print(f"child_already_exited: {child.poll() == 0}")


if __name__ == "__main__":
    main()
