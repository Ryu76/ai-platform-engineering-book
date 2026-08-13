"""Volume 03 MCP STDIO output decode/redaction의 offline boundary를 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.mcp.fair_drain import McpStdioStreamPairCapture
from ai_platform.mcp.output_decode import (
    McpStdioOutputDecodeError,
    McpStdioOutputRedactionPolicy,
    decode_and_redact_mcp_stdio_output,
)
from ai_platform.mcp.stream_drain import McpStdioStreamCapture


def _capture(
    *, stdout: bytes = b"safe stdout", stderr: bytes = b"safe stderr"
) -> McpStdioStreamPairCapture:
    return McpStdioStreamPairCapture(
        stdout=McpStdioStreamCapture(channel="stdout", data=stdout),
        stderr=McpStdioStreamCapture(channel="stderr", data=stderr),
    )


def test_decode_strict_utf8_and_redacts_fixed_literals_in_both_output_channels() -> None:
    capture = _capture(
        stdout=b"token=top-secret; status=ok",
        stderr=b"diagnostic top-secret",
    )
    policy = McpStdioOutputRedactionPolicy(literals=("top-secret",))

    result = decode_and_redact_mcp_stdio_output(capture, policy)

    assert result.stdout == "token=[REDACTED]; status=ok"
    assert result.stderr == "diagnostic [REDACTED]"


def test_redaction_replaces_longer_overlapping_literal_before_shorter_literal() -> None:
    capture = _capture(stdout=b"credential=abc123", stderr=b"")
    policy = McpStdioOutputRedactionPolicy(literals=("abc", "abc123"))

    result = decode_and_redact_mcp_stdio_output(capture, policy)

    assert result.stdout == "credential=[REDACTED]"
    assert result.stderr == ""


def test_empty_policy_keeps_decoded_offline_text_without_logging_or_process_io() -> None:
    result = decode_and_redact_mcp_stdio_output(
        _capture(stdout="안전".encode(), stderr=b""), McpStdioOutputRedactionPolicy(literals=())
    )

    assert result.stdout == "안전"
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("stdout", "stderr", "message"),
    (
        (b"\xffsecret", b"safe", "stdout output is not valid UTF-8"),
        (b"safe", b"\xffsecret", "stderr output is not valid UTF-8"),
    ),
)
def test_invalid_utf8_rejects_without_leaking_raw_output(
    stdout: bytes, stderr: bytes, message: str
) -> None:
    with pytest.raises(McpStdioOutputDecodeError, match=message) as error:
        decode_and_redact_mcp_stdio_output(
            _capture(stdout=stdout, stderr=stderr),
            McpStdioOutputRedactionPolicy(literals=("secret",)),
        )

    assert "secret" not in str(error.value)
    assert "ff" not in str(error.value)


@pytest.mark.parametrize(
    "literals",
    (
        ["not-a-tuple"],
        ("",),
        ("duplicate", "duplicate"),
        ("line\nbreak",),
        ("x" * 257,),
        tuple(str(index) for index in range(17)),
    ),
)
def test_policy_rejects_mutable_ambiguous_or_unbounded_literals(literals: object) -> None:
    with pytest.raises(McpStdioOutputDecodeError, match="redaction literals are invalid"):
        McpStdioOutputRedactionPolicy(literals=literals)  # type: ignore[arg-type]


def test_invalid_capture_or_policy_is_rejected_before_decode() -> None:
    with pytest.raises(McpStdioOutputDecodeError, match="output capture is invalid"):
        decode_and_redact_mcp_stdio_output(object(), McpStdioOutputRedactionPolicy(literals=()))  # type: ignore[arg-type]
    with pytest.raises(McpStdioOutputDecodeError, match="redaction policy is invalid"):
        decode_and_redact_mcp_stdio_output(_capture(), object())  # type: ignore[arg-type]


def test_swapped_or_non_bytes_capture_is_rejected_without_calling_decoder() -> None:
    swapped = McpStdioStreamPairCapture(
        stdout=McpStdioStreamCapture(channel="stderr", data=b"must-not-decode"),
        stderr=McpStdioStreamCapture(channel="stderr", data=b"safe"),
    )
    malformed = McpStdioStreamPairCapture(
        stdout=McpStdioStreamCapture(channel="stdout", data="must-not-decode"),  # type: ignore[arg-type]
        stderr=McpStdioStreamCapture(channel="stderr", data=b"safe"),
    )
    policy = McpStdioOutputRedactionPolicy(literals=())

    for capture in (swapped, malformed):
        with pytest.raises(McpStdioOutputDecodeError, match="output capture is invalid"):
            decode_and_redact_mcp_stdio_output(capture, policy)
