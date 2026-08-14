"""MCP Tool idempotency·approval·audit reservation을 memory-only fixture로 확인한다."""

from __future__ import annotations

from ai_platform.tools.idempotency import (
    InMemoryMcpToolExecutionAuditSink,
    InMemoryMcpToolExecutionLedger,
    McpTimedToolApproval,
    McpToolExecutionBinding,
    McpToolExecutionOutcome,
)
from ai_platform.tools.registry import SAFE_CALCULATOR, ToolRegistry


def main() -> None:
    """allowlisted safe_calculator request 하나의 reservation/completion만 모델링한다."""
    arguments: dict[str, object] = {"left": 2, "right": 3, "operation": "add"}
    ToolRegistry((SAFE_CALCULATOR,)).validate_request(
        tool_name="safe_calculator", arguments=arguments
    )
    binding = McpToolExecutionBinding.for_request(
        idempotency_key="idem-demo-001",
        request_id="mcp-stdio:string:demo-001",
        tool_name="safe_calculator",
        arguments=arguments,
    )
    approval = McpTimedToolApproval(
        approval_id="approval-demo-001",
        binding=binding,
        expires_at=101.0,
    )
    audit_sink = InMemoryMcpToolExecutionAuditSink()
    ledger = InMemoryMcpToolExecutionLedger(audit_sink)

    claim = ledger.reserve(approval, now=100.0)
    resolution = ledger.resolve(claim, outcome=McpToolExecutionOutcome.SUCCEEDED)

    print(f"idempotency_key: {claim.binding.idempotency_key}")
    print(f"audit_phases: {','.join(event.phase for event in audit_sink.events)}")
    print(f"state: {resolution.state}")
    print(f"reconciliation_required: {resolution.reconciliation_required}")


if __name__ == "__main__":
    main()
