"""Offline MCP STDIO resources/list projection; no real STDIO or Resource read occurs."""

from __future__ import annotations

import json

from ai_platform.mcp.resources import McpResourceCatalog, McpStaticResource
from ai_platform.mcp.stdio import MCP_PROTOCOL_VERSION, McpStdioSession

RESOURCE = McpStaticResource(
    uri="ai-platform://volume03/transport-boundary",
    name="Transport boundary note",
    mime_type="text/plain",
    text="Listing a resource does not read a file or execute a Tool.",
)


def main() -> None:
    """Run an in-memory handshake and list a fixed resource metadata snapshot."""
    session = McpStdioSession(resource_catalog=McpResourceCatalog((RESOURCE,)))
    session.receive_line(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "initialize-001",
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "offline-example", "version": "0.1.0"},
                },
            }
        )
        + "\n"
    )
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"resources-001","method":"resources/list","params":{}}\n'
    )
    if response_line is None:
        raise RuntimeError("resources/list must return a response")
    resource = json.loads(response_line)["result"]["resources"][0]
    print(f"{resource['uri']}: listed")


if __name__ == "__main__":
    main()
