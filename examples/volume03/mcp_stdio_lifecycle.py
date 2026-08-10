"""교육용 MCP STDIO lifecycle adapter는 framing만 검증하고 Tool을 실행하지 않는다."""
from __future__ import annotations

import json

from ai_platform.mcp.stdio import MCP_PROTOCOL_VERSION, McpStdioSession


def main() -> None:
    """고정 initialize handshake 두 message를 메모리에서 검증한다; 실제 STDIO는 열지 않는다."""
    session = McpStdioSession()
    initialize_line = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "offline-initialize-001",
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "offline-example", "version": "0.1.0"},
            },
        }
    ) + "\n"
    response_line = session.receive_line(initialize_line)
    if response_line is None:
        raise RuntimeError("initialize request must produce a response")
    response = json.loads(response_line)
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    print(f"{response['result']['protocolVersion']}: {session.state.value}")


if __name__ == "__main__":
    main()
