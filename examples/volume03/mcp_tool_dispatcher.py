"""검증된 MCP Tool 요청을 승인·timeout·감사 경계에 묶어 순수 Tool만 dispatch한다."""
from __future__ import annotations

from ai_platform.mcp.dispatcher import dispatch_mcp_tool_call
from ai_platform.tools.audit import InMemoryToolAuditSink
from ai_platform.tools.authorization import ToolAuthorizationPolicy, ToolRisk
from ai_platform.tools.execution import ToolExecutionPolicy
from ai_platform.tools.registry import SAFE_TEXT_CASE, ToolRegistry


def main() -> None:
    """고정 JSON 요청 하나를 allowlist의 문자열 변환 Tool로만 안전하게 dispatch한다."""
    sink = InMemoryToolAuditSink()
    result = dispatch_mcp_tool_call(
        ToolRegistry((SAFE_TEXT_CASE,)),
        request_id="offline-mcp-001",
        raw_request=(
            '{"name": "safe_text_case", "arguments": {"text": "Mcp", "operation": "upper"}}'
        ),
        authorization_policy=ToolAuthorizationPolicy({"safe_text_case": ToolRisk.LOW}),
        execution_policy=ToolExecutionPolicy(timeout_seconds=0.5),
        audit_sink=sink,
    )
    print(f"{result.tool_name}: {result.output['text']} ({sink.events[0].outcome})")


if __name__ == "__main__":
    main()
