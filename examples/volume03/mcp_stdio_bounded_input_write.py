"""MCP STDIO stdin writer가 in-memory frame만 bounded 전송함을 확인한다."""
from __future__ import annotations

from ai_platform.mcp.input_write import (
    build_mcp_stdio_input_frame,
    write_mcp_stdio_input_frame,
)


class OfflineBinaryWriter:
    """process·OS pipe 없이 memory bytes와 write sizes만 기록한다."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.write_sizes: list[int] = []
        self.flush_calls = 0

    def write(self, data: bytes) -> int:
        """요청받은 fixed bytes 전부를 memory buffer에만 기록한다."""
        self.write_sizes.append(len(data))
        self.data.extend(data)
        return len(data)

    def flush(self) -> None:
        """실제 descriptor를 건드리지 않고 local call만 기록한다."""
        self.flush_calls += 1


def main() -> None:
    """고정 initialized notification을 offline writer에 전송하고 Tool을 실행하지 않는다."""
    writer = OfflineBinaryWriter()
    frame = build_mcp_stdio_input_frame(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}
    )
    receipt = write_mcp_stdio_input_frame(writer, frame)

    print(f"frame_bytes: {receipt.byte_count}")
    print(f"write_calls: {receipt.write_calls}")
    print(f"flush_calls: {writer.flush_calls}")


if __name__ == "__main__":
    main()
