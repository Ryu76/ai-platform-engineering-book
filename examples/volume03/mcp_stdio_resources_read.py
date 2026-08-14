"""Offline MCP STDIO resources/read snapshot; no real STDIO or resource loader occurs."""

from __future__ import annotations

import json

from ai_platform.mcp.resources import McpResourceCatalog, McpStaticResource
from ai_platform.mcp.stdio import MCP_PROTOCOL_VERSION, McpStdioSession

RESOURCE = McpStaticResource(
    uri="ai-platform://volume03/transport-boundary",
    name="Transport boundary note",
    mime_type="text/plain",
    text="Reading this resource does not read a file or execute a Tool.",
)


def main() -> None:
    """Run an in-memory handshake and read one fixed allowlisted Resource."""
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
        '{"jsonrpc":"2.0","id":"resource-001","method":"resources/read",'
        '"params":{"uri":"ai-platform://volume03/transport-boundary"}}\n'
    )
    if response_line is None:
        raise RuntimeError("resources/read must return a response")
    resource = json.loads(response_line)["result"]["contents"][0]
    print(f"{resource['uri']}: fixed snapshot")


if __name__ == "__main__":
    main()
