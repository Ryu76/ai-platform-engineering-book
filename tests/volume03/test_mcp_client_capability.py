"""Volume 03 MCP client attested health 뒤 exact Tool capability를 검증한다."""

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
from ai_platform.mcp.client_capability import (
    McpClientConfigurationCapabilityError,
    McpClientConfigurationCapabilityReceipt,
    verify_mcp_client_configuration_capability,
)
from ai_platform.mcp.client_handoff import McpClientIntegrationHandoff, McpClientKind

_CHALLENGE = "volume03-capability-challenge-001"


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


@dataclass
class _OfflineCapabilityProbe:
    receipt: object = McpClientConfigurationCapabilityReceipt(("safe_calculator",))
    calls: list[McpClientConfigurationAttestationRequest] = field(default_factory=list)

    def inspect(
        self, request: McpClientConfigurationAttestationRequest
    ) -> McpClientConfigurationCapabilityReceipt:
        self.calls.append(request)
        return self.receipt  # type: ignore[return-value]


class _FailingCapabilityProbe:
    def __init__(self) -> None:
        self.calls = 0

    def inspect(
        self, request: McpClientConfigurationAttestationRequest
    ) -> McpClientConfigurationCapabilityReceipt:
        self.calls += 1
        raise RuntimeError("offline capability adapter failure")


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


def _attestation() -> McpClientConfigurationAttestation:
    return McpClientConfigurationAttestation(
        acknowledgement=McpClientConfigurationAcknowledgement(
            client=McpClientKind.HERMES_AGENT,
            server_name="safe-tools",
            tool_names=("safe_calculator",),
            configuration_generation="deployment-revision-001",
        ),
        attestation_challenge=_CHALLENGE,
    )


def test_attested_healthy_exact_capability_returns_original_handoff_after_one_call_per_seam() -> (
    None
):
    request = _request()
    attestation_verifier = _OfflineAttestationVerifier()
    health_probe = _OfflineHealthProbe()
    capability_probe = _OfflineCapabilityProbe()

    verified = verify_mcp_client_configuration_capability(
        request,
        _attestation(),
        attestation_verifier,
        health_probe,
        capability_probe,
    )

    assert verified is request.application.handoff
    assert attestation_verifier.calls == [_attestation()]
    assert health_probe.calls == [request]
    assert capability_probe.calls == [request]


def test_invalid_attestation_is_rejected_before_health_or_capability_probe_call() -> None:
    attestation_verifier = _OfflineAttestationVerifier()
    health_probe = _OfflineHealthProbe()
    capability_probe = _OfflineCapabilityProbe()
    invalid_attestation = McpClientConfigurationAttestation(
        acknowledgement=_attestation().acknowledgement,
        attestation_challenge="volume03-capability-challenge-002",
    )

    with pytest.raises(McpClientConfigurationCapabilityError, match="health is invalid"):
        verify_mcp_client_configuration_capability(
            _request(), invalid_attestation, attestation_verifier, health_probe, capability_probe
        )

    assert attestation_verifier.calls == []
    assert health_probe.calls == []
    assert capability_probe.calls == []


def test_failed_health_is_rejected_before_capability_probe_call() -> None:
    capability_probe = _OfflineCapabilityProbe()

    with pytest.raises(McpClientConfigurationCapabilityError, match="health is invalid"):
        verify_mcp_client_configuration_capability(
            _request(),
            _attestation(),
            _OfflineAttestationVerifier(),
            _OfflineHealthProbe(result=False),
            capability_probe,
        )

    assert capability_probe.calls == []


@pytest.mark.parametrize(
    "receipt",
    (
        McpClientConfigurationCapabilityReceipt(("different_safe_tool",)),
        McpClientConfigurationCapabilityReceipt(("safe_calculator", "another_safe_tool")),
        object(),
    ),
)
def test_mismatched_or_malformed_capability_receipt_is_rejected_without_handoff(
    receipt: object,
) -> None:
    capability_probe = _OfflineCapabilityProbe(receipt=receipt)

    with pytest.raises(McpClientConfigurationCapabilityError):
        verify_mcp_client_configuration_capability(
            _request(),
            _attestation(),
            _OfflineAttestationVerifier(),
            _OfflineHealthProbe(),
            capability_probe,
        )

    assert len(capability_probe.calls) == 1


def test_capability_probe_exception_hides_adapter_detail() -> None:
    capability_probe = _FailingCapabilityProbe()

    with pytest.raises(
        McpClientConfigurationCapabilityError, match="capability probe failed"
    ) as error:
        verify_mcp_client_configuration_capability(
            _request(),
            _attestation(),
            _OfflineAttestationVerifier(),
            _OfflineHealthProbe(),
            capability_probe,
        )

    assert "offline capability adapter failure" not in str(error.value)
    assert capability_probe.calls == 1


def test_mutated_capability_receipt_is_revalidated_after_probe_call() -> None:
    receipt = McpClientConfigurationCapabilityReceipt(("safe_calculator",))
    object.__setattr__(receipt, "tool_names", ["safe_calculator"])
    capability_probe = _OfflineCapabilityProbe(receipt=receipt)

    with pytest.raises(McpClientConfigurationCapabilityError, match="capability probe failed"):
        verify_mcp_client_configuration_capability(
            _request(),
            _attestation(),
            _OfflineAttestationVerifier(),
            _OfflineHealthProbe(),
            capability_probe,
        )

    assert len(capability_probe.calls) == 1


def test_invalid_capability_probe_is_rejected_before_any_other_seam_call() -> None:
    attestation_verifier = _OfflineAttestationVerifier()
    health_probe = _OfflineHealthProbe()

    with pytest.raises(McpClientConfigurationCapabilityError, match="capability probe is invalid"):
        verify_mcp_client_configuration_capability(
            _request(),
            _attestation(),
            attestation_verifier,
            health_probe,
            object(),  # type: ignore[arg-type]
        )

    assert attestation_verifier.calls == []
    assert health_probe.calls == []
