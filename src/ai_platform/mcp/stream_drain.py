"""MCP STDIO binary output 한 stream을 bounded fake seam으로 수집한다.

이 module은 process를 시작하거나 두 pipe를 동시에 drain하지 않는다. caller가 이미 소유한
하나의 binary readable stream에서 fixed-size bounded read만 수행한다. UTF-8 decode, redaction,
stdin write, cancellation, child shutdown과 backpressure scheduling은 별도 ownership이다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

_MAX_STREAM_BYTES = 1_048_576
_MIN_STREAM_BYTES = 1_024
_READ_CHUNK_BYTES = 4_096


class McpStdioStreamDrainError(ValueError):
    """MCP STDIO output stream contract 또는 bounded drain 실패를 나타낸다."""


@runtime_checkable
class McpStdioReadableBinaryStream(Protocol):
    """한 binary pipe에서 host가 읽는 최소 synchronous API다."""

    def read(self, size: int) -> bytes:
        """최대 ``size`` byte를 반환하고 EOF에서는 빈 bytes를 반환한다."""


@dataclass(frozen=True, slots=True)
class McpStdioStreamCapture:
    """EOF까지 성공적으로 수집한 한 allowlisted channel의 immutable raw-byte snapshot이다."""

    channel: Literal["stdout", "stderr"]
    data: bytes

    @property
    def byte_count(self) -> int:
        """decode 없이 수집한 raw byte 수를 반환한다."""
        return len(self.data)


def drain_mcp_stdio_binary_stream(
    stream: McpStdioReadableBinaryStream,
    *,
    channel: Literal["stdout", "stderr"],
    max_bytes: int,
) -> McpStdioStreamCapture:
    """한 binary stream을 EOF까지 읽되 configured byte ceiling을 넘기면 즉시 거부한다.

    각 read에는 ceiling보다 최대 한 byte 큰 요청만 전달한다. 따라서 overflow를 감지하면서도
    이 adapter가 한 번에 보관하는 untrusted input은 ``max_bytes + 1`` byte를 넘지 않는다.
    이 함수는 synchronous single-stream collector일 뿐 stdout/stderr concurrent scheduling을
    제공하지 않으며, failure 뒤 재시도하거나 process를 종료하지 않는다.
    """
    _validate_channel(channel)
    _validate_max_bytes(max_bytes)
    if not isinstance(stream, McpStdioReadableBinaryStream):
        raise McpStdioStreamDrainError("MCP STDIO stream is invalid")

    captured = bytearray()
    while True:
        remaining_with_overflow_sentinel = max_bytes - len(captured) + 1
        read_size = min(_READ_CHUNK_BYTES, remaining_with_overflow_sentinel)
        try:
            chunk = stream.read(read_size)
        except Exception:
            raise McpStdioStreamDrainError(f"MCP STDIO {channel} stream read failed") from None
        if not isinstance(chunk, bytes):
            raise McpStdioStreamDrainError(f"MCP STDIO {channel} stream returned non-bytes data")
        if not chunk:
            return McpStdioStreamCapture(channel=channel, data=bytes(captured))
        if len(chunk) > remaining_with_overflow_sentinel:
            raise McpStdioStreamDrainError(f"MCP STDIO {channel} stream violated read bound")
        if len(captured) + len(chunk) > max_bytes:
            raise McpStdioStreamDrainError(f"MCP STDIO {channel} stream exceeded byte budget")
        captured.extend(chunk)


def _validate_channel(channel: object) -> None:
    """Popen stream attribute나 arbitrary log label을 path처럼 해석하지 않는다."""
    if not isinstance(channel, str) or channel not in ("stdout", "stderr"):
        raise McpStdioStreamDrainError("MCP STDIO channel must be stdout or stderr")


def _validate_max_bytes(max_bytes: object) -> None:
    """launch plan과 같은 finite output budget만 허용한다."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
        raise McpStdioStreamDrainError("MCP STDIO stream byte budget is invalid")
    if not _MIN_STREAM_BYTES <= max_bytes <= _MAX_STREAM_BYTES:
        raise McpStdioStreamDrainError("MCP STDIO stream byte budget is invalid")
