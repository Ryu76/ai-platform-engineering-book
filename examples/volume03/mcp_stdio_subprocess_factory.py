"""OS-specific MCP STDIO Popen adapter를 fake factory로만 확인한다."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from ai_platform.mcp.host import (
    McpStdioChildProcess,
    McpStdioHostAllowlist,
    McpStdioServerSpec,
    start_mcp_stdio_child,
)
from ai_platform.mcp.subprocess_factory import (
    McpStdioPopenProcess,
    McpStdioSubprocessConfig,
    McpStdioSubprocessFactory,
)


class OfflinePopenProcess(McpStdioPopenProcess):
    """실제 process·pipe·signal 없이 Popen shutdown API만 메모리에서 흉내 낸다."""

    def poll(self) -> int | None:
        return 0

    def terminate(self) -> None:
        return None

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        return 0

    def kill(self) -> None:
        return None


class OfflinePopen:
    """Popen을 호출하지 않고 fixed subprocess kwargs만 기록한다."""

    def __init__(self) -> None:
        self.argv: tuple[str, ...] = ()
        self.shell: Literal[False] = False
        self.call_count = 0

    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        stdin: int,
        stdout: int,
        stderr: int,
        shell: Literal[False],
        cwd: str,
        env: Mapping[str, str],
        text: Literal[False],
        bufsize: int,
        close_fds: bool,
    ) -> McpStdioPopenProcess:
        del stdin, stdout, stderr, cwd, env, text, bufsize, close_fds
        self.argv = argv
        self.shell = shell
        self.call_count += 1
        return OfflinePopenProcess()


def main() -> None:
    """allowlisted plan과 trusted config이 fake Popen seam에만 도달함을 출력한다."""
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
    fake_popen = OfflinePopen()
    factory = McpStdioSubprocessFactory(
        McpStdioSubprocessConfig(cwd=str(Path.cwd()), environment={"PATH": "C:/trusted/bin"}),
        popen_factory=fake_popen,
    )

    child: McpStdioChildProcess = start_mcp_stdio_child(plan, factory)
    print(f"argv: {' '.join(fake_popen.argv)}")
    print(f"shell: {fake_popen.shell}")
    print(f"popen_calls: {fake_popen.call_count}")
    print(f"child_already_exited: {child.poll() == 0}")


if __name__ == "__main__":
    main()
