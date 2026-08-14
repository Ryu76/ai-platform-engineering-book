"""MCP client configuration의 attested health 뒤 exact Tool capability를 좁게 확인한다.

이 module은 Hermes/Codex CLI, configuration file, credential, subprocess, network, MCP server 또는
Tool을 호출하지 않는다. 기존 fresh provenance attestation과 one-shot health evidence를 먼저
검증한 뒤 caller-owned capability probe의 exact Tool tuple만 original immutable handoff으로
승격한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ai_platform.mcp.client_attestation import (
    McpClientConfigurationAttestation,
    McpClientConfigurationAttestationRequest,
    McpClientConfigurationAttestationVerifier,
)
from ai_platform.mcp.client_handoff import McpClientIntegrationHandoff
from ai_platform.mcp.client_health import (
    McpClientConfigurationHealthError,
    McpClientConfigurationHealthProbe,
    verify_mcp_client_configuration_health,
)


class McpClientConfigurationCapabilityError(ValueError):
    """attested healthy configuration이 exact client-visible Tool capability를
    보이지 않을 때 발생한다.
    """


@dataclass(frozen=True, slots=True)
class McpClientConfigurationCapabilityReceipt:
    """client adapter가 관측한 exact visible Tool name snapshot이다.

    Receipt에는 config content, credential, server response, session object 또는 raw adapter
    detail을 넣지 않는다. Production adapter는 authenticated client/session/server identity와
    this snapshot의 provenance를 별도로 검증한다.
    """

    tool_names: tuple[str, ...]

    def __post_init__(self) -> None:
        """probe 호출 결과가 small immutable exact-name tuple인지 먼저 좁힌다."""
        if not isinstance(self.tool_names, tuple) or not 1 <= len(self.tool_names) <= 16:
            raise McpClientConfigurationCapabilityError(
                "MCP client configuration capability tool names are invalid"
            )
        for tool_name in self.tool_names:
            if (
                not isinstance(tool_name, str)
                or not tool_name
                or len(tool_name) > 128
                or any(character in "\x00\n\r*" for character in tool_name)
            ):
                raise McpClientConfigurationCapabilityError(
                    "MCP client configuration capability tool names are invalid"
                )
        if len(self.tool_names) != len(set(self.tool_names)):
            raise McpClientConfigurationCapabilityError(
                "MCP client configuration capability tool names are invalid"
            )


@runtime_checkable
class McpClientConfigurationCapabilityProbe(Protocol):
    """client-specific adapter가 수행하는 one-shot visible Tool snapshot seam이다."""

    def inspect(
        self, request: McpClientConfigurationAttestationRequest
    ) -> McpClientConfigurationCapabilityReceipt:
        """현재 client가 보이는 exact Tool names만 immutable receipt로 보고한다."""


def verify_mcp_client_configuration_capability(
    request: McpClientConfigurationAttestationRequest,
    attestation: McpClientConfigurationAttestation,
    attestation_verifier: McpClientConfigurationAttestationVerifier,
    health_probe: McpClientConfigurationHealthProbe,
    capability_probe: McpClientConfigurationCapabilityProbe,
) -> McpClientIntegrationHandoff:
    """attested health 뒤 exact client-visible Tool snapshot일 때만 original handoff을 반환한다.

    Malformed input/probe 및 health failure는 capability probe 호출 전에 거부한다.
    Capability probe의 exception, malformed receipt 또는 expected tuple mismatch는 raw adapter
    detail이나 partial handoff 없이 generic error가 된다. 이 model은 actual reload/reconnect,
    client/server authentication, network transport 또는 Tool execution을 직접 증명하지 않는다.
    """
    if not isinstance(request, McpClientConfigurationAttestationRequest):
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability request is invalid"
        )
    if not isinstance(attestation, McpClientConfigurationAttestation):
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability attestation is invalid"
        )
    if not isinstance(attestation_verifier, McpClientConfigurationAttestationVerifier):
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability attestation verifier is invalid"
        )
    if not isinstance(health_probe, McpClientConfigurationHealthProbe):
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability health probe is invalid"
        )
    if not isinstance(capability_probe, McpClientConfigurationCapabilityProbe):
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability probe is invalid"
        )
    try:
        handoff = verify_mcp_client_configuration_health(
            request,
            attestation,
            attestation_verifier,
            health_probe,
        )
    except McpClientConfigurationHealthError:
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability health is invalid"
        ) from None
    try:
        receipt = capability_probe.inspect(request)
    except Exception:
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability probe failed"
        ) from None
    if not isinstance(receipt, McpClientConfigurationCapabilityReceipt):
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability probe failed"
        )
    try:
        validated_receipt = McpClientConfigurationCapabilityReceipt(receipt.tool_names)
    except McpClientConfigurationCapabilityError:
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability probe failed"
        ) from None
    if validated_receipt.tool_names != handoff.tool_names:
        raise McpClientConfigurationCapabilityError(
            "MCP client configuration capability did not match the handoff"
        )
    return handoff
