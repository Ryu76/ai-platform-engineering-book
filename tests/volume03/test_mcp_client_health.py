"""Volume 03 MCP client attestation 뒤 health probe를 검증한다."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from ai_platform.mcp.client_acknowledgement import (
    McpClientConfigurationAcknowledgement,
    McpClientConfigurationApplication,
)
from ai_platform.mcp.client_attestation import (
    McpClientConfigurationAttestation,
    McpClientConfigurationAttestationRequest,
)
from ai_platform.mcp.client_handoff import McpClientIntegrationHandoff, McpClientKind
from ai_platform.mcp.client_health import (
    McpClientConfigurationHealthError,
    verify_mcp_client_configuration_health,
)

_CHALLENGE = "volume03-health-challenge-001"


@dataclass
class _OfflineAttestationVerifier:
    result: object = True
    calls: list[McpClientConfigurationAttestation] = field(default_factory=list)

    def verify(self, attestation: McpClientConfigurationAttestation) -> bool:
        self.calls.append(attestation)
        return self.result  # type: ignore[return-value]


@dataclass
class _OfflineHealthProbe:
    result: object = True
    calls: list[McpClientConfigurationAttestationRequest] = field(default_factory=list)

    def probe(self, request: McpClientConfigurationAttestationRequest) -> bool:
        self.calls.append(request)
        return self.result  # type: ignore[return-value]


class _FailingHealthProbe:
    def __init__(self) -> None:
        self.calls = 0

    def probe(self, request: McpClientConfigurationAttestationRequest) -> bool:
        self.calls += 1
        raise RuntimeError("offline health probe adapter failure")


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


def test_attested_healthy_configuration_returns_original_handoff_after_one_call_per_seam() -> None:
    request = _request()
    attestation_verifier = _OfflineAttestationVerifier()
    health_probe = _OfflineHealthProbe()

    verified = verify_mcp_client_configuration_health(
        request,
        _attestation(),
        attestation_verifier,
        health_probe,
    )

    assert verified is request.application.handoff
    assert attestation_verifier.calls == [_attestation()]
    assert health_probe.calls == [request]


def test_invalid_attestation_is_rejected_before_health_probe_call() -> None:
    attestation_verifier = _OfflineAttestationVerifier()
    health_probe = _OfflineHealthProbe()

    with pytest.raises(McpClientConfigurationHealthError, match="attestation is invalid"):
        verify_mcp_client_configuration_health(
            _request(),
            _attestation(attestation_challenge="volume03-health-challenge-002"),
            attestation_verifier,
            health_probe,
        )

    assert len(attestation_verifier.calls) == 0
    assert health_probe.calls == []


def test_failed_attestation_verifier_is_rejected_before_health_probe_call() -> None:
    attestation_verifier = _OfflineAttestationVerifier(result=False)
    health_probe = _OfflineHealthProbe()

    with pytest.raises(McpClientConfigurationHealthError, match="attestation is invalid"):
        verify_mcp_client_configuration_health(
            _request(),
            _attestation(),
            attestation_verifier,
            health_probe,
        )

    assert len(attestation_verifier.calls) == 1
    assert health_probe.calls == []


@pytest.mark.parametrize("result", (False, 1, "healthy", None))
def test_false_or_non_bool_health_probe_result_is_rejected_without_handoff(result: object) -> None:
    health_probe = _OfflineHealthProbe(result=result)

    with pytest.raises(McpClientConfigurationHealthError, match="health probe failed"):
        verify_mcp_client_configuration_health(
            _request(),
            _attestation(),
            _OfflineAttestationVerifier(),
            health_probe,
        )

    assert len(health_probe.calls) == 1


def test_health_probe_exception_hides_adapter_detail() -> None:
    health_probe = _FailingHealthProbe()

    with pytest.raises(McpClientConfigurationHealthError, match="health probe failed") as error:
        verify_mcp_client_configuration_health(
            _request(),
            _attestation(),
            _OfflineAttestationVerifier(),
            health_probe,
        )

    assert "offline health probe adapter failure" not in str(error.value)
    assert health_probe.calls == 1


def test_invalid_health_probe_is_rejected_before_attestation_or_probe_call() -> None:
    attestation_verifier = _OfflineAttestationVerifier()

    with pytest.raises(McpClientConfigurationHealthError, match="health probe is invalid"):
        verify_mcp_client_configuration_health(
            _request(),
            _attestation(),
            attestation_verifier,
            object(),  # type: ignore[arg-type]
        )

    assert attestation_verifier.calls == []
