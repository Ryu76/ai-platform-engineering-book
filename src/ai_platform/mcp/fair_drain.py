"""MCP STDIO의 두 binary output stream을 fake seam에서 공정하게 bounded drain한다.

이 module은 실제 Popen pipe, thread, selector, async event loop 또는 child shutdown을 소유하지
않는다. trusted host가 제공한 두 independent synchronous readable stream을 한 번씩 교대하여
읽는 deterministic model이다. 따라서 실제 blocking pipe의 deadlock/backpressure를 해결한다고
주장하지 않으며, OS-level concurrent IO는 별도 adapter의 책임이다.
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_platform.mcp.stream_drain import McpStdioReadableBinaryStream, McpStdioStreamCapture

_MAX_STREAM_BYTES = 1_048_576
_MIN_STREAM_BYTES = 1_024
_READ_CHUNK_BYTES = 4_096


class McpStdioFairDrainError(ValueError):
    """두 MCP STDIO output stream의 scheduling 또는 bounded drain 실패를 나타낸다."""


@dataclass(frozen=True, slots=True)
class McpStdioStreamPairCapture:
    """두 stream이 각각 EOF에 도달했을 때만 만드는 immutable raw-byte snapshot이다."""

    stdout: McpStdioStreamCapture
    stderr: McpStdioStreamCapture

    @property
    def total_byte_count(self) -> int:
        """decode 없이 두 independent capture의 총 raw byte 수를 반환한다."""
        return self.stdout.byte_count + self.stderr.byte_count


def drain_mcp_stdio_stream_pair_fairly(
    stdout_stream: McpStdioReadableBinaryStream,
    stderr_stream: McpStdioReadableBinaryStream,
    *,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> McpStdioStreamPairCapture:
    """두 fake stream을 EOF까지 round-robin으로 읽고 각자의 byte ceiling을 강제한다.

    시작 순서는 stdout이고, 아직 EOF가 아닌 각 channel에는 round마다 최대 한 번만 ``read``를
    요청한다. 어느 channel에서 overflow, malformed return 또는 read failure가 발생하면 partial
    capture를 반환하지 않고 어느 channel도 더 읽지 않는다. process shutdown·retry·decode·logging
    은 caller의 별도 ownership이다.
    """
    _validate_stream(stdout_stream, field_name="stdout stream")
    _validate_stream(stderr_stream, field_name="stderr stream")
    if stdout_stream is stderr_stream:
        raise McpStdioFairDrainError("stdout and stderr streams must be distinct")
    _validate_max_bytes(max_stdout_bytes, field_name="stdout byte budget")
    _validate_max_bytes(max_stderr_bytes, field_name="stderr byte budget")

    captures: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    streams = {"stdout": stdout_stream, "stderr": stderr_stream}
    limits = {"stdout": max_stdout_bytes, "stderr": max_stderr_bytes}
    complete = {"stdout": False, "stderr": False}

    while not all(complete.values()):
        for channel in ("stdout", "stderr"):
            if complete[channel]:
                continue
            chunk = _read_one_chunk(
                streams[channel],
                channel=channel,
                captured=captures[channel],
                max_bytes=limits[channel],
            )
            if chunk is None:
                complete[channel] = True
            else:
                captures[channel].extend(chunk)

    return McpStdioStreamPairCapture(
        stdout=McpStdioStreamCapture(channel="stdout", data=bytes(captures["stdout"])),
        stderr=McpStdioStreamCapture(channel="stderr", data=bytes(captures["stderr"])),
    )


def _read_one_chunk(
    stream: McpStdioReadableBinaryStream,
    *,
    channel: str,
    captured: bytearray,
    max_bytes: int,
) -> bytes | None:
    """한 scheduled turn만 수행하고 EOF, invalid input, overflow를 명시적으로 구분한다."""
    remaining_with_overflow_sentinel = max_bytes - len(captured) + 1
    read_size = min(_READ_CHUNK_BYTES, remaining_with_overflow_sentinel)
    try:
        chunk = stream.read(read_size)
    except Exception:
        raise McpStdioFairDrainError(f"MCP STDIO {channel} stream read failed") from None
    if not isinstance(chunk, bytes):
        raise McpStdioFairDrainError(f"MCP STDIO {channel} stream returned non-bytes data")
    if len(chunk) > remaining_with_overflow_sentinel:
        raise McpStdioFairDrainError(f"MCP STDIO {channel} stream violated read bound")
    if len(captured) + len(chunk) > max_bytes:
        raise McpStdioFairDrainError(f"MCP STDIO {channel} stream exceeded byte budget")
    if not chunk:
        return None
    return chunk


def _validate_stream(stream: object, *, field_name: str) -> None:
    """arbitrary object가 host-owned binary stream처럼 읽히지 않게 시작 전에 좁힌다."""
    if not isinstance(stream, McpStdioReadableBinaryStream):
        raise McpStdioFairDrainError(f"MCP STDIO {field_name} is invalid")


def _validate_max_bytes(max_bytes: object, *, field_name: str) -> None:
    """launch plan과 호환되는 finite independent output budget만 허용한다."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
        raise McpStdioFairDrainError(f"MCP STDIO {field_name} is invalid")
    if not _MIN_STREAM_BYTES <= max_bytes <= _MAX_STREAM_BYTES:
        raise McpStdioFairDrainError(f"MCP STDIO {field_name} is invalid")
