"""MCP STDIO Popen stdin ownership을 memory-only fake seam으로 확인한다."""

from __future__ import annotations

from ai_platform.mcp.input_write import build_mcp_stdio_input_frame
from ai_platform.mcp.popen_input import McpStdioPopenInputOwner


class OfflineBinaryWriter:
    """실제 pipe·process 없이 bytes와 flush 호출만 기록한다."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.flush_calls = 0

    def write(self, data: bytes) -> int:
        self.data.extend(data)
        return len(data)

    def flush(self) -> None:
        self.flush_calls += 1


class OfflinePopen:
    """실제 Popen을 호출하지 않는 live-process snapshot seam이다."""

    def __init__(self, stdin: OfflineBinaryWriter) -> None:
        self.stdin = stdin
        self.poll_calls = 0

    def poll(self) -> int | None:
        self.poll_calls += 1
        return None


def main() -> None:
    """allowlisted-looking fixed frame만 in-memory stdin snapshot에 전달한다."""
    writer = OfflineBinaryWriter()
    process = OfflinePopen(writer)
    owner = McpStdioPopenInputOwner(process)
    frame = build_mcp_stdio_input_frame(
        {"jsonrpc": "2.0", "id": "popen-input-demo-001", "method": "safe/test"}
    )
    receipt = owner.write("popen-input-demo-001", frame)

    print(f"correlation_id: {receipt.correlation_id}")
    print(f"frame_bytes: {receipt.write_receipt.byte_count}")
    print(f"poll_calls: {process.poll_calls}")
    print(f"flush_calls: {writer.flush_calls}")
    print(f"state: {owner.state}")


if __name__ == "__main__":
    main()
