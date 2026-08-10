"""사람 승인이 필요한 것으로 분류한 순수 Tool도 allowlist 안에서만 실행한다."""
from __future__ import annotations

from ai_platform.tools.authorization import (
    ApprovalGrant,
    ToolAuthorizationPolicy,
    ToolRisk,
    execute_authorized,
)
from ai_platform.tools.registry import SAFE_TEXT_CASE, ToolRegistry


def main() -> None:
    """고정된 교육용 승인 기록으로 문자열 대소문자 변환만 실행한다."""
    request_id = "demo-request-001"
    arguments = {"text": "AI Platform", "operation": "lower"}
    approval = ApprovalGrant.for_request(
        approval_id="demo-approval-001",
        request_id=request_id,
        tool_name="safe_text_case",
        arguments=arguments,
    )
    result = execute_authorized(
        ToolRegistry((SAFE_TEXT_CASE,)),
        request_id=request_id,
        tool_name="safe_text_case",
        arguments=arguments,
        policy=ToolAuthorizationPolicy({"safe_text_case": ToolRisk.HIGH}),
        approval=approval,
    )
    print(f"{result.tool_name}: {result.output['text']} (approved demo)")


if __name__ == "__main__":
    main()
