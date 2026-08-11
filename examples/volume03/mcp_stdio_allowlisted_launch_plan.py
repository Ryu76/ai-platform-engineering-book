"""MCP STDIO subprocess를 실행하지 않고 allowlisted launch plan만 확인한다."""
from __future__ import annotations

from ai_platform.mcp.host import McpStdioHostAllowlist, McpStdioServerSpec


def main() -> None:
    """고정 safe server spec을 선택해 process 없이 bounded host 설정을 출력한다."""
    allowlist = McpStdioHostAllowlist(
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
    )

    plan = allowlist.prepare_launch("safe-echo")
    print(f"server_name: {plan.server_name}")
    print(f"argv: {' '.join(plan.argv)}")
    print(f"stdout_limit_bytes: {plan.max_stdout_bytes}")
    print(f"restart_limit: {plan.restart_limit}")


if __name__ == "__main__":
    main()
