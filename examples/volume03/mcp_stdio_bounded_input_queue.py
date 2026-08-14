"""MCP STDIO stdin bounded queue와 fake worker result policy를 offline으로 보인다."""

from __future__ import annotations

from ai_platform.mcp.input_queue import McpStdioInputQueue, McpStdioInputWorkerOutcome
from ai_platform.mcp.input_write import build_mcp_stdio_input_frame


def main() -> None:
    """고정 frame을 queue에 넣고 fake delivered outcome만 기록하며 실제 I/O는 하지 않는다."""
    queue = McpStdioInputQueue(max_pending_frames=2)
    queue.offer(
        "queue-demo-001",
        build_mcp_stdio_input_frame(
            {"jsonrpc": "2.0", "id": "queue-demo-001", "method": "safe/test"}
        ),
    )
    queue.offer(
        "queue-demo-002",
        build_mcp_stdio_input_frame(
            {"jsonrpc": "2.0", "id": "queue-demo-002", "method": "safe/test"}
        ),
    )
    item = queue.claim_next()
    assert item is not None
    resolution = queue.resolve(item, McpStdioInputWorkerOutcome.DELIVERED)

    print(f"correlation_id: {resolution.correlation_id}")
    print(f"outcome: {resolution.outcome}")
    print(f"pending_frames: {queue.pending_count}")
    print(f"state: {queue.state}")


if __name__ == "__main__":
    main()
