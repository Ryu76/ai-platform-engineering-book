"""MCP STDIO delivery gate가 cancellation·disconnect·ambiguity를 offline으로 분리함을 보인다."""

from __future__ import annotations

from ai_platform.mcp.input_delivery import McpStdioInputDeliveryGate
from ai_platform.mcp.input_write import build_mcp_stdio_input_frame


class OfflineBinaryWriter:
    """process·OS pipe 없이 memory bytes와 flush 호출만 기록한다."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.flush_calls = 0

    def write(self, data: bytes) -> int:
        self.data.extend(data)
        return len(data)

    def flush(self) -> None:
        self.flush_calls += 1


def main() -> None:
    """고정 typed ID의 frame만 쓰고 실제 child·Tool·네트워크를 호출하지 않는다."""
    gate = McpStdioInputDeliveryGate()
    writer = OfflineBinaryWriter()
    frame = build_mcp_stdio_input_frame(
        {"jsonrpc": "2.0", "id": "delivery-demo-001", "method": "safe/test"}
    )
    receipt = gate.write("delivery-demo-001", writer, frame)

    print(f"correlation_id: {receipt.correlation_id}")
    print(f"frame_bytes: {receipt.write_receipt.byte_count}")
    print(f"flush_calls: {writer.flush_calls}")
    print(f"state: {gate.state}")


if __name__ == "__main__":
    main()
