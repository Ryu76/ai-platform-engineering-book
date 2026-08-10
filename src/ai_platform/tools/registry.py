"""신뢰되지 않은 모델 도구 요청을 제한된 로컬 함수로 연결하는 경계."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite
from typing import cast


class ToolRegistryError(ValueError):
    """도구 등록 또는 호출 계약이 안전하지 않을 때 발생한다."""


class ToolNotAllowedError(ToolRegistryError):
    """허용 목록에 없는 도구 이름을 요청했을 때 발생한다."""


class ToolArgumentsError(ToolRegistryError):
    """도구의 JSON Schema 계약에 맞지 않는 인자를 받았을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class ToolResult:
    """도구 실행 뒤 모델에 돌려줄 구조화된, 비밀값 없는 결과다."""

    tool_name: str
    output: Mapping[str, object]


ToolHandler = Callable[[Mapping[str, object]], Mapping[str, object]]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """허용된 도구의 이름, 입력 Schema, 부작용 없는 처리 함수를 정의한다."""

    name: str
    description: str
    input_schema: Mapping[str, object]
    handler: ToolHandler

    def __post_init__(self) -> None:
        """등록 전에 최소 JSON Schema 형태와 설명을 확인한다."""
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ToolRegistryError("tool name must contain only letters, digits, and underscores")
        if not self.description.strip():
            raise ToolRegistryError("tool description must not be empty")
        if self.input_schema.get("type") != "object":
            raise ToolRegistryError("tool input schema type must be object")
        if not isinstance(self.input_schema.get("properties"), Mapping):
            raise ToolRegistryError("tool input schema must define object properties")


class ToolRegistry:
    """등록된 도구만 인자 검증 뒤 실행하는 명시적 allowlist다."""

    def __init__(self, tools: tuple[ToolSpec, ...] = ()) -> None:
        self._tools: dict[str, ToolSpec] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: ToolSpec) -> None:
        """이름 중복 없이 검토된 도구 하나를 allowlist에 넣는다."""
        if tool.name in self._tools:
            raise ToolRegistryError(f"tool is already registered: {tool.name}")
        self._tools[tool.name] = tool

    def allowed_tool_names(self) -> tuple[str, ...]:
        """모델에 제공할 수 있는 안정된 도구 이름 목록을 반환한다."""
        return tuple(self._tools)

    def allowed_tools(self) -> tuple[ToolSpec, ...]:
        """Function Calling 정의로 내보낼 수 있는 등록 Tool만 순서대로 반환한다."""
        return tuple(self._tools.values())

    def execute(self, *, tool_name: str, arguments: Mapping[str, object]) -> ToolResult:
        """allowlist와 입력 Schema를 통과한 로컬 함수만 실행한다."""
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolNotAllowedError(f"tool is not allowlisted: {tool_name}")
        _validate_arguments(arguments, schema=tool.input_schema)
        return ToolResult(tool_name=tool.name, output=tool.handler(arguments))


def _validate_arguments(arguments: Mapping[str, object], *, schema: Mapping[str, object]) -> None:
    """이 예제의 객체·필수 필드·추가 필드·숫자·문자열·enum 계약을 검증한다."""
    properties = cast(Mapping[str, object], schema["properties"])
    required = schema.get("required", ())
    if not isinstance(required, (list, tuple)) or not all(
        isinstance(name, str) for name in required
    ):
        raise ToolRegistryError("tool input schema required must be a list of field names")
    missing = [name for name in required if name not in arguments]
    if missing:
        raise ToolArgumentsError(f"missing required argument: {missing[0]}")
    if schema.get("additionalProperties") is False:
        unexpected = sorted(set(arguments) - set(properties))
        if unexpected:
            raise ToolArgumentsError(f"unexpected argument: {unexpected[0]}")
    for name, value in arguments.items():
        property_schema = properties.get(name)
        if not isinstance(property_schema, Mapping):
            raise ToolArgumentsError(f"argument is not defined by schema: {name}")
        _validate_value(name, value=value, schema=property_schema)


def _validate_value(name: str, *, value: object, schema: Mapping[str, object]) -> None:
    """지원하는 좁은 JSON Schema 타입과 enum을 검사한다."""
    expected_type = schema.get("type")
    if expected_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ToolArgumentsError(f"argument {name} must be a finite number")
    elif expected_type == "string":
        if not isinstance(value, str):
            raise ToolArgumentsError(f"argument {name} must be a string")
    else:
        raise ToolRegistryError(f"unsupported schema type for {name}: {expected_type!r}")
    enum = schema.get("enum")
    if enum is not None:
        if not isinstance(enum, (list, tuple)):
            raise ToolRegistryError(f"schema enum for {name} must be a list")
        if value not in enum:
            raise ToolArgumentsError(f"argument {name} must be one of: {', '.join(map(str, enum))}")


def safe_calculator(arguments: Mapping[str, object]) -> Mapping[str, object]:
    """사칙연산만 수행하는 순수 함수; 파일·프로세스·네트워크에는 접근하지 않는다."""
    left = cast(float, arguments["left"])
    right = cast(float, arguments["right"])
    operation = cast(str, arguments["operation"])
    operations: Mapping[str, Callable[[float, float], float]] = {
        "add": lambda first, second: first + second,
        "subtract": lambda first, second: first - second,
        "multiply": lambda first, second: first * second,
        "divide": lambda first, second: first / second,
    }
    if operation == "divide" and right == 0:
        raise ToolArgumentsError("division by zero is not allowed")
    return {"value": operations[operation](left, right)}


SAFE_CALCULATOR = ToolSpec(
    name="safe_calculator",
    description="두 유한 수의 허용된 사칙연산을 수행합니다. 외부 시스템을 변경하지 않습니다.",
    input_schema={
        "type": "object",
        "properties": {
            "left": {"type": "number"},
            "right": {"type": "number"},
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
            },
        },
        "required": ["left", "right", "operation"],
        "additionalProperties": False,
    },
    handler=safe_calculator,
)


def safe_text_case(arguments: Mapping[str, object]) -> Mapping[str, object]:
    """문자열의 대소문자만 변환하는 순수 함수; 외부 시스템에는 접근하지 않는다."""
    text = cast(str, arguments["text"])
    operation = cast(str, arguments["operation"])
    transformations: Mapping[str, Callable[[str], str]] = {
        "upper": str.upper,
        "lower": str.lower,
    }
    return {"text": transformations[operation](text)}


SAFE_TEXT_CASE = ToolSpec(
    name="safe_text_case",
    description="문자열을 대문자 또는 소문자로만 변환합니다. 외부 시스템을 변경하지 않습니다.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "operation": {"type": "string", "enum": ["upper", "lower"]},
        },
        "required": ["text", "operation"],
        "additionalProperties": False,
    },
    handler=safe_text_case,
)
