"""Volume 03의 bounded MCP STDIO binary output collector를 real pipe 없이 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.mcp.stream_drain import (
    McpStdioStreamDrainError,
    drain_mcp_stdio_binary_stream,
)


class _FakeReadableStream:
    """OS pipe 없이 planned chunks와 read size만 메모리에서 제공한다."""

    def __init__(self, chunks: list[bytes | object]) -> None:
        self._chunks = chunks
        self.read_sizes: list[int] = []

    def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        chunk = self._chunks.pop(0)
        if isinstance(chunk, BaseException):
            raise chunk
        return chunk  # type: ignore[return-value]


def test_drain_collects_one_binary_stdout_stream_to_eof_with_fixed_bounded_reads() -> None:
    stream = _FakeReadableStream([b'{"jsonrpc":', b'"2.0"}\n', b""])

    capture = drain_mcp_stdio_binary_stream(stream, channel="stdout", max_bytes=1_024)

    assert capture.channel == "stdout"
    assert capture.data == b'{"jsonrpc":"2.0"}\n'
    assert capture.byte_count == 18
    assert stream.read_sizes == [1_025, 1_014, 1_007]


def test_drain_reads_at_most_one_overflow_sentinel_byte_beyond_the_budget_then_stops() -> None:
    stream = _FakeReadableStream([b"a" * 1_025, b"must-not-be-read"])

    with pytest.raises(McpStdioStreamDrainError, match="stdout stream exceeded byte budget"):
        drain_mcp_stdio_binary_stream(stream, channel="stdout", max_bytes=1_024)

    assert stream.read_sizes == [1_025]


def test_drain_rejects_stream_that_returns_more_than_requested_without_retaining_it() -> None:
    stream = _FakeReadableStream([b"a" * 1_026])

    with pytest.raises(McpStdioStreamDrainError, match="stderr stream violated read bound"):
        drain_mcp_stdio_binary_stream(stream, channel="stderr", max_bytes=1_024)

    assert stream.read_sizes == [1_025]


def test_drain_rejects_non_bytes_result_before_decoding_or_logging_raw_content() -> None:
    stream = _FakeReadableStream([bytearray(b"untrusted")])

    with pytest.raises(McpStdioStreamDrainError, match="stdout stream returned non-bytes data"):
        drain_mcp_stdio_binary_stream(stream, channel="stdout", max_bytes=1_024)

    assert stream.read_sizes == [1_025]


def test_drain_narrows_stream_read_failure_without_leaking_raw_adapter_detail() -> None:
    stream = _FakeReadableStream([RuntimeError("secret pipe path must not leak")])

    with pytest.raises(McpStdioStreamDrainError, match="stderr stream read failed") as error:
        drain_mcp_stdio_binary_stream(stream, channel="stderr", max_bytes=1_024)

    assert "secret pipe path" not in str(error.value)


@pytest.mark.parametrize(
    ("channel", "max_bytes", "message"),
    (
        ("stdin", 1_024, "channel"),
        ("stdout", 1_023, "byte budget"),
        ("stdout", True, "byte budget"),
        ("stdout", 1_048_577, "byte budget"),
    ),
)
def test_drain_rejects_untrusted_channel_or_unbounded_budget_before_any_read(
    channel: object, max_bytes: object, message: str
) -> None:
    stream = _FakeReadableStream([b"must-not-be-read"])

    with pytest.raises(McpStdioStreamDrainError, match=message):
        drain_mcp_stdio_binary_stream(
            stream, channel=channel, max_bytes=max_bytes  # type: ignore[arg-type]
        )

    assert stream.read_sizes == []


def test_drain_rejects_object_without_binary_read_contract_before_any_read() -> None:
    with pytest.raises(McpStdioStreamDrainError, match="stream is invalid"):
        drain_mcp_stdio_binary_stream(object(), channel="stdout", max_bytes=1_024)  # type: ignore[arg-type]
