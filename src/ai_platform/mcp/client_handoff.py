"""Hermes·Codex 같은 MCP client에 전달할 최소 Tool visibility snapshot을 모델링한다.

이 module은 client CLI/config file, MCP connection, subprocess, network 또는 Tool 실행을
호출하지 않는다. Trusted deployment policy가 exact allowlisted Tool name을 고르면, 이미 static한
MCP catalog와 allowlisted server launch plan에서 검증 가능한 immutable handoff만 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_platform.mcp.catalog import McpServerCatalog
from ai_platform.mcp.host import McpStdioHostLaunchPlan


class McpClientHandoffError(ValueError):
    """client visibility policy 또는 trusted catalog/plan binding이 안전하지 않을 때 발생한다."""


class McpClientKind(StrEnum):
    """이 teaching model이 구별하는 configuration consumer label이다."""

    HERMES_AGENT = "hermes-agent"
    CODEX_CLI = "codex-cli"


@dataclass(frozen=True, slots=True)
class McpClientToolVisibilityPolicy:
    """deployment가 review한 client 하나의 exact MCP Tool visibility allowlist다.

    Tool name은 wildcard, prefix 또는 denylist가 아니다. 이 policy는 Tool execution 권한, client
    configuration schema, approval 또는 idempotency를 바꾸지 않는다.
    """

    client: McpClientKind
    tool_names: tuple[str, ...]

    def __post_init__(self) -> None:
        """작고 immutable한 exact name allowlist만 client handoff에 남긴다."""
        if not isinstance(self.client, McpClientKind):
            raise McpClientHandoffError("MCP client kind is invalid")
        if not isinstance(self.tool_names, tuple) or not 1 <= len(self.tool_names) <= 16:
            raise McpClientHandoffError("MCP client tool names must be a tuple of 1 to 16 values")
        for tool_name in self.tool_names:
            if (
                not isinstance(tool_name, str)
                or not tool_name
                or len(tool_name) > 128
                or any(character in "\x00\n\r*" for character in tool_name)
            ):
                raise McpClientHandoffError(
                    "MCP client tool names must be exact non-empty single-line names"
                )
        if len(self.tool_names) != len(set(self.tool_names)):
            raise McpClientHandoffError("MCP client tool names must be unique")


@dataclass(frozen=True, slots=True)
class McpClientIntegrationHandoff:
    """client 설정 writer가 사용할 수 있는 server-name과 exact visible Tool name snapshot이다."""

    client: McpClientKind
    server_name: str
    tool_names: tuple[str, ...]


def prepare_mcp_client_integration_handoff(
    plan: McpStdioHostLaunchPlan,
    catalog: McpServerCatalog,
    policy: McpClientToolVisibilityPolicy,
) -> McpClientIntegrationHandoff:
    """trusted plan/catalog에서 policy가 선택한 exact Tool만 client-neutral handoff로 반환한다.

    반환값을 Hermes Agent 또는 Codex CLI의 실제 config syntax로 쓰거나 reload/launch하는 책임은
    caller의 별도 adapter에 있다. catalog failure, unavailable Tool, invalid input에는 raw catalog
    metadata나 adapter detail 없이 실패하며 external I/O를 수행하지 않는다.
    """
    if not isinstance(plan, McpStdioHostLaunchPlan):
        raise McpClientHandoffError("MCP client launch plan is invalid")
    if not isinstance(catalog, McpServerCatalog):
        raise McpClientHandoffError("MCP client catalog is invalid")
    if not isinstance(policy, McpClientToolVisibilityPolicy):
        raise McpClientHandoffError("MCP client tool visibility policy is invalid")
    try:
        available_tool_names = {
            tool["name"] for tool in catalog.list_tools() if isinstance(tool.get("name"), str)
        }
    except Exception:
        raise McpClientHandoffError("MCP client catalog snapshot failed") from None
    if not set(policy.tool_names).issubset(available_tool_names):
        raise McpClientHandoffError("MCP client policy selects a tool outside the catalog")
    return McpClientIntegrationHandoff(
        client=policy.client,
        server_name=plan.server_name,
        tool_names=policy.tool_names,
    )
