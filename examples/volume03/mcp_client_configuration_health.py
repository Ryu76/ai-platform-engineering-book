"""MCP client health evidence를 actual client/config 없이 attested fixture에 연결한다."""

from __future__ import annotations

from ai_platform.mcp.client_acknowledgement import (
    McpClientConfigurationAcknowledgement,
    McpClientConfigurationApplication,
)
from ai_platform.mcp.client_attestation import (
    McpClientConfigurationAttestation,
    McpClientConfigurationAttestationRequest,
)
from ai_platform.mcp.client_handoff import McpClientIntegrationHandoff, McpClientKind
from ai_platform.mcp.client_health import verify_mcp_client_configuration_health


class OfflineAttestationVerifier:
    """교육용 memory seam; credential, signature, client, file을 열지 않는다."""

    def verify(self, attestation: McpClientConfigurationAttestation) -> bool:
        """fixed in-memory challenge만 승인한다."""
        return attestation.attestation_challenge == "volume03-health-challenge-001"


class OfflineHealthProbe:
    """교육용 memory seam; network, MCP session, subprocess를 열지 않는다."""

    def __init__(self) -> None:
        self.calls = 0

    def probe(self, request: McpClientConfigurationAttestationRequest) -> bool:
        """fixed deployment request 하나만 healthy라고 보고한다."""
        self.calls += 1
        return request.application.configuration_generation == "volume03-demo-001"


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
        attestation_challenge="volume03-health-challenge-001",
    )
    attestation = McpClientConfigurationAttestation(
        acknowledgement=McpClientConfigurationAcknowledgement(
            client=McpClientKind.HERMES_AGENT,
            server_name="safe-tools",
            tool_names=("safe_calculator",),
            configuration_generation="volume03-demo-001",
        ),
        attestation_challenge="volume03-health-challenge-001",
    )
    health_probe = OfflineHealthProbe()
    verified = verify_mcp_client_configuration_health(
        request,
        attestation,
        OfflineAttestationVerifier(),
        health_probe,
    )

    print(f"client: {verified.client}")
    print(f"server_name: {verified.server_name}")
    print(f"visible_tools: {','.join(verified.tool_names)}")
    print(f"health_probe_calls: {health_probe.calls}")


if __name__ == "__main__":
    main()
