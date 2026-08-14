"""MCP client config adapter의 exact handoff acknowledgement를 memory model로 검증한다.

이 module은 Hermes/Codex CLI, configuration file, credential, reload command, subprocess, network
또는 Tool을 호출하지 않는다. 별도 client-specific adapter가 제출한 immutable acknowledgement가
deployment의 exact client-neutral handoff과 같은지만 검사한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_platform.mcp.client_handoff import (
    McpClientIntegrationHandoff,
    McpClientKind,
)


class McpClientConfigurationAcknowledgementError(ValueError):
    """client receipt가 trusted handoff과 일치하지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class McpClientConfigurationApplication:
    """별도 adapter가 적용할 exact handoff과 deployment-owned generation label이다.

    ``configuration_generation``은 config file path, content, credential 또는 client-specific
    schema가 아니다. Caller가 자신의 deployment revision을 opaque single-line label로 전달할 뿐이다.
    """

    handoff: McpClientIntegrationHandoff
    configuration_generation: str

    def __post_init__(self) -> None:
        """untrusted/malformed handoff과 ambiguous generation을 acknowledgement 전에 거부한다."""
        _validate_handoff(self.handoff)
        _validate_generation(self.configuration_generation)


@dataclass(frozen=True, slots=True)
class McpClientConfigurationAcknowledgement:
    """external client adapter가 실제 apply/reload 뒤 반환할 최소 exact visibility receipt다.

    Receipt는 successful application만 표현한다. Client-specific error, config content, secret,
    file path, reload log는 이 teaching boundary에 전달하거나 보관하지 않는다.
    """

    client: McpClientKind
    server_name: str
    tool_names: tuple[str, ...]
    configuration_generation: str

    def __post_init__(self) -> None:
        """acknowledgement가 wildcard/mutable visibility를 반사하지 않게 한다."""
        _validate_handoff(
            McpClientIntegrationHandoff(
                client=self.client,
                server_name=self.server_name,
                tool_names=self.tool_names,
            )
        )
        _validate_generation(self.configuration_generation)


def verify_mcp_client_configuration_acknowledgement(
    application: McpClientConfigurationApplication,
    acknowledgement: McpClientConfigurationAcknowledgement,
) -> McpClientIntegrationHandoff:
    """matching application receipt만 immutable handoff snapshot으로 반환한다.

    Caller는 이 return value를 actual client config가 secure하다는 증명으로 쓰면 안 된다.
    Client config schema/version, credential, file permission, atomic write, reload acknowledgement
    provenance와 connection health는 client-specific production adapter의 별도 검증 책임이다.
    """
    if not isinstance(application, McpClientConfigurationApplication):
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration application is invalid"
        )
    if not isinstance(acknowledgement, McpClientConfigurationAcknowledgement):
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration acknowledgement is invalid"
        )
    if acknowledgement.configuration_generation != application.configuration_generation:
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration acknowledgement does not match the application"
        )
    if (
        acknowledgement.client is not application.handoff.client
        or acknowledgement.server_name != application.handoff.server_name
        or acknowledgement.tool_names != application.handoff.tool_names
    ):
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration acknowledgement does not match the application"
        )
    return application.handoff


def _validate_handoff(handoff: object) -> None:
    """public dataclass direct construction도 exact immutable visibility contract에 다시 묶는다."""
    if not isinstance(handoff, McpClientIntegrationHandoff):
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration handoff is invalid"
        )
    if not isinstance(handoff.client, McpClientKind):
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration handoff is invalid"
        )
    if (
        not isinstance(handoff.server_name, str)
        or not handoff.server_name
        or len(handoff.server_name) > 128
        or any(character in "\x00\n\r" for character in handoff.server_name)
    ):
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration handoff is invalid"
        )
    _validate_exact_tool_names(handoff.tool_names)


def _validate_exact_tool_names(tool_names: object) -> None:
    """application과 receipt 모두 1–16 exact name tuple만 허용한다."""
    if not isinstance(tool_names, tuple) or not 1 <= len(tool_names) <= 16:
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration tool names are invalid"
        )
    for tool_name in tool_names:
        if (
            not isinstance(tool_name, str)
            or not tool_name
            or len(tool_name) > 128
            or any(character in "\x00\n\r*" for character in tool_name)
        ):
            raise McpClientConfigurationAcknowledgementError(
                "MCP client configuration tool names are invalid"
            )
    if len(tool_names) != len(set(tool_names)):
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration tool names are invalid"
        )


def _validate_generation(value: object) -> None:
    """receipt correlation label이 path/log injection으로 쓰이지 않도록 좁힌다."""
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or any(character in "\x00\n\r" for character in value)
    ):
        raise McpClientConfigurationAcknowledgementError(
            "MCP client configuration generation is invalid"
        )
