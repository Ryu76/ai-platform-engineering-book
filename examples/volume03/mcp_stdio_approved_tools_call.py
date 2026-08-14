"""Offline high-risk MCP tools/call using a host-bound approval and one pure Tool."""

from __future__ import annotations

import json

from ai_platform.mcp.stdio import (
    MCP_PROTOCOL_VERSION,
    McpStdioSession,
    McpToolCallBoundary,
    mcp_stdio_request_correlation_id,
)
from ai_platform.tools.audit import InMemoryToolAuditSink
from ai_platform.tools.authorization import ApprovalGrant, ToolAuthorizationPolicy, ToolRisk
from ai_platform.tools.execution import ToolExecutionPolicy
from ai_platform.tools.registry import SAFE_TEXT_CASE, ToolRegistry

REQUEST_ID = "approved-call-001"
ARGUMENTS = {"text": "Mcp", "operation": "upper"}


def main() -> None:
    """Run an in-memory handshake and one pre-approved pure text transformation."""
    approval = ApprovalGrant.for_request(
        approval_id="offline-approval-001",
        request_id=mcp_stdio_request_correlation_id(REQUEST_ID),
        tool_name="safe_text_case",
        arguments=ARGUMENTS,
    )
    session = McpStdioSession(
        tool_call_boundary=McpToolCallBoundary(
            registry=ToolRegistry((SAFE_TEXT_CASE,)),
            authorization_policy=ToolAuthorizationPolicy({"safe_text_case": ToolRisk.HIGH}),
            execution_policy=ToolExecutionPolicy(timeout_seconds=0.5),
            audit_sink=InMemoryToolAuditSink(),
            approval=approval,
        )
    )
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
        '{"jsonrpc":"2.0","id":"approved-call-001","method":"tools/call","params":'
        '{"name":"safe_text_case","arguments":{"text":"Mcp","operation":"upper"}}}\n'
    )
    if response_line is None:
        raise RuntimeError("tools/call must return a response")
    output = json.loads(response_line)["result"]["content"][0]["text"]
    print(f"approved_safe_text_case: {json.loads(output)['text']}")


if __name__ == "__main__":
    main()
