"""모델 제공자 Function Calling 형식과 allowlisted Tool Registry 사이의 안전한 어댑터."""
from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import cast

from ai_platform.tools.registry import ToolRegistry, ToolRegistryError, ToolResult


class FunctionCallParseError(ToolRegistryError):
    """신뢰되지 않은 모델 Function Calling 응답이 예상 형식이 아닐 때 발생한다."""


@dataclass(frozen=True, slots=True)
class FunctionCall:
    """파싱을 마친 모델의 Tool 실행 요청이다. 이것 자체는 실행 권한이 아니다."""

    call_id: str
    tool_name: str
    arguments: Mapping[str, object]


def serialize_function_tools(registry: ToolRegistry) -> tuple[dict[str, object], ...]:
    """등록된 Tool만 OpenAI 호환 `tools` 배열의 function 정의로 직렬화한다."""
    definitions: list[dict[str, object]] = []
    for tool in registry.allowed_tools():
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": deepcopy(dict(tool.input_schema)),
                    "strict": True,
                },
            }
        )
    return tuple(definitions)


def parse_function_call(payload: Mapping[str, object]) -> FunctionCall:
    """OpenAI 호환 Tool-call payload를 검증하고 JSON 객체 인자만 추출한다."""
    call_id = payload.get("id")
    if not isinstance(call_id, str) or not call_id:
        raise FunctionCallParseError("function call id must be a non-empty string")
    if payload.get("type") != "function":
        raise FunctionCallParseError("tool call type must be function")
    function = payload.get("function")
    if not isinstance(function, Mapping):
        raise FunctionCallParseError("function call must contain a function object")
    tool_name = function.get("name")
    if not isinstance(tool_name, str) or not tool_name:
        raise FunctionCallParseError("function name must be a non-empty string")
    encoded_arguments = function.get("arguments")
    if not isinstance(encoded_arguments, str):
        raise FunctionCallParseError("function arguments must be a JSON object string")
    try:
        decoded_arguments = json.loads(encoded_arguments)
    except json.JSONDecodeError as error:
        raise FunctionCallParseError("function arguments are not valid JSON") from error
    if not isinstance(decoded_arguments, Mapping):
        raise FunctionCallParseError("function arguments must decode to a JSON object")
    return FunctionCall(
        call_id=call_id,
        tool_name=tool_name,
        arguments=cast(Mapping[str, object], decoded_arguments),
    )


def dispatch_function_call(registry: ToolRegistry, call: FunctionCall) -> ToolResult:
    """파싱된 요청을 기존 allowlist·Schema 실행 경계로 전달한다."""
    return registry.execute(tool_name=call.tool_name, arguments=call.arguments)
