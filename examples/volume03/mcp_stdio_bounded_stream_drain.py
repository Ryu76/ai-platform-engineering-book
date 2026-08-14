"""MCP STDIO output collector가 fake binary stream만 bounded drain함을 확인한다."""
from __future__ import annotations

from ai_platform.mcp.stream_drain import drain_mcp_stdio_binary_stream


class OfflineReadableStream:
    """OS pipe·subprocess 없이 고정 byte chunks만 반환한다."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks
        self.read_calls = 0

    def read(self, size: int) -> bytes:
        """요청 size보다 작은 planned chunk 하나를 반환한다."""
        self.read_calls += 1
        chunk = self._chunks.pop(0)
        assert len(chunk) <= size
        return chunk


def main() -> None:
    """fake stdout의 raw bytes를 decode나 process 없이 EOF까지 수집한다."""
    stream = OfflineReadableStream([b'{"jsonrpc":', b'"2.0"}\n', b""])
    capture = drain_mcp_stdio_binary_stream(stream, channel="stdout", max_bytes=1_024)

    print(f"channel: {capture.channel}")
    print(f"captured_bytes: {capture.byte_count}")
    print(f"read_calls: {stream.read_calls}")


if __name__ == "__main__":
    main()
