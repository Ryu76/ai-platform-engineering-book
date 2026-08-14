"""짧은 내장 MCP Resource만 읽기 전용으로 나열·조회한다."""
from __future__ import annotations

from ai_platform.mcp.resources import (
    McpResourceCatalog,
    McpStaticResource,
)

RESOURCE = McpStaticResource(
    uri="ai-platform://volume03/tool-boundary",
    name="Tool boundary note",
    mime_type="text/plain",
    text="Resources describe fixed reference text; they do not grant Tool execution.",
)


def main() -> None:
    """고정 allowlist Resource만 읽고 파일·셸·네트워크에는 접근하지 않는다."""
    catalog = McpResourceCatalog((RESOURCE,))
    listed = catalog.list_resources()[0]
    content = catalog.read_resource(listed["uri"])
    print(f"{content['uri']}: {content['text']}")


if __name__ == "__main__":
    main()
