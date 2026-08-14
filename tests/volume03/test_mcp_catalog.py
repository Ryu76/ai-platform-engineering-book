"""Volume 03 교육용 MCP Tool catalog가 실행 권한을 만들지 않는지 검사한다."""
from __future__ import annotations

import pytest

from ai_platform.mcp.catalog import McpCatalogError, McpServerCatalog, McpToolDefinition
from ai_platform.tools.registry import SAFE_CALCULATOR, SAFE_TEXT_CASE, ToolRegistry


def test_catalog_projects_only_allowlisted_tools_as_mcp_list_definitions() -> None:
    catalog = McpServerCatalog.from_registry(ToolRegistry((SAFE_CALCULATOR, SAFE_TEXT_CASE)))

    assert catalog.list_tools() == (
        {
            "name": "safe_calculator",
            "description": SAFE_CALCULATOR.description,
            "inputSchema": SAFE_CALCULATOR.input_schema,
        },
        {
            "name": "safe_text_case",
            "description": SAFE_TEXT_CASE.description,
            "inputSchema": SAFE_TEXT_CASE.input_schema,
        },
    )
    assert not hasattr(catalog, "execute")


def test_catalog_snapshot_cannot_change_with_returned_schema_mutation() -> None:
    catalog = McpServerCatalog.from_registry(ToolRegistry((SAFE_CALCULATOR,)))
    listed = catalog.list_tools()
    schema = listed[0]["inputSchema"]
    assert isinstance(schema, dict)
    properties = schema["properties"]
    assert isinstance(properties, dict)
    left = properties["left"]
    assert isinstance(left, dict)
    left["type"] = "string"

    next_schema = catalog.list_tools()[0]["inputSchema"]
    assert isinstance(next_schema, dict)
    next_properties = next_schema["properties"]
    assert isinstance(next_properties, dict)
    assert next_properties["left"] == {"type": "number"}


def test_catalog_rejects_duplicate_names_and_non_object_schema() -> None:
    definition = McpToolDefinition(
        name="reviewed_tool",
        description="테스트 전용 정의",
        input_schema={"type": "object", "properties": {}},
    )
    with pytest.raises(McpCatalogError, match="names must be unique"):
        McpServerCatalog((definition, definition))
    with pytest.raises(McpCatalogError, match="schema type must be object"):
        McpToolDefinition(
            name="not_an_object",
            description="테스트 전용 잘못된 정의",
            input_schema={"type": "array"},
        )
