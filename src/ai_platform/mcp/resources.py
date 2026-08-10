"""정적으로 내장한 allowlisted MCP Resource를 읽기 전용으로 노출하는 교육용 모델."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlparse


class McpResourceError(ValueError):
    """정적 MCP Resource 계약 또는 allowlist를 벗어난 요청일 때 발생한다."""


@dataclass(frozen=True, slots=True)
class McpStaticResource:
    """짧은 내장 텍스트만 가진 allowlisted Resource 정의다.

    이 정의는 파일 경로나 loader, handler를 받지 않는다. 따라서 Resource를 읽는 일은
    로컬 파일·환경 변수·네트워크·Tool 실행으로 이어지지 않는다.
    """

    uri: str
    name: str
    mime_type: str
    text: str

    def __post_init__(self) -> None:
        """고정 URI와 짧은 텍스트 Resource라는 최소 계약을 확인한다."""
        parsed = urlparse(self.uri)
        if parsed.scheme != "ai-platform" or not parsed.netloc or not parsed.path:
            raise McpResourceError(
                "MCP resource URI must be an ai-platform URI with an authority and path"
            )
        if parsed.query or parsed.fragment:
            raise McpResourceError("MCP resource URI must not contain a query or fragment")
        if not self.name.strip():
            raise McpResourceError("MCP resource name must not be empty")
        if self.mime_type != "text/plain":
            raise McpResourceError("MCP static resource MIME type must be text/plain")
        if not self.text.strip():
            raise McpResourceError("MCP static resource text must not be empty")
        if len(self.text) > 4096:
            raise McpResourceError("MCP static resource text must be at most 4096 characters")


class McpResourceCatalog:
    """명시적으로 등록한 짧은 내장 Resource만 URI로 조회한다.

    이 클래스는 MCP SDK, STDIO, 네트워크, subprocess, 파일 API를 사용하지 않는다.
    URI는 경로로 해석하지 않고 정확히 일치하는 allowlist key로만 사용한다.
    """

    def __init__(self, resources: tuple[McpStaticResource, ...]) -> None:
        uris = [resource.uri for resource in resources]
        if len(uris) != len(set(uris)):
            raise McpResourceError("MCP resource URIs must be unique")
        self._resources = MappingProxyType({resource.uri: resource for resource in resources})

    def list_resources(self) -> tuple[dict[str, str], ...]:
        """MCP `resources/list` 모양의 metadata snapshot만 반환한다."""
        return tuple(
            {
                "uri": resource.uri,
                "name": resource.name,
                "mimeType": resource.mime_type,
            }
            for resource in self._resources.values()
        )

    def read_resource(self, uri: str) -> dict[str, str]:
        """allowlisted URI의 고정 text snapshot만 반환하고 URI를 해석하지 않는다."""
        resource = self._resources.get(uri)
        if resource is None:
            raise McpResourceError(f"MCP resource is not allowlisted: {uri}")
        return {
            "uri": resource.uri,
            "mimeType": resource.mime_type,
            "text": resource.text,
        }
