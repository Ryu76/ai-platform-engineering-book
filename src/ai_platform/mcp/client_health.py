"""MCP client configuration의 attested receipt와 live-health probe를 좁게 연결한다.

이 module은 Hermes/Codex CLI, configuration file, credential, subprocess, network, MCP server 또는
Tool을 호출하지 않는다. 기존 fresh provenance attestation을 먼저 검증한 뒤 caller-owned
client-specific health probe의 exact ``True``만 original immutable handoff으로 승격한다.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ai_platform.mcp.client_attestation import (
    McpClientConfigurationAttestation,
    McpClientConfigurationAttestationError,
    McpClientConfigurationAttestationRequest,
    McpClientConfigurationAttestationVerifier,
    verify_mcp_client_configuration_attestation,
)
from ai_platform.mcp.client_handoff import McpClientIntegrationHandoff


class McpClientConfigurationHealthError(ValueError):
    """attested configuration의 client-health proof가 없을 때 발생한다."""


@runtime_checkable
class McpClientConfigurationHealthProbe(Protocol):
    """client-specific adapter가 수행하는 one-shot health evidence seam이다."""

    def probe(self, request: McpClientConfigurationAttestationRequest) -> bool:
        """현재 deployment request가 usable하다는 관측만 true/false로 축소해 보고한다."""


def verify_mcp_client_configuration_health(
    request: McpClientConfigurationAttestationRequest,
    attestation: McpClientConfigurationAttestation,
    attestation_verifier: McpClientConfigurationAttestationVerifier,
    health_probe: McpClientConfigurationHealthProbe,
) -> McpClientIntegrationHandoff:
    """fresh provenance 뒤 one-shot health probe가 승인할 때만 original handoff을 반환한다.

    Invalid probe, attestation mismatch/failure, malformed input은 probe 호출 전에 거부된다.
    Probe의 exception, false 또는 non-bool return은 raw adapter detail이나 partial handoff 없이
    generic error로 끝난다. 이 model은 connection, reload, server identity 또는
    TLS/STDIO lifecycle을 직접 확인하지 않는다.
    """
    if not isinstance(request, McpClientConfigurationAttestationRequest):
        raise McpClientConfigurationHealthError(
            "MCP client configuration health request is invalid"
        )
    if not isinstance(attestation, McpClientConfigurationAttestation):
        raise McpClientConfigurationHealthError(
            "MCP client configuration health attestation is invalid"
        )
    if not isinstance(attestation_verifier, McpClientConfigurationAttestationVerifier):
        raise McpClientConfigurationHealthError(
            "MCP client configuration health attestation verifier is invalid"
        )
    if not isinstance(health_probe, McpClientConfigurationHealthProbe):
        raise McpClientConfigurationHealthError("MCP client configuration health probe is invalid")
    try:
        handoff = verify_mcp_client_configuration_attestation(
            request,
            attestation,
            attestation_verifier,
        )
    except McpClientConfigurationAttestationError:
        raise McpClientConfigurationHealthError(
            "MCP client configuration health attestation is invalid"
        ) from None
    try:
        healthy = health_probe.probe(request)
    except Exception:
        raise McpClientConfigurationHealthError(
            "MCP client configuration health probe failed"
        ) from None
    if healthy is not True:
        raise McpClientConfigurationHealthError("MCP client configuration health probe failed")
    return handoff
