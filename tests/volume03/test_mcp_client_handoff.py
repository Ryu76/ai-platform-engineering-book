"""Volume 03 MCP client handoff이 exact allowlist 밖 Tool을 노출하지 않는지 검증한다."""

from __future__ import annotations

import pytest

from ai_platform.mcp.catalog import McpServerCatalog
from ai_platform.mcp.client_handoff import (
    McpClientHandoffError,
    McpClientIntegrationHandoff,
    McpClientKind,
    McpClientToolVisibilityPolicy,
    prepare_mcp_client_integration_handoff,
)
from ai_platform.mcp.host import McpStdioHostAllowlist, McpStdioServerSpec
from ai_platform.tools.registry import SAFE_CALCULATOR, SAFE_TEXT_CASE, ToolRegistry


def _plan() -> object:
    return McpStdioHostAllowlist(
        (
            McpStdioServerSpec(
                name="safe-tools",
                argv=("offline-mcp-server",),
                max_stdout_bytes=1_024,
                max_stderr_bytes=1_024,
                shutdown_grace_seconds=1.0,
                restart_limit=0,
            ),
        )
    ).prepare_launch("safe-tools")


def _catalog() -> McpServerCatalog:
    return McpServerCatalog.from_registry(ToolRegistry((SAFE_CALCULATOR, SAFE_TEXT_CASE)))


@pytest.mark.parametrize("client", tuple(McpClientKind))
def test_handoff_exposes_only_deployment_selected_catalog_tools(client: McpClientKind) -> None:
    handoff = prepare_mcp_client_integration_handoff(
        _plan(),  # type: ignore[arg-type]
        _catalog(),
        McpClientToolVisibilityPolicy(client=client, tool_names=("safe_calculator",)),
    )

    assert handoff == McpClientIntegrationHandoff(
        client=client,
        server_name="safe-tools",
        tool_names=("safe_calculator",),
    )


@pytest.mark.parametrize(
    "tool_names",
    (
        ["safe_calculator"],
        (),
        ("safe_calculator", "safe_calculator"),
        ("safe_*",),
        ("safe_calculator\nother",),
        (["safe_calculator"],),
    ),
)
def test_policy_rejects_mutable_empty_duplicate_or_wildcard_names_before_catalog(
    tool_names: object,
) -> None:
    with pytest.raises(McpClientHandoffError, match="MCP client tool names"):
        McpClientToolVisibilityPolicy(  # type: ignore[arg-type]
            client=McpClientKind.HERMES_AGENT,
            tool_names=tool_names,
        )


def test_unavailable_tool_is_rejected_without_leaking_catalog_metadata() -> None:
    with pytest.raises(McpClientHandoffError, match="outside the catalog") as error:
        prepare_mcp_client_integration_handoff(
            _plan(),  # type: ignore[arg-type]
            _catalog(),
            McpClientToolVisibilityPolicy(
                client=McpClientKind.CODEX_CLI,
                tool_names=("not-a-real-tool",),
            ),
        )

    assert "safe_text_case" not in str(error.value)


def test_invalid_plan_or_catalog_is_rejected_before_client_handoff() -> None:
    policy = McpClientToolVisibilityPolicy(
        client=McpClientKind.HERMES_AGENT,
        tool_names=("safe_calculator",),
    )

    with pytest.raises(McpClientHandoffError, match="launch plan is invalid"):
        prepare_mcp_client_integration_handoff(object(), _catalog(), policy)  # type: ignore[arg-type]
    with pytest.raises(McpClientHandoffError, match="catalog is invalid"):
        prepare_mcp_client_integration_handoff(_plan(), object(), policy)  # type: ignore[arg-type]
