"""Offline MCP STDIO tools/list projection; no real STDIO or Tool execution occurs."""
from __future__ import annotations

import json

from ai_platform.mcp.catalog import McpServerCatalog
from ai_platform.mcp.stdio import MCP_PROTOCOL_VERSION, McpStdioSession
from ai_platform.tools.registry import SAFE_CALCULATOR, SAFE_TEXT_CASE, ToolRegistry


def main() -> None:
    """Run a fixed in-memory handshake and inspect the allowlisted catalog response."""
    catalog = McpServerCatalog.from_registry(ToolRegistry((SAFE_CALCULATOR, SAFE_TEXT_CASE)))
    session = McpStdioSession(catalog=catalog)
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
        '{"jsonrpc":"2.0","id":"list-001","method":"tools/list","params":{}}\n'
    )
    if response_line is None:
        raise RuntimeError("tools/list must return a response")
    tool_names = ", ".join(tool["name"] for tool in json.loads(response_line)["result"]["tools"])
    print(f"{tool_names}: listed")


if __name__ == "__main__":
    main()
