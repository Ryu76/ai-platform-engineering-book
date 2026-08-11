"""Injected in-memory stream으로만 MCP STDIO process loop 경계를 실행한다."""
from __future__ import annotations

import io
import json

from ai_platform.mcp.stdio import MCP_PROTOCOL_VERSION, McpStdioSession, run_mcp_stdio_session


def main() -> None:
    """고정 handshake·잘못된 request·EOF를 실제 process I/O 없이 한 번 실행한다."""
    input_stream = io.StringIO(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "initialize-001",
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "volume03-example", "version": "0.1.0"},
                },
            }
        )
        + "\n"
        + '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
        + '{"jsonrpc":"1.0","id":"invalid-001","method":"tools/list","params":{}}\n'
    )
    output_stream = io.StringIO()

    stats = run_mcp_stdio_session(input_stream, output_stream, McpStdioSession())
    responses = [json.loads(line) for line in output_stream.getvalue().splitlines()]

    print(f"responses_written: {stats.responses_written}")
    print(f"invalid_request_code: {responses[-1]['error']['code']}")
    print(f"invalid_request_id: {responses[-1]['id']}")


if __name__ == "__main__":
    main()
