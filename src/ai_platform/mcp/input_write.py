"""MCP STDIO stdin JSON-RPC frame을 injected binary writer로 bounded 전송한다.

이 module은 subprocess, pipe 생성, child shutdown, retry 또는 network를 소유하지 않는다. trusted
host가 이미 만들고 검증한 immutable JSON-RPC request/notification frame만 작은 binary write로
전송하고, frame이 일부 전송되었을 수 있는 failure를 caller에게 명시한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ai_platform.mcp.stdio import (
    DEFAULT_MAX_MESSAGE_BYTES,
    McpStdioError,
    encode_stdio_jsonrpc_message,
    parse_stdio_jsonrpc_line,
)

_MAX_WRITE_CHUNK_BYTES = 4_096


class McpStdioInputWriteError(ValueError):
    """stdin frame contract 또는 injected writer failure를 나타낸다.

    ``frame_may_be_partial``이 참이면 receiver가 frame prefix 또는 complete frame을 이미 받았을 수
    있다. caller는 같은 request를 blind retry하거나 이 error로 child shutdown을 결정하지 않는다.
    """

    def __init__(self, message: str, *, frame_may_be_partial: bool) -> None:
        super().__init__(message)
        self.frame_may_be_partial = frame_may_be_partial


@runtime_checkable
class McpStdioWritableBinaryStream(Protocol):
    """host-owned child stdin의 최소 binary write/flush seam이다."""

    def write(self, data: bytes) -> int:
        """전송한 byte 수를 반환한다; zero/short write는 caller가 명시적으로 처리한다."""

    def flush(self) -> None:
        """이미 write한 bytes를 buffered writer에서 전송 계층으로 밀어낸다."""


@dataclass(frozen=True, slots=True)
class McpStdioInputFrame:
    """한 LF-delimited MCP JSON-RPC request 또는 notification의 immutable binary snapshot이다."""

    data: bytes

    def __post_init__(self) -> None:
        """untrusted raw bytes가 stdin framing을 우회하지 않게 construction 때 검증한다."""
        if not isinstance(self.data, bytes):
            raise McpStdioInputWriteError(
                "MCP STDIO input frame is invalid", frame_may_be_partial=False
            )
        try:
            line = self.data.decode("utf-8", errors="strict")
            parse_stdio_jsonrpc_line(line, max_message_bytes=DEFAULT_MAX_MESSAGE_BYTES)
        except (McpStdioError, UnicodeDecodeError):
            raise McpStdioInputWriteError(
                "MCP STDIO input frame is invalid", frame_may_be_partial=False
            ) from None

    @property
    def byte_count(self) -> int:
        """전송 전 immutable frame의 UTF-8 byte count를 반환한다."""
        return len(self.data)


@dataclass(frozen=True, slots=True)
class McpStdioInputWriteReceipt:
    """flush까지 성공한 local writer 호출의 immutable record다; peer receipt은 증명하지 않는다."""

    byte_count: int
    write_calls: int


def build_mcp_stdio_input_frame(payload: object) -> McpStdioInputFrame:
    """trusted request/notification object를 bounded UTF-8 JSON-RPC frame으로 만든다.

    Existing parser가 request/notification envelope, exact one-LF framing, duplicate key가 없는
    JSON object 및 16 KiB ceiling을 다시 검증한다. payload 값은 writer adapter에서 만들거나 바꾸지
    않는다.
    """
    if not isinstance(payload, dict):
        raise McpStdioInputWriteError(
            "MCP STDIO input payload is invalid", frame_may_be_partial=False
        )
    try:
        line = encode_stdio_jsonrpc_message(payload, max_message_bytes=DEFAULT_MAX_MESSAGE_BYTES)
        return McpStdioInputFrame(line.encode("utf-8"))
    except (McpStdioError, McpStdioInputWriteError, UnicodeEncodeError):
        raise McpStdioInputWriteError(
            "MCP STDIO input payload is invalid", frame_may_be_partial=False
        ) from None


def write_mcp_stdio_input_frame(
    stream: McpStdioWritableBinaryStream, frame: McpStdioInputFrame
) -> McpStdioInputWriteReceipt:
    """immutable frame을 4 KiB 이하 write로 완결 전송한 뒤 정확히 한 번 flush한다.

    Short positive write는 remaining bytes만 이어서 전송한다. exception, zero write, invalid count,
    flush failure에는 partial frame 가능성을 표시하고 no retry/no shutdown/no logging으로 종료한다.
    이 함수의 successful return은 local writer flush 완료일 뿐 MCP child의 JSON parse나 execution을
    보장하지 않는다.
    """
    if not isinstance(stream, McpStdioWritableBinaryStream):
        raise McpStdioInputWriteError(
            "MCP STDIO input stream is invalid", frame_may_be_partial=False
        )
    if not isinstance(frame, McpStdioInputFrame):
        raise McpStdioInputWriteError(
            "MCP STDIO input frame is invalid", frame_may_be_partial=False
        )

    offset = 0
    write_calls = 0
    while offset < frame.byte_count:
        chunk = frame.data[offset : offset + _MAX_WRITE_CHUNK_BYTES]
        try:
            written = stream.write(chunk)
        except Exception:
            raise McpStdioInputWriteError(
                "MCP STDIO input stream write failed", frame_may_be_partial=True
            ) from None
        write_calls += 1
        if isinstance(written, bool) or not isinstance(written, int):
            raise McpStdioInputWriteError(
                "MCP STDIO input stream returned an invalid write count", frame_may_be_partial=True
            )
        if written <= 0 or written > len(chunk):
            raise McpStdioInputWriteError(
                "MCP STDIO input stream returned an invalid write count", frame_may_be_partial=True
            )
        offset += written

    try:
        stream.flush()
    except Exception:
        raise McpStdioInputWriteError(
            "MCP STDIO input stream flush failed", frame_may_be_partial=True
        ) from None
    return McpStdioInputWriteReceipt(byte_count=offset, write_calls=write_calls)
