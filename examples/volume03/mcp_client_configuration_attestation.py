"""MCP client configuration attestation을 actual client/config 없이 fresh receipt로 검증한다."""

from __future__ import annotations

from ai_platform.mcp.client_acknowledgement import (
    McpClientConfigurationAcknowledgement,
    McpClientConfigurationApplication,
)
from ai_platform.mcp.client_attestation import (
    McpClientConfigurationAttestation,
    McpClientConfigurationAttestationRequest,
    verify_mcp_client_configuration_attestation,
)
from ai_platform.mcp.client_handoff import McpClientIntegrationHandoff, McpClientKind


class OfflineReceiptVerifier:
    """교육용 memory seam; signature, client, file, credential을 열지 않는다."""

    def __init__(self) -> None:
        self.calls = 0

    def verify(self, attestation: McpClientConfigurationAttestation) -> bool:
        """fixed in-memory attestation 하나를 승인한다."""
        self.calls += 1
        return attestation.attestation_challenge == "volume03-attestation-001"


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
        attestation_challenge="volume03-attestation-001",
    )
    attestation = McpClientConfigurationAttestation(
        acknowledgement=McpClientConfigurationAcknowledgement(
            client=McpClientKind.HERMES_AGENT,
            server_name="safe-tools",
            tool_names=("safe_calculator",),
            configuration_generation="volume03-demo-001",
        ),
        attestation_challenge="volume03-attestation-001",
    )
    verifier = OfflineReceiptVerifier()
    verified = verify_mcp_client_configuration_attestation(request, attestation, verifier)

    print(f"client: {verified.client}")
    print(f"server_name: {verified.server_name}")
    print(f"visible_tools: {','.join(verified.tool_names)}")
    print(f"verifier_calls: {verifier.calls}")


if __name__ == "__main__":
    main()
