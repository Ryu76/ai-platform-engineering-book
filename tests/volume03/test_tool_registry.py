"""네트워크나 시스템 변경 없이 Volume 03 Tool allowlist 계약을 검사한다."""
from __future__ import annotations

import pytest

from ai_platform.tools.registry import (
    SAFE_CALCULATOR,
    ToolArgumentsError,
    ToolNotAllowedError,
    ToolRegistry,
    ToolRegistryError,
    ToolSpec,
)


def registry() -> ToolRegistry:
    """각 테스트에 부작용 없는 계산기 하나만 등록한다."""
    return ToolRegistry((SAFE_CALCULATOR,))


def test_allowlisted_calculator_executes_only_safe_arithmetic() -> None:
    result = registry().execute(
        tool_name="safe_calculator",
        arguments={"left": 21, "right": 2, "operation": "multiply"},
    )

    assert result.tool_name == "safe_calculator"
    assert result.output == {"value": 42}
    assert registry().allowed_tool_names() == ("safe_calculator",)


def test_registry_rejects_a_tool_not_in_its_allowlist() -> None:
    with pytest.raises(ToolNotAllowedError, match="not allowlisted: delete_file"):
        registry().execute(tool_name="delete_file", arguments={"path": "important.txt"})


def test_invalid_arguments_do_not_reach_the_tool_handler() -> None:
    calls: list[dict[str, object]] = []
    guarded_tool = ToolSpec(
        name="guarded",
        description="검증 실패 시 handler가 실행되지 않는지 확인하는 테스트 전용 도구",
        input_schema={
            "type": "object",
            "properties": {"count": {"type": "number"}},
            "required": ["count"],
            "additionalProperties": False,
        },
        handler=lambda arguments: calls.append(dict(arguments)) or {"ok": True},
    )

    with pytest.raises(ToolArgumentsError, match="unexpected argument: path"):
        ToolRegistry((guarded_tool,)).execute(
            tool_name="guarded", arguments={"count": 1, "path": "not-used"}
        )

    assert calls == []


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"left": 1, "right": 2}, "missing required argument: operation"),
        ({"left": 1, "right": 2, "operation": "power"}, "operation must be one of"),
        ({"left": True, "right": 2, "operation": "add"}, "left must be a finite number"),
        ({"left": 1, "right": 2, "operation": "add", "path": "x"}, "unexpected argument: path"),
        ({"left": 1, "right": 0, "operation": "divide"}, "division by zero"),
    ],
)
def test_calculator_rejects_invalid_or_extra_model_arguments(
    arguments: dict[str, object], message: str
) -> None:
    with pytest.raises(ToolArgumentsError, match=message):
        registry().execute(tool_name="safe_calculator", arguments=arguments)


def test_registry_rejects_duplicate_names_and_unsupported_schema_types() -> None:
    with pytest.raises(ToolRegistryError, match="already registered"):
        ToolRegistry((SAFE_CALCULATOR, SAFE_CALCULATOR))

    with pytest.raises(ToolRegistryError, match="unsupported schema type"):
        ToolRegistry(
            (
                ToolSpec(
                    name="unsupported",
                    description="지원하지 않는 JSON Schema 타입을 확인하는 테스트 전용 도구",
                    input_schema={
                        "type": "object",
                        "properties": {"enabled": {"type": "boolean"}},
                    },
                    handler=lambda _: {},
                ),
            )
        ).execute(tool_name="unsupported", arguments={"enabled": True})
