"""MCP STDIO의 성공한 raw output snapshot을 strict decode하고 fixed literal을 redaction한다.

이 module은 subprocess, pipe, scheduler, logging 또는 network를 소유하지 않는다. caller는 이미
bounded drain이 EOF까지 성공한 immutable raw-byte pair만 전달한다. trusted deployment policy의
고정 literal만 stdout/stderr text snapshot에 적용하며, 이 결과를 어디에 기록할지는 caller의
별도 ownership이다.
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_platform.mcp.fair_drain import McpStdioStreamPairCapture
from ai_platform.mcp.stream_drain import McpStdioStreamCapture

_REDACTION_REPLACEMENT = "[REDACTED]"
_MAX_REDACTION_LITERAL_COUNT = 16
_MAX_REDACTION_LITERAL_LENGTH = 256


class McpStdioOutputDecodeError(ValueError):
    """raw output snapshot 또는 trusted redaction policy가 안전하게 해석되지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class McpStdioOutputRedactionPolicy:
    """deployment에서 검토한 fixed literal redaction 목록이다.

    literal은 request/model/MCP output에서 만들지 않는다. 빈 literal은 모든 text 경계에 삽입될 수
    있으므로 금지하고, overlap은 긴 literal부터 적용해 짧은 token이 긴 secret의 일부만 가리지
    않게 한다.
    """

    literals: tuple[str, ...]

    def __post_init__(self) -> None:
        """작고 immutable한 trusted literal allowlist만 허용한다."""
        if (
            not isinstance(self.literals, tuple)
            or len(self.literals) > _MAX_REDACTION_LITERAL_COUNT
        ):
            raise McpStdioOutputDecodeError("MCP STDIO redaction literals are invalid")
        if any(
            not isinstance(literal, str)
            or not literal
            or len(literal) > _MAX_REDACTION_LITERAL_LENGTH
            or "\x00" in literal
            or "\n" in literal
            or "\r" in literal
            for literal in self.literals
        ):
            raise McpStdioOutputDecodeError("MCP STDIO redaction literals are invalid")
        if len(set(self.literals)) != len(self.literals):
            raise McpStdioOutputDecodeError("MCP STDIO redaction literals are invalid")


@dataclass(frozen=True, slots=True)
class McpStdioDecodedOutputPair:
    """strict UTF-8 decode와 literal redaction 뒤의 immutable two-channel text snapshot이다."""

    stdout: str
    stderr: str


def decode_and_redact_mcp_stdio_output(
    capture: McpStdioStreamPairCapture, policy: McpStdioOutputRedactionPolicy
) -> McpStdioDecodedOutputPair:
    """성공한 raw capture를 strict UTF-8로 decode하고 trusted literals만 가린다.

    invalid UTF-8, malformed channel capture, invalid policy에는 raw data나 decoder detail을
    포함하지 않는 generic error를 내고 partial text를 반환하지 않는다. JSON-RPC framing,
    structured log emission, process shutdown, retry는 이 boundary의 책임이 아니다.
    """
    _validate_capture(capture)
    _validate_policy(policy)
    stdout = _decode_channel(capture.stdout)
    stderr = _decode_channel(capture.stderr)
    return McpStdioDecodedOutputPair(
        stdout=_redact(stdout, policy), stderr=_redact(stderr, policy)
    )


def _validate_capture(capture: object) -> None:
    """직접 구성된 arbitrary object 또는 swapped output channel을 decode 전에 거부한다."""
    if not isinstance(capture, McpStdioStreamPairCapture):
        raise McpStdioOutputDecodeError("MCP STDIO output capture is invalid")
    if (
        not isinstance(capture.stdout, McpStdioStreamCapture)
        or capture.stdout.channel != "stdout"
        or not isinstance(capture.stdout.data, bytes)
        or not isinstance(capture.stderr, McpStdioStreamCapture)
        or capture.stderr.channel != "stderr"
        or not isinstance(capture.stderr.data, bytes)
    ):
        raise McpStdioOutputDecodeError("MCP STDIO output capture is invalid")


def _validate_policy(policy: object) -> None:
    """untrusted custom callback 대신 typed immutable policy만 허용한다."""
    if not isinstance(policy, McpStdioOutputRedactionPolicy):
        raise McpStdioOutputDecodeError("MCP STDIO redaction policy is invalid")


def _decode_channel(capture: McpStdioStreamCapture) -> str:
    """decoder exception detail과 raw bytes를 외부 error에서 숨긴다."""
    try:
        return capture.data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise McpStdioOutputDecodeError(
            f"MCP STDIO {capture.channel} output is not valid UTF-8"
        ) from None


def _redact(text: str, policy: McpStdioOutputRedactionPolicy) -> str:
    """긴 literal부터 deterministic하게 전부 mask하며 external action을 하지 않는다."""
    redacted = text
    for literal in sorted(policy.literals, key=lambda value: (-len(value), value)):
        redacted = redacted.replace(literal, _REDACTION_REPLACEMENT)
    return redacted
