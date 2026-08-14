"""신뢰되지 않은 MCP Tool 호출 JSON을 실행 전에 좁게 검증하는 경계."""
from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType

from ai_platform.tools.registry import ToolRegistry


class McpCallRequestError(ValueError):
    """MCP Tool 호출 요청이 제한된 JSON 계약을 따르지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class McpToolCallRequest:
    """파싱된 MCP Tool 호출 의도다; handler·결과·실행 기능은 보관하지 않는다."""

    name: str
    arguments: Mapping[str, object]

    def __post_init__(self) -> None:
        """이름과 객체 인자를 고정해 이후 경계가 같은 요청을 검증하게 한다."""
        if not self.name.strip():
            raise McpCallRequestError("MCP tool call name must not be empty")
        object.__setattr__(
            self,
            "arguments",
            MappingProxyType(deepcopy(dict(self.arguments))),
        )

    def validate_against(self, registry: ToolRegistry) -> None:
        """실행 없이 기존 allowlist와 JSON Schema를 반드시 다시 검증한다."""
        registry.validate_request(tool_name=self.name, arguments=self.arguments)


def parse_mcp_tool_call_request(raw_request: str) -> McpToolCallRequest:
    """정확히 ``name``과 객체형 ``arguments``를 가진 JSON 호출 요청만 파싱한다."""
    if not isinstance(raw_request, str):
        raise McpCallRequestError("MCP tool call request must be a JSON string")
    try:
        payload: object = json.loads(
            raw_request,
            object_pairs_hook=_json_object_without_duplicate_keys,
            parse_constant=_reject_non_standard_json_constant,
        )
    except json.JSONDecodeError as error:
        raise McpCallRequestError("MCP tool call request must be valid JSON") from error

    if not isinstance(payload, dict):
        raise McpCallRequestError("MCP tool call request must be a JSON object")
    _validate_request_keys(payload)

    name = payload["name"]
    arguments = payload["arguments"]
    if not isinstance(name, str):
        raise McpCallRequestError("MCP tool call name must be a string")
    if not isinstance(arguments, dict):
        raise McpCallRequestError("MCP tool call arguments must be a JSON object")
    return McpToolCallRequest(name=name, arguments=arguments)


def _json_object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """JSON object의 중복 키가 앞선 안전한 값을 덮어쓰지 못하게 한다."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise McpCallRequestError(f"MCP tool call JSON contains duplicate key: {key}")
        result[key] = value
    return result


def _reject_non_standard_json_constant(value: str) -> object:
    """JSON 표준 밖의 NaN·Infinity 상수를 거부한다."""
    raise McpCallRequestError(f"MCP tool call JSON constant is not allowed: {value}")


def _validate_request_keys(payload: Mapping[str, object]) -> None:
    """호출 의도 외 메타데이터가 실행 경계에 섞이지 않게 정확한 키만 허용한다."""
    expected = {"name", "arguments"}
    missing = sorted(expected - set(payload))
    if missing:
        raise McpCallRequestError(f"MCP tool call request is missing key: {missing[0]}")
    unexpected = sorted(set(payload) - expected)
    if unexpected:
        raise McpCallRequestError(f"MCP tool call request has unexpected key: {unexpected[0]}")
