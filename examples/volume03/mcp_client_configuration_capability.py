"""MCP client capability receipt를 actual client/config 없이 healthy attestation에 연결한다."""

from __future__ import annotations

from ai_platform.mcp.client_acknowledgement import (
    McpClientConfigurationAcknowledgement,
    McpClientConfigurationApplication,
)
from ai_platform.mcp.client_attestation import (
    McpClientConfigurationAttestation,
    McpClientConfigurationAttestationRequest,
)
from ai_platform.mcp.client_capability import (
    McpClientConfigurationCapabilityReceipt,
    verify_mcp_client_configuration_capability,
)
from ai_platform.mcp.client_handoff import McpClientIntegrationHandoff, McpClientKind


class OfflineAttestationVerifier:
    """교육용 memory seam; credential, signature, client, file을 열지 않는다."""

    def verify(self, attestation: McpClientConfigurationAttestation) -> bool:
        """fixed in-memory challenge만 승인한다."""
        return attestation.attestation_challenge == "volume03-capability-challenge-001"


class OfflineHealthProbe:
    """교육용 memory seam; network, MCP session, subprocess를 열지 않는다."""

    def probe(self, request: McpClientConfigurationAttestationRequest) -> bool:
        """fixed deployment request 하나만 healthy라고 보고한다."""
        return request.application.configuration_generation == "volume03-demo-001"


class OfflineCapabilityProbe:
    """교육용 memory seam; actual client tools/list, process, network를 호출하지 않는다."""

    def __init__(self) -> None:
        self.calls = 0

    def inspect(
        self, request: McpClientConfigurationAttestationRequest
    ) -> McpClientConfigurationCapabilityReceipt:
        """fixed exact visible Tool tuple만 immutable receipt로 반환한다."""
        self.calls += 1
        return McpClientConfigurationCapabilityReceipt(request.application.handoff.tool_names)


def main() -> None:
    """fixed snapshots만 대조하며 client, config, process, Tool을 호출하지 않는다."""
    application = McpClientConfigurationApplication(
        handoff=McpClientIntegrationHandoff(
            client=McpClientKind.HERMES_AGENT,
            server_name="safe-tools",
            tool_names=("safe_calculator",),
        ),
        configuration_generation="volume03-demo-001",
    )
    request = McpClientConfigurationAttestationRequest(
        application=application,
        attestation_challenge="volume03-capability-challenge-001",
    )
    attestation = McpClientConfigurationAttestation(
        acknowledgement=McpClientConfigurationAcknowledgement(
            client=McpClientKind.HERMES_AGENT,
            server_name="safe-tools",
            tool_names=("safe_calculator",),
            configuration_generation="volume03-demo-001",
        ),
        attestation_challenge="volume03-capability-challenge-001",
    )
    capability_probe = OfflineCapabilityProbe()
    verified = verify_mcp_client_configuration_capability(
        request,
        attestation,
        OfflineAttestationVerifier(),
        OfflineHealthProbe(),
        capability_probe,
    )

    print(f"client: {verified.client}")
    print(f"server_name: {verified.server_name}")
    print(f"visible_tools: {','.join(verified.tool_names)}")
    print(f"capability_probe_calls: {capability_probe.calls}")


if __name__ == "__main__":
    main()
