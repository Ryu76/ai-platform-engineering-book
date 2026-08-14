"""MCP STDIO claimed queue item을 memory-only delivery owner에 한 번 전달한다."""

from __future__ import annotations

from ai_platform.mcp.input_delivery import McpStdioInputDeliveryReceipt
from ai_platform.mcp.input_queue import McpStdioInputQueue
from ai_platform.mcp.input_write import (
    McpStdioInputFrame,
    McpStdioInputWriteReceipt,
    build_mcp_stdio_input_frame,
)
from ai_platform.mcp.queued_delivery import deliver_next_mcp_stdio_queued_input


class OfflineDeliveryOwner:
    """실제 worker·Popen·pipe 없이 local delivery receipt만 반환한다."""

    def __init__(self) -> None:
        self.write_calls = 0

    def write(
        self, request_id: str | int, frame: McpStdioInputFrame
    ) -> McpStdioInputDeliveryReceipt:
        self.write_calls += 1
        return McpStdioInputDeliveryReceipt(
            correlation_id=request_id,
            write_receipt=McpStdioInputWriteReceipt(byte_count=frame.byte_count, write_calls=1),
        )


def main() -> None:
    """allowlisted-looking fixed frame만 queue와 fake delivery seam에서 처리한다."""
    queue = McpStdioInputQueue()
    frame = build_mcp_stdio_input_frame(
        {"jsonrpc": "2.0", "id": "queued-delivery-demo-001", "method": "safe/test"}
    )
    queue.offer("queued-delivery-demo-001", frame)
    owner = OfflineDeliveryOwner()
    result = deliver_next_mcp_stdio_queued_input(queue, owner)
    assert result is not None

    print(f"correlation_id: {result.resolution.correlation_id}")
    print(f"outcome: {result.resolution.outcome}")
    print(f"write_calls: {owner.write_calls}")
    print(f"state: {queue.state}")


if __name__ == "__main__":
    main()
