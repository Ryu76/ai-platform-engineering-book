"""Offline MCP STDIO prompts/get snapshot; no real STDIO or prompt rendering occurs."""

from __future__ import annotations

import json

from ai_platform.mcp.prompts import McpPromptCatalog, McpPromptMessage, McpStaticPrompt
from ai_platform.mcp.stdio import MCP_PROTOCOL_VERSION, McpStdioSession

PROMPT = McpStaticPrompt(
    name="review-tool-boundary",
    description="Reviews the fixed Tool Calling safety boundary.",
    messages=(
        McpPromptMessage(
            role="system",
            content="Review allowlist and approval boundaries without executing Tools.",
        ),
    ),
)


def main() -> None:
    """Run an in-memory handshake and retrieve one fixed allowlisted Prompt."""
    session = McpStdioSession(prompt_catalog=McpPromptCatalog((PROMPT,)))
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
        '{"jsonrpc":"2.0","id":"prompt-001","method":"prompts/get",'
        '"params":{"name":"review-tool-boundary","arguments":{}}}\n'
    )
    if response_line is None:
        raise RuntimeError("prompts/get must return a response")
    prompt = json.loads(response_line)["result"]
    print(f"{prompt['name']}: fixed snapshot")


if __name__ == "__main__":
    main()
