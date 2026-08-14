"""Volume 03 MCP client acknowledgement가 exact allowlist handoff을 바꾸지 않는지 검증한다."""

from __future__ import annotations

import pytest

from ai_platform.mcp.client_acknowledgement import (
    McpClientConfigurationAcknowledgement,
    McpClientConfigurationAcknowledgementError,
    McpClientConfigurationApplication,
    verify_mcp_client_configuration_acknowledgement,
)
from ai_platform.mcp.client_handoff import (
    McpClientIntegrationHandoff,
    McpClientKind,
)


def _application() -> McpClientConfigurationApplication:
    return McpClientConfigurationApplication(
        handoff=McpClientIntegrationHandoff(
            client=McpClientKind.HERMES_AGENT,
            server_name="safe-tools",
            tool_names=("safe_calculator",),
        ),
        configuration_generation="deployment-revision-001",
    )


def _acknowledgement(**changes: object) -> McpClientConfigurationAcknowledgement:
    values: dict[str, object] = {
        "client": McpClientKind.HERMES_AGENT,
        "server_name": "safe-tools",
        "tool_names": ("safe_calculator",),
        "configuration_generation": "deployment-revision-001",
    }
    values.update(changes)
    return McpClientConfigurationAcknowledgement(**values)  # type: ignore[arg-type]


def test_matching_acknowledgement_returns_the_original_immutable_handoff() -> None:
    application = _application()

    verified = verify_mcp_client_configuration_acknowledgement(application, _acknowledgement())

    assert verified is application.handoff
    assert verified.tool_names == ("safe_calculator",)


@pytest.mark.parametrize(
    "changes",
    (
        {"client": McpClientKind.CODEX_CLI},
        {"server_name": "other-safe-tools"},
        {"tool_names": ("safe_text_case",)},
        {"configuration_generation": "deployment-revision-002"},
    ),
)
def test_mismatched_acknowledgement_is_rejected_without_returning_partial_visibility(
    changes: dict[str, object],
) -> None:
    with pytest.raises(
        McpClientConfigurationAcknowledgementError,
        match="does not match the application",
    ):
        verify_mcp_client_configuration_acknowledgement(_application(), _acknowledgement(**changes))


@pytest.mark.parametrize(
    "tool_names",
    (
        ["safe_calculator"],
        (),
        ("safe_calculator", "safe_calculator"),
        ("safe_*",),
        ("safe_calculator\nother",),
    ),
)
def test_acknowledgement_rejects_non_exact_or_mutable_visibility_before_verification(
    tool_names: object,
) -> None:
    with pytest.raises(McpClientConfigurationAcknowledgementError, match="tool names are invalid"):
        _acknowledgement(tool_names=tool_names)


def test_application_rechecks_manually_forged_handoff_before_external_adapter_boundary() -> None:
    forged_handoff = McpClientIntegrationHandoff(  # type: ignore[arg-type]
        client=McpClientKind.HERMES_AGENT,
        server_name="safe-tools\nother",
        tool_names=("safe_calculator",),
    )

    with pytest.raises(McpClientConfigurationAcknowledgementError, match="handoff is invalid"):
        McpClientConfigurationApplication(
            handoff=forged_handoff,
            configuration_generation="deployment-revision-001",
        )


def test_invalid_object_is_rejected_before_any_configuration_acknowledgement_is_trusted() -> None:
    with pytest.raises(McpClientConfigurationAcknowledgementError, match="application is invalid"):
        verify_mcp_client_configuration_acknowledgement(object(), _acknowledgement())  # type: ignore[arg-type]
    with pytest.raises(
        McpClientConfigurationAcknowledgementError, match="acknowledgement is invalid"
    ):
        verify_mcp_client_configuration_acknowledgement(_application(), object())  # type: ignore[arg-type]
