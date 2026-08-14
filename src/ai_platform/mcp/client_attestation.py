"""MCP client configuration receipt의 freshness와 verifier ownership을 memory model로 분리한다.

이 module은 Hermes/Codex CLI, configuration file, credential, signature library, subprocess, network
또는 Tool을 호출하지 않는다. Exact configuration acknowledgement와 deployment-provided one-shot
challenge를 먼저 대조한 뒤, caller가 소유한 client-specific provenance verifier를 한 번 호출한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ai_platform.mcp.client_acknowledgement import (
    McpClientConfigurationAcknowledgement,
    McpClientConfigurationAcknowledgementError,
    McpClientConfigurationApplication,
    verify_mcp_client_configuration_acknowledgement,
)
from ai_platform.mcp.client_handoff import McpClientIntegrationHandoff


class McpClientConfigurationAttestationError(ValueError):
    """attestation input 또는 trusted verifier가 configuration trust 전에 거부되었음을 나타낸다."""


@dataclass(frozen=True, slots=True)
class McpClientConfigurationAttestationRequest:
    """한 deployment application에만 쓰는 opaque single-line freshness challenge다.

    Challenge는 credential, signature, file path, config content 또는 client session ID가 아니다.
    Production adapter는 challenge를 authenticated external receipt에 어떻게 bind할지 별도로
    소유한다.
    """

    application: McpClientConfigurationApplication
    attestation_challenge: str

    def __post_init__(self) -> None:
        """untrusted application/challenge가 verifier에 도달하지 않게 한다."""
        if not isinstance(self.application, McpClientConfigurationApplication):
            raise McpClientConfigurationAttestationError(
                "MCP client configuration attestation application is invalid"
            )
        _validate_challenge(self.attestation_challenge)


@dataclass(frozen=True, slots=True)
class McpClientConfigurationAttestation:
    """external adapter가 apply/reload 뒤 제출할 acknowledgement와 freshness echo다."""

    acknowledgement: McpClientConfigurationAcknowledgement
    attestation_challenge: str

    def __post_init__(self) -> None:
        """receipt object와 challenge shape를 verifier 호출 전에 좁힌다."""
        if not isinstance(self.acknowledgement, McpClientConfigurationAcknowledgement):
            raise McpClientConfigurationAttestationError(
                "MCP client configuration attestation acknowledgement is invalid"
            )
        _validate_challenge(self.attestation_challenge)


@runtime_checkable
class McpClientConfigurationAttestationVerifier(Protocol):
    """client-specific adapter가 구현하는 one-shot receipt provenance seam이다."""

    def verify(self, attestation: McpClientConfigurationAttestation) -> bool:
        """authenticated receipt provenance를 true/false로만 축소해 보고한다."""


def verify_mcp_client_configuration_attestation(
    request: McpClientConfigurationAttestationRequest,
    attestation: McpClientConfigurationAttestation,
    verifier: McpClientConfigurationAttestationVerifier,
) -> McpClientIntegrationHandoff:
    """fresh exact receipt를 대조하고 trusted verifier가 승인할 때만 original handoff을 반환한다.

    Exact acknowledgement와 challenge mismatch, malformed object는 verifier 호출 전에 거부된다.
    Verifier의 exception, false 또는 non-bool return은 raw adapter detail 없이 generic error로
    끝난다. This model does not create, store, or validate credentials/signatures itself and does
    not establish client reload/reconnect health.
    """
    if not isinstance(request, McpClientConfigurationAttestationRequest):
        raise McpClientConfigurationAttestationError(
            "MCP client configuration attestation request is invalid"
        )
    if not isinstance(attestation, McpClientConfigurationAttestation):
        raise McpClientConfigurationAttestationError(
            "MCP client configuration attestation is invalid"
        )
    if not isinstance(verifier, McpClientConfigurationAttestationVerifier):
        raise McpClientConfigurationAttestationError(
            "MCP client configuration attestation verifier is invalid"
        )
    if attestation.attestation_challenge != request.attestation_challenge:
        raise McpClientConfigurationAttestationError(
            "MCP client configuration attestation did not match the request"
        )
    try:
        handoff = verify_mcp_client_configuration_acknowledgement(
            request.application,
            attestation.acknowledgement,
        )
    except McpClientConfigurationAcknowledgementError:
        raise McpClientConfigurationAttestationError(
            "MCP client configuration attestation acknowledgement is invalid"
        ) from None
    try:
        verified = verifier.verify(attestation)
    except Exception:
        raise McpClientConfigurationAttestationError(
            "MCP client configuration attestation verification failed"
        ) from None
    if verified is not True:
        raise McpClientConfigurationAttestationError(
            "MCP client configuration attestation verification failed"
        )
    return handoff


def _validate_challenge(value: object) -> None:
    """receipt freshness label을 작은 opaque single-line token으로 제한한다."""
    if (
        not isinstance(value, str)
        or not 16 <= len(value) <= 128
        or any(character in "\x00\n\r" for character in value)
    ):
        raise McpClientConfigurationAttestationError(
            "MCP client configuration attestation challenge is invalid"
        )
