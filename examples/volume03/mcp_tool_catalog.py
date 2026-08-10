"""순수 allowlisted Tool을 전송·실행 없이 교육용 MCP catalog로 나열한다."""
from __future__ import annotations

from ai_platform.mcp.catalog import McpServerCatalog
from ai_platform.tools.registry import SAFE_CALCULATOR, SAFE_TEXT_CASE, ToolRegistry


def main() -> None:
    """MCP `tools/list` 모양의 메타데이터만 출력하고 Tool은 호출하지 않는다."""
    catalog = McpServerCatalog.from_registry(ToolRegistry((SAFE_CALCULATOR, SAFE_TEXT_CASE)))
    for tool in catalog.list_tools():
        print(f"{tool['name']}: {tool['description']}")


if __name__ == "__main__":
    main()
