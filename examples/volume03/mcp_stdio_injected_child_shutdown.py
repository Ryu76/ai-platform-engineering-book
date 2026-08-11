"""Allowlisted MCP STDIO child shutdown을 fake process로만 확인한다."""
from __future__ import annotations

from ai_platform.mcp.host import (
    McpStdioChildProcess,
    McpStdioHostAllowlist,
    McpStdioServerSpec,
    shutdown_mcp_stdio_child,
)


class OfflineChild(McpStdioChildProcess):
    """실제 process나 signal 없이 graceful-stop 결과만 재현한다."""

    def poll(self) -> int | None:
        """예제 child가 아직 실행 중임을 나타낸다."""
        return None

    def terminate(self) -> None:
        """메모리 fake에서는 OS signal을 보내지 않는다."""

    def wait(self, timeout: float) -> int | None:
        """graceful terminate 뒤 고정 exit code를 즉시 반환한다."""
        del timeout
        return 0

    def kill(self) -> None:
        """이 예제의 graceful path는 force-kill에 도달하지 않는다."""
        raise RuntimeError("force-kill must not be used by this offline example")


def main() -> None:
    """allowlisted plan과 injected fake child만으로 finite shutdown을 확인한다."""
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

    result = shutdown_mcp_stdio_child(plan, OfflineChild())
    print(f"server_name: {result.server_name}")
    print(f"exit_code: {result.exit_code}")
    print(f"termination_requested: {result.termination_requested}")
    print(f"force_killed: {result.force_killed}")


if __name__ == "__main__":
    main()
