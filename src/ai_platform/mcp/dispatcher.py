"""전송 계층 없이 검증된 MCP Tool 요청을 기존 실행 경계로 묶는 dispatcher."""
from __future__ import annotations

from ai_platform.mcp.requests import McpToolCallRequest, parse_mcp_tool_call_request
from ai_platform.tools.audit import InMemoryToolAuditSink, execute_audited_with_policy
from ai_platform.tools.authorization import ApprovalGrant, ToolAuthorizationPolicy
from ai_platform.tools.execution import ToolExecutionPolicy
from ai_platform.tools.registry import ToolRegistry, ToolResult


class McpDispatchError(ValueError):
    """dispatcher 요청 자체가 안전한 실행 상관관계 계약을 따르지 않을 때 발생한다."""


def dispatch_mcp_tool_call(
    registry: ToolRegistry,
    *,
    request_id: str,
    raw_request: str,
    authorization_policy: ToolAuthorizationPolicy,
    execution_policy: ToolExecutionPolicy,
    audit_sink: InMemoryToolAuditSink,
    approval: ApprovalGrant | None = None,
) -> ToolResult:
    """JSON parser·allowlist·승인·timeout/retry·감사를 순서대로 거친 Tool만 실행한다."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise McpDispatchError("request_id must be a non-empty string")

    request = parse_mcp_tool_call_request(raw_request)
    _validate_request_without_execution(request, registry)
    return execute_audited_with_policy(
        registry,
        request_id=request_id,
        tool_name=request.name,
        arguments=request.arguments,
        authorization_policy=authorization_policy,
        execution_policy=execution_policy,
        audit_sink=audit_sink,
        approval=approval,
    )


def _validate_request_without_execution(
    request: McpToolCallRequest, registry: ToolRegistry
) -> None:
    """전송된 의도가 handler 전에 기존 registry allowlist·Schema를 통과하게 한다."""
    request.validate_against(registry)
