"""승인된 순수 Tool 실행의 최소 감사 이벤트를 오프라인에서 확인한다."""
from __future__ import annotations

from ai_platform.tools.audit import InMemoryToolAuditSink, execute_audited
from ai_platform.tools.authorization import ApprovalGrant, ToolAuthorizationPolicy, ToolRisk
from ai_platform.tools.registry import SAFE_TEXT_CASE, ToolRegistry


def main() -> None:
    """문자열 변환 하나와 원문 인자를 포함하지 않는 감사 이벤트 하나만 만든다."""
    request_id = "audit-demo-request-001"
    arguments = {"text": "AI Platform", "operation": "upper"}
    approval = ApprovalGrant.for_request(
        approval_id="audit-demo-approval-001",
        request_id=request_id,
        tool_name="safe_text_case",
        arguments=arguments,
    )
    sink = InMemoryToolAuditSink()
    result = execute_audited(
        ToolRegistry((SAFE_TEXT_CASE,)),
        request_id=request_id,
        tool_name="safe_text_case",
        arguments=arguments,
        policy=ToolAuthorizationPolicy({"safe_text_case": ToolRisk.HIGH}),
        approval=approval,
        audit_sink=sink,
    )
    event = sink.events[0]
    print(f"{result.tool_name}: {result.output['text']}")
    print(
        "audit: "
        f"request_id={event.request_id}, tool={event.tool_name}, "
        f"risk={event.risk}, approval_id={event.approval_id}, outcome={event.outcome}"
    )


if __name__ == "__main__":
    main()
