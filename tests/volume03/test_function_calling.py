"""외부 모델 없이 Volume 03 Function Calling 어댑터의 경계를 검사한다."""
from __future__ import annotations

import json

import pytest

from ai_platform.tools.function_calling import (
    FunctionCallParseError,
    dispatch_function_call,
    parse_function_call,
    serialize_function_tools,
)
from ai_platform.tools.registry import (
    SAFE_CALCULATOR,
    SAFE_TEXT_CASE,
    ToolArgumentsError,
    ToolNotAllowedError,
    ToolRegistry,
)


def registry() -> ToolRegistry:
    """서로 다른 두 순수 Tool만 가진 고정 allowlist를 만든다."""
    return ToolRegistry((SAFE_CALCULATOR, SAFE_TEXT_CASE))


def valid_text_call() -> dict[str, object]:
    """Mock 모델이 반환한 것과 같은 고정 Function Calling payload다."""
    return {
        "id": "call_mock_01",
        "type": "function",
        "function": {
            "name": "safe_text_case",
            "arguments": json.dumps({"text": "Ai Platform", "operation": "upper"}),
        },
    }


def test_serialize_function_tools_exports_only_allowlisted_tools() -> None:
    definitions = serialize_function_tools(registry())

    assert [definition["type"] for definition in definitions] == ["function", "function"]
    functions = [definition["function"] for definition in definitions]
    assert [function["name"] for function in functions] == [
        "safe_calculator",
        "safe_text_case",
    ]
    assert all(function["strict"] is True for function in functions)
    assert functions[1]["parameters"] == SAFE_TEXT_CASE.input_schema


def test_mock_function_call_is_parsed_then_dispatched_through_registry() -> None:
    call = parse_function_call(valid_text_call())

    result = dispatch_function_call(registry(), call)

    assert call.call_id == "call_mock_01"
    assert result.tool_name == "safe_text_case"
    assert result.output == {"text": "AI PLATFORM"}


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"id": "call_1", "type": "function", "function": {}}, "function name"),
        ({"id": "call_1", "type": "function", "function": {"name": "safe_text_case"}}, "arguments"),
        (
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "safe_text_case", "arguments": "[1, 2]"},
            },
            "JSON object",
        ),
        (
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "safe_text_case", "arguments": "not-json"},
            },
            "valid JSON",
        ),
    ],
)
def test_untrusted_function_payload_must_have_a_valid_object_arguments(
    payload: dict[str, object], message: str
) -> None:
    with pytest.raises(FunctionCallParseError, match=message):
        parse_function_call(payload)


def test_parsed_call_cannot_bypass_allowlist_or_argument_validation() -> None:
    forbidden = parse_function_call(
        {
            "id": "call_forbidden",
            "type": "function",
            "function": {"name": "delete_file", "arguments": '{"path": "important.txt"}'},
        }
    )
    invalid = parse_function_call(
        {
            "id": "call_invalid",
            "type": "function",
            "function": {
                "name": "safe_text_case",
                "arguments": '{"text": "safe", "operation": "title"}',
            },
        }
    )

    with pytest.raises(ToolNotAllowedError, match="not allowlisted: delete_file"):
        dispatch_function_call(registry(), forbidden)
    with pytest.raises(ToolArgumentsError, match="operation must be one of"):
        dispatch_function_call(registry(), invalid)
