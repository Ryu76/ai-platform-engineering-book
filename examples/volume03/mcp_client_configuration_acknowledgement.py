"""MCP client configuration acknowledgement를 actual client/config 없이 대조한다."""

from __future__ import annotations

from ai_platform.mcp.client_acknowledgement import (
    McpClientConfigurationAcknowledgement,
    McpClientConfigurationApplication,
    verify_mcp_client_configuration_acknowledgement,
)
from ai_platform.mcp.client_handoff import (
    McpClientIntegrationHandoff,
    McpClientKind,
)


def main() -> None:
    """fixed in-memory snapshots만 대조하며 client, file, credential, Tool을 호출하지 않는다."""
    application = McpClientConfigurationApplication(
        handoff=McpClientIntegrationHandoff(
            client=McpClientKind.HERMES_AGENT,
            server_name="safe-tools",
            tool_names=("safe_calculator",),
        ),
        configuration_generation="volume03-demo-001",
    )
    verified = verify_mcp_client_configuration_acknowledgement(
        application,
        McpClientConfigurationAcknowledgement(
            client=McpClientKind.HERMES_AGENT,
            server_name="safe-tools",
            tool_names=("safe_calculator",),
            configuration_generation="volume03-demo-001",
        ),
    )

    print(f"client: {verified.client}")
    print(f"server_name: {verified.server_name}")
    print(f"visible_tools: {','.join(verified.tool_names)}")
    print(f"configuration_generation: {application.configuration_generation}")


if __name__ == "__main__":
    main()
