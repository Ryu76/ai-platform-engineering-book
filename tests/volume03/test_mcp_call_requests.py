"""Volume 03 MCP Tool 호출 요청이 실행 전에 좁게 검증되는지 검사한다."""
from __future__ import annotations

import pytest

from ai_platform.mcp.requests import (
    McpCallRequestError,
    McpToolCallRequest,
    parse_mcp_tool_call_request,
)
from ai_platform.tools.registry import (
    SAFE_CALCULATOR,
    ToolArgumentsError,
    ToolNotAllowedError,
    ToolRegistry,
    ToolSpec,
)


def test_parsed_request_revalidates_allowlist_without_running_handler() -> None:
    calls: list[dict[str, object]] = []
    reviewed_tool = ToolSpec(
        name="reviewed_number",
        description="검증 전용 테스트 Tool",
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "number"}},
            "required": ["value"],
            "additionalProperties": False,
        },
        handler=lambda arguments: calls.append(dict(arguments)) or {"ok": True},
    )
    request = parse_mcp_tool_call_request(
        '{"name": "reviewed_number", "arguments": {"value": 3}}'
    )

    request.validate_against(ToolRegistry((reviewed_tool,)))

    assert request.name == "reviewed_number"
    assert dict(request.arguments) == {"value": 3}
    assert calls == []
    assert not hasattr(request, "execute")


@pytest.mark.parametrize(
    ("raw_request", "message"),
    [
        ("[]", "must be a JSON object"),
        ('{"name": "safe_calculator"}', "missing key: arguments"),
        ('{"name": "safe_calculator", "arguments": {}, "id": "untrusted"}', "unexpected key: id"),
        ('{"name": 7, "arguments": {}}', "name must be a string"),
        ('{"name": "safe_calculator", "arguments": []}', "arguments must be a JSON object"),
        ('{"name": "safe_calculator", "arguments": {}, "name": "other"}', "duplicate key: name"),
        ('{"name": "safe_calculator", "arguments": {"left": NaN}}', "constant is not allowed"),
    ],
)
def test_parser_rejects_non_contract_or_ambiguous_json(
    raw_request: str, message: str
) -> None:
    with pytest.raises(McpCallRequestError, match=message):
        parse_mcp_tool_call_request(raw_request)


def test_request_validation_reuses_registry_for_allowlist_and_schema() -> None:
    registry = ToolRegistry((SAFE_CALCULATOR,))
    unknown_tool = parse_mcp_tool_call_request(
        '{"name": "delete_file", "arguments": {"path": "not-used.txt"}}'
    )
    invalid_arguments = parse_mcp_tool_call_request(
        '{"name": "safe_calculator", "arguments": {"left": 1, "right": 2, "operation": "power"}}'
    )

    with pytest.raises(ToolNotAllowedError, match="not allowlisted: delete_file"):
        unknown_tool.validate_against(registry)
    with pytest.raises(ToolArgumentsError, match="operation must be one of"):
        invalid_arguments.validate_against(registry)


def test_manual_request_copies_arguments_before_registry_validation() -> None:
    source_arguments: dict[str, object] = {"left": 1, "right": 2, "operation": "add"}
    request = McpToolCallRequest(name="safe_calculator", arguments=source_arguments)
    source_arguments["operation"] = "divide"

    request.validate_against(ToolRegistry((SAFE_CALCULATOR,)))

    assert dict(request.arguments)["operation"] == "add"
