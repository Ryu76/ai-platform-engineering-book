"""Allowlisted Tool을 실행 권한 없이 MCP Tool catalog로 투영하는 교육용 모델."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass

from ai_platform.tools.registry import ToolRegistry


class McpCatalogError(ValueError):
    """MCP catalog 계약이 안전한 최소 형태가 아닐 때 발생한다."""


@dataclass(frozen=True, slots=True)
class McpToolDefinition:
    """MCP `tools/list`에 제공할 Tool 메타데이터다; handler나 실행 권한은 없다."""

    name: str
    description: str
    input_schema: Mapping[str, object]

    def __post_init__(self) -> None:
        """전송 전에 이름·설명·객체 Schema라는 최소 계약을 고정한다."""
        if not self.name:
            raise McpCatalogError("MCP tool name must not be empty")
        if not self.description.strip():
            raise McpCatalogError("MCP tool description must not be empty")
        if self.input_schema.get("type") != "object":
            raise McpCatalogError("MCP tool input schema type must be object")


class McpServerCatalog:
    """명시적 allowlist의 Tool 정의만 읽기 전용 MCP 목록으로 제공한다.

    이 클래스는 SDK, STDIO, 네트워크, subprocess를 사용하지 않는다. `tools/list`와
    닮은 정의를 만들 뿐이며, Tool 호출은 기존 ToolRegistry 및 그 상위 정책 경계가 맡는다.
    """

    def __init__(self, definitions: tuple[McpToolDefinition, ...]) -> None:
        names = [definition.name for definition in definitions]
        if len(names) != len(set(names)):
            raise McpCatalogError("MCP tool names must be unique")
        self._definitions = tuple(
            McpToolDefinition(
                name=definition.name,
                description=definition.description,
                input_schema=deepcopy(dict(definition.input_schema)),
            )
            for definition in definitions
        )

    @classmethod
    def from_registry(cls, registry: ToolRegistry) -> McpServerCatalog:
        """등록된 allowlisted Tool만 handler 없이 catalog 정의로 복사한다."""
        return cls(
            tuple(
                McpToolDefinition(
                    name=tool.name,
                    description=tool.description,
                    input_schema=deepcopy(dict(tool.input_schema)),
                )
                for tool in registry.allowed_tools()
            )
        )

    def list_tools(self) -> tuple[dict[str, object], ...]:
        """MCP `tools/list` 모양의 독립 snapshot을 반환한다; Tool을 실행하지 않는다."""
        return tuple(
            {
                "name": definition.name,
                "description": definition.description,
                "inputSchema": deepcopy(dict(definition.input_schema)),
            }
            for definition in self._definitions
        )
