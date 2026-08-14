"""Volume 03의 fresh MCP client configuration attestation verifier를 검증한다."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from ai_platform.mcp.client_acknowledgement import (
    McpClientConfigurationAcknowledgement,
    McpClientConfigurationApplication,
)
from ai_platform.mcp.client_attestation import (
    McpClientConfigurationAttestation,
    McpClientConfigurationAttestationError,
    McpClientConfigurationAttestationRequest,
    verify_mcp_client_configuration_attestation,
)
from ai_platform.mcp.client_handoff import McpClientIntegrationHandoff, McpClientKind

_CHALLENGE = "volume03-attestation-001"


@dataclass
class _OfflineVerifier:
    result: object = True
    calls: list[McpClientConfigurationAttestation] = field(default_factory=list)

    def verify(self, attestation: McpClientConfigurationAttestation) -> bool:
        self.calls.append(attestation)
        return self.result  # type: ignore[return-value]


class _FailingVerifier:
    def __init__(self) -> None:
        self.calls = 0

    def verify(self, attestation: McpClientConfigurationAttestation) -> bool:
        self.calls += 1
        raise RuntimeError("offline adapter failure")


def _request() -> McpClientConfigurationAttestationRequest:
    return McpClientConfigurationAttestationRequest(
        application=McpClientConfigurationApplication(
            handoff=McpClientIntegrationHandoff(
                client=McpClientKind.HERMES_AGENT,
                server_name="safe-tools",
                tool_names=("safe_calculator",),
            ),
            configuration_generation="deployment-revision-001",
        ),
        attestation_challenge=_CHALLENGE,
    )


def _attestation(**changes: object) -> McpClientConfigurationAttestation:
    values: dict[str, object] = {
        "acknowledgement": McpClientConfigurationAcknowledgement(
            client=McpClientKind.HERMES_AGENT,
            server_name="safe-tools",
            tool_names=("safe_calculator",),
            configuration_generation="deployment-revision-001",
        ),
        "attestation_challenge": _CHALLENGE,
    }
    values.update(changes)
    return McpClientConfigurationAttestation(**values)  # type: ignore[arg-type]


def test_verified_fresh_exact_attestation_returns_original_handoff_after_one_verifier_call() -> (
    None
):
    request = _request()
    attestation = _attestation()
    verifier = _OfflineVerifier()

    verified = verify_mcp_client_configuration_attestation(request, attestation, verifier)

    assert verified is request.application.handoff
    assert verifier.calls == [attestation]


def test_challenge_mismatch_is_rejected_before_verifier_call() -> None:
    verifier = _OfflineVerifier()

    with pytest.raises(
        McpClientConfigurationAttestationError,
        match="did not match the request",
    ):
        verify_mcp_client_configuration_attestation(
            _request(),
            _attestation(attestation_challenge="volume03-attestation-002"),
            verifier,
        )

    assert verifier.calls == []


def test_acknowledgement_mismatch_is_rejected_before_verifier_call() -> None:
    verifier = _OfflineVerifier()
    mismatched_acknowledgement = McpClientConfigurationAcknowledgement(
        client=McpClientKind.HERMES_AGENT,
        server_name="safe-tools",
        tool_names=("safe_text_case",),
        configuration_generation="deployment-revision-001",
    )

    with pytest.raises(
        McpClientConfigurationAttestationError,
        match="acknowledgement is invalid",
    ):
        verify_mcp_client_configuration_attestation(
            _request(),
            _attestation(acknowledgement=mismatched_acknowledgement),
            verifier,
        )

    assert verifier.calls == []


@pytest.mark.parametrize("result", (False, 1, "true", None))
def test_false_or_non_bool_verifier_result_is_rejected_without_handoff(
    result: object,
) -> None:
    verifier = _OfflineVerifier(result=result)

    with pytest.raises(
        McpClientConfigurationAttestationError,
        match="verification failed",
    ):
        verify_mcp_client_configuration_attestation(_request(), _attestation(), verifier)

    assert len(verifier.calls) == 1


def test_verifier_exception_hides_adapter_detail() -> None:
    verifier = _FailingVerifier()

    with pytest.raises(
        McpClientConfigurationAttestationError,
        match="verification failed",
    ) as error:
        verify_mcp_client_configuration_attestation(_request(), _attestation(), verifier)

    assert "offline adapter failure" not in str(error.value)
    assert verifier.calls == 1


@pytest.mark.parametrize("challenge", ("too-short", "valid-challenge\nother", "x" * 129))
def test_invalid_challenge_is_rejected_when_request_or_attestation_is_constructed(
    challenge: str,
) -> None:
    with pytest.raises(McpClientConfigurationAttestationError, match="challenge is invalid"):
        McpClientConfigurationAttestationRequest(
            application=_request().application,
            attestation_challenge=challenge,
        )
    with pytest.raises(McpClientConfigurationAttestationError, match="challenge is invalid"):
        _attestation(attestation_challenge=challenge)


def test_invalid_verifier_is_rejected_before_acknowledgement_trust() -> None:
    with pytest.raises(McpClientConfigurationAttestationError, match="verifier is invalid"):
        verify_mcp_client_configuration_attestation(
            _request(),
            _attestation(),
            object(),  # type: ignore[arg-type]
        )
