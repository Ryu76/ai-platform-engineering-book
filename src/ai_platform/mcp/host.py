"""MCP STDIO subprocess를 열기 전, trusted host의 고정 launch plan만 모델링한다.

이 모듈은 ``subprocess``, shell, signal 또는 OS pipe를 열지 않는다. 호출자가 제공한
server selector는 exact allowlist lookup에만 쓰이며, 반환하는 immutable plan은 host가
별도로 안전하게 실행할 수 있도록 필요한 resource bound만 표현한다.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType


class McpStdioHostError(ValueError):
    """MCP STDIO host launch configuration 또는 allowlist selector가 유효하지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class McpStdioServerSpec:
    """신뢰된 deployment configuration에 둔 하나의 shell-free MCP server 정의다.

    ``argv``는 OS shell command string이 아니라 그대로 subprocess argv로 전달할 tuple이다.
    이 교육용 모델은 process를 실행하지 않으며 Tool 실행 권한도 부여하지 않는다.
    """

    name: str
    argv: tuple[str, ...]
    max_stdout_bytes: int
    max_stderr_bytes: int
    shutdown_grace_seconds: float
    restart_limit: int

    def __post_init__(self) -> None:
        """shell parsing에 의존하지 않는 고정 argv와 유한한 host resource budget을 강제한다."""
        _validate_server_name(self.name)
        _validate_argv(self.argv)
        _validate_stream_limit(self.max_stdout_bytes, field_name="max_stdout_bytes")
        _validate_stream_limit(self.max_stderr_bytes, field_name="max_stderr_bytes")
        _validate_shutdown_grace_seconds(self.shutdown_grace_seconds)
        _validate_restart_limit(self.restart_limit)


@dataclass(frozen=True, slots=True)
class McpStdioHostLaunchPlan:
    """exact allowlist selector에서만 얻는 immutable subprocess launch snapshot이다."""

    server_name: str
    argv: tuple[str, ...]
    max_stdout_bytes: int
    max_stderr_bytes: int
    shutdown_grace_seconds: float
    restart_limit: int


class McpStdioHostAllowlist:
    """untrusted selector가 새 command, shell flag, resource limit을 주입하지 못하게 한다."""

    def __init__(self, servers: tuple[McpStdioServerSpec, ...]) -> None:
        """deployment 시점의 고정 server spec만 snapshot으로 받아 name 충돌을 거부한다."""
        if not isinstance(servers, tuple) or not servers:
            raise McpStdioHostError("servers must be a non-empty tuple of trusted server specs")
        by_name: dict[str, McpStdioServerSpec] = {}
        for server in servers:
            if not isinstance(server, McpStdioServerSpec):
                raise McpStdioHostError("servers must contain only McpStdioServerSpec values")
            if server.name in by_name:
                raise McpStdioHostError(f"duplicate MCP STDIO server name: {server.name}")
            by_name[server.name] = server
        self._by_name: Mapping[str, McpStdioServerSpec] = MappingProxyType(by_name)

    def server_names(self) -> tuple[str, ...]:
        """host가 review 가능한 고정 allowlisted server name snapshot을 반환한다."""
        return tuple(self._by_name)

    def prepare_launch(self, server_name: str) -> McpStdioHostLaunchPlan:
        """exact selector의 static plan만 반환하며 unknown name에는 command 정보를 주지 않는다."""
        if not isinstance(server_name, str) or server_name not in self._by_name:
            raise McpStdioHostError("MCP STDIO server is not allowlisted")
        server = self._by_name[server_name]
        return McpStdioHostLaunchPlan(
            server_name=server.name,
            argv=server.argv,
            max_stdout_bytes=server.max_stdout_bytes,
            max_stderr_bytes=server.max_stderr_bytes,
            shutdown_grace_seconds=server.shutdown_grace_seconds,
            restart_limit=server.restart_limit,
        )


def _validate_server_name(name: object) -> None:
    """로그·config key를 흐리지 않는 작은 lowercase server identifier만 허용한다."""
    if not isinstance(name, str) or not name or len(name) > 64:
        raise McpStdioHostError("server name must be a non-empty string of at most 64 characters")
    allowed_characters = "abcdefghijklmnopqrstuvwxyz0123456789-"
    if name[0] == "-" or any(character not in allowed_characters for character in name):
        raise McpStdioHostError(
            "server name must contain only lowercase letters, digits, and hyphens"
        )


def _validate_argv(argv: object) -> None:
    """shell command text가 아닌 작은 immutable argv tuple만 허용한다."""
    if not isinstance(argv, tuple) or not 1 <= len(argv) <= 16:
        raise McpStdioHostError("argv must be a tuple with between 1 and 16 arguments")
    for argument in argv:
        if not isinstance(argument, str) or not argument or len(argument) > 512:
            raise McpStdioHostError(
                "each argv argument must be a non-empty string of at most 512 characters"
            )
        if "\x00" in argument or "\n" in argument or "\r" in argument:
            raise McpStdioHostError("argv arguments must not contain NUL or line-break characters")


def _validate_stream_limit(value: object, *, field_name: str) -> None:
    """stdout/stderr가 무제한 메모리를 쓰지 않도록 byte ceiling을 검증한다."""
    if isinstance(value, bool) or not isinstance(value, int) or not 1024 <= value <= 1_048_576:
        raise McpStdioHostError(f"{field_name} must be an integer between 1024 and 1048576")


def _validate_shutdown_grace_seconds(value: object) -> None:
    """cancellation 이후 host가 기다릴 유한한 grace period만 허용한다."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise McpStdioHostError("shutdown_grace_seconds must be a finite number between 0.1 and 60")
    if not isfinite(value) or not 0.1 <= value <= 60:
        raise McpStdioHostError("shutdown_grace_seconds must be a finite number between 0.1 and 60")


def _validate_restart_limit(value: object) -> None:
    """crash/disconnect restart가 무한 loop가 되지 않도록 작은 retry budget을 강제한다."""
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3:
        raise McpStdioHostError("restart_limit must be an integer between 0 and 3")
