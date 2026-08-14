"""Volume 03의 fake MCP STDIO two-stream fair bounded drain을 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.mcp.fair_drain import (
    McpStdioFairDrainError,
    drain_mcp_stdio_stream_pair_fairly,
)


class _FakeScheduledStream:
    """OS pipe 없이 planned chunks를 제공하고 scheduler turn을 trace한다."""

    def __init__(self, name: str, chunks: list[bytes | object], trace: list[str]) -> None:
        self._name = name
        self._chunks = chunks
        self._trace = trace
        self.read_sizes: list[int] = []

    def read(self, size: int) -> bytes:
        self._trace.append(self._name)
        self.read_sizes.append(size)
        chunk = self._chunks.pop(0)
        if isinstance(chunk, BaseException):
            raise chunk
        return chunk  # type: ignore[return-value]


def test_drain_interleaves_each_unfinished_stream_once_per_round_until_both_eof() -> None:
    trace: list[str] = []
    stdout = _FakeScheduledStream("stdout", [b"out-1", b"out-2", b""], trace)
    stderr = _FakeScheduledStream("stderr", [b"err-1", b"err-2", b""], trace)

    capture = drain_mcp_stdio_stream_pair_fairly(
        stdout, stderr, max_stdout_bytes=1_024, max_stderr_bytes=1_024
    )

    assert capture.stdout.data == b"out-1out-2"
    assert capture.stderr.data == b"err-1err-2"
    assert capture.total_byte_count == 20
    assert trace == ["stdout", "stderr", "stdout", "stderr", "stdout", "stderr"]
    assert stdout.read_sizes == [1_025, 1_020, 1_015]
    assert stderr.read_sizes == [1_025, 1_020, 1_015]


def test_drain_skips_eof_stream_without_starving_remaining_stream() -> None:
    trace: list[str] = []
    stdout = _FakeScheduledStream("stdout", [b""], trace)
    stderr = _FakeScheduledStream("stderr", [b"one", b"two", b""], trace)

    capture = drain_mcp_stdio_stream_pair_fairly(
        stdout, stderr, max_stdout_bytes=1_024, max_stderr_bytes=1_024
    )

    assert capture.stdout.data == b""
    assert capture.stderr.data == b"onetwo"
    assert trace == ["stdout", "stderr", "stderr", "stderr"]


def test_stdout_overflow_stops_before_any_further_stream_reads_or_partial_capture() -> None:
    trace: list[str] = []
    stdout = _FakeScheduledStream("stdout", [b"a", b"b" * 1_024, b"must-not-be-read"], trace)
    stderr = _FakeScheduledStream("stderr", [b"safe", b"must-not-be-read"], trace)

    with pytest.raises(McpStdioFairDrainError, match="stdout stream exceeded byte budget"):
        drain_mcp_stdio_stream_pair_fairly(
            stdout, stderr, max_stdout_bytes=1_024, max_stderr_bytes=1_024
        )

    assert trace == ["stdout", "stderr", "stdout"]


def test_stderr_read_failure_stops_before_next_stdout_turn_and_hides_adapter_detail() -> None:
    trace: list[str] = []
    stdout = _FakeScheduledStream("stdout", [b"safe", b"must-not-be-read"], trace)
    stderr = _FakeScheduledStream("stderr", [RuntimeError("secret pipe handle")], trace)

    with pytest.raises(McpStdioFairDrainError, match="stderr stream read failed") as error:
        drain_mcp_stdio_stream_pair_fairly(
            stdout, stderr, max_stdout_bytes=1_024, max_stderr_bytes=1_024
        )

    assert "secret pipe handle" not in str(error.value)
    assert trace == ["stdout", "stderr"]


def test_non_bytes_stderr_stops_before_next_stdout_turn_or_decode() -> None:
    trace: list[str] = []
    stdout = _FakeScheduledStream("stdout", [b"safe", b"must-not-be-read"], trace)
    stderr = _FakeScheduledStream("stderr", [bytearray(b"untrusted")], trace)

    with pytest.raises(McpStdioFairDrainError, match="stderr stream returned non-bytes data"):
        drain_mcp_stdio_stream_pair_fairly(
            stdout, stderr, max_stdout_bytes=1_024, max_stderr_bytes=1_024
        )

    assert trace == ["stdout", "stderr"]


def test_drain_rejects_read_bound_violation_without_reading_other_stream() -> None:
    trace: list[str] = []
    stdout = _FakeScheduledStream("stdout", [b"a" * 1_026], trace)
    stderr = _FakeScheduledStream("stderr", [b"must-not-be-read"], trace)

    with pytest.raises(McpStdioFairDrainError, match="stdout stream violated read bound"):
        drain_mcp_stdio_stream_pair_fairly(
            stdout, stderr, max_stdout_bytes=1_024, max_stderr_bytes=1_024
        )

    assert trace == ["stdout"]


@pytest.mark.parametrize(
    ("stdout_stream", "stderr_stream", "max_stdout_bytes", "max_stderr_bytes", "message"),
    (
        (object(), object(), 1_024, 1_024, "stdout stream is invalid"),
        (None, object(), 1_024, 1_024, "stdout stream is invalid"),
        ("not-a-stream", "not-a-stream", 1_024, 1_024, "stdout stream is invalid"),
    ),
)
def test_drain_rejects_invalid_streams_before_any_read(
    stdout_stream: object,
    stderr_stream: object,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
    message: str,
) -> None:
    with pytest.raises(McpStdioFairDrainError, match=message):
        drain_mcp_stdio_stream_pair_fairly(
            stdout_stream,  # type: ignore[arg-type]
            stderr_stream,  # type: ignore[arg-type]
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
        )


def test_drain_rejects_same_stream_and_invalid_budget_before_reading() -> None:
    trace: list[str] = []
    stream = _FakeScheduledStream("shared", [b"must-not-be-read"], trace)

    with pytest.raises(McpStdioFairDrainError, match="must be distinct"):
        drain_mcp_stdio_stream_pair_fairly(
            stream, stream, max_stdout_bytes=1_024, max_stderr_bytes=1_024
        )
    with pytest.raises(McpStdioFairDrainError, match="stderr byte budget is invalid"):
        drain_mcp_stdio_stream_pair_fairly(
            stream, _FakeScheduledStream("stderr", [b"must-not-be-read"], trace),
            max_stdout_bytes=1_024,
            max_stderr_bytes=True,  # type: ignore[arg-type]
        )

    assert trace == []


def test_drain_rejects_invalid_stderr_stream_before_stdout_can_read() -> None:
    trace: list[str] = []
    stdout = _FakeScheduledStream("stdout", [b"must-not-be-read"], trace)

    with pytest.raises(McpStdioFairDrainError, match="stderr stream is invalid"):
        drain_mcp_stdio_stream_pair_fairly(
            stdout, object(), max_stdout_bytes=1_024, max_stderr_bytes=1_024  # type: ignore[arg-type]
        )

    assert trace == []
