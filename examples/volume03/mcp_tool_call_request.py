"""신뢰되지 않은 MCP Tool 호출 JSON을 실행하지 않고 allowlist·Schema로 재검증한다."""
from __future__ import annotations

from ai_platform.mcp.requests import parse_mcp_tool_call_request
from ai_platform.tools.registry import SAFE_TEXT_CASE, ToolRegistry


def main() -> None:
    """순수 Tool 요청의 실행 전 검증만 수행하며 handler는 호출하지 않는다."""
    request = parse_mcp_tool_call_request(
        '{"name": "safe_text_case", "arguments": {"text": "Mcp", "operation": "upper"}}'
    )
    request.validate_against(ToolRegistry((SAFE_TEXT_CASE,)))
    print(f"validated without execution: {request.name}")


if __name__ == "__main__":
    main()
