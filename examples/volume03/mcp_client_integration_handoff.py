"""Hermes/Codex MCP client handoff을 actual config·connection 없이 확인한다."""

from __future__ import annotations

from ai_platform.mcp.catalog import McpServerCatalog
from ai_platform.mcp.client_handoff import (
    McpClientKind,
    McpClientToolVisibilityPolicy,
    prepare_mcp_client_integration_handoff,
)
from ai_platform.mcp.host import McpStdioHostAllowlist, McpStdioServerSpec
from ai_platform.tools.registry import SAFE_CALCULATOR, SAFE_TEXT_CASE, ToolRegistry


def main() -> None:
    """allowlisted plan/catalog/policy를 memory에서 조합할 뿐 client나 Tool을 호출하지 않는다."""
    plan = McpStdioHostAllowlist(
        (
            McpStdioServerSpec(
                name="safe-tools",
                argv=("offline-mcp-server",),
                max_stdout_bytes=1_024,
                max_stderr_bytes=1_024,
                shutdown_grace_seconds=1.0,
                restart_limit=0,
            ),
        )
    ).prepare_launch("safe-tools")
    catalog = McpServerCatalog.from_registry(ToolRegistry((SAFE_CALCULATOR, SAFE_TEXT_CASE)))
    handoff = prepare_mcp_client_integration_handoff(
        plan,
        catalog,
        McpClientToolVisibilityPolicy(
            client=McpClientKind.HERMES_AGENT,
            tool_names=("safe_calculator",),
        ),
    )

    print(f"client: {handoff.client}")
    print(f"server_name: {handoff.server_name}")
    print(f"visible_tools: {','.join(handoff.tool_names)}")


if __name__ == "__main__":
    main()
