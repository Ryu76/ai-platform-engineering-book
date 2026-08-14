"""Volume 03 MCP STDIO bounded input queue를 process·worker 없이 검증한다."""

from __future__ import annotations

import pytest

from ai_platform.mcp.input_queue import (
    McpStdioInputQueue,
    McpStdioInputQueueError,
    McpStdioInputQueueState,
    McpStdioInputWorkerOutcome,
)
from ai_platform.mcp.input_write import McpStdioInputFrame, build_mcp_stdio_input_frame


def _frame(request_id: str) -> McpStdioInputFrame:
    return build_mcp_stdio_input_frame({"jsonrpc": "2.0", "id": request_id, "method": "safe/test"})


def test_fifo_admission_is_bounded_and_has_no_writer_or_process_seam() -> None:
    queue = McpStdioInputQueue(max_pending_frames=2)
    first = queue.offer("first", _frame("first"))
    second = queue.offer("second", _frame("second"))

    with pytest.raises(McpStdioInputQueueError, match="queue is full") as error:
        queue.offer("third", _frame("third"))

    assert error.value.correlation_id == "mcp-stdio:string:third"
    assert queue.pending_count == 2
    assert queue.claim_next() is first
    assert queue.pending_count == 1

    with pytest.raises(McpStdioInputQueueError, match="already owns"):
        queue.claim_next()

    resolution = queue.resolve(first, McpStdioInputWorkerOutcome.DELIVERED)
    assert resolution.correlation_id == "mcp-stdio:string:first"
    assert resolution.outcome is McpStdioInputWorkerOutcome.DELIVERED
    assert resolution.child_shutdown_requested is False
    assert queue.claim_next() is second


def test_cancel_removes_only_pending_typed_id_and_latches_future_admission() -> None:
    queue = McpStdioInputQueue()
    queue.offer("7", _frame("seven-string"))
    integer_item = queue.offer(7, _frame("seven-integer"))

    assert queue.cancel("7") is True
    assert queue.pending_count == 1
    assert queue.claim_next() is integer_item

    with pytest.raises(McpStdioInputQueueError, match="cancelled") as error:
        queue.offer("7", _frame("new-seven-string"))
    assert error.value.correlation_id == "mcp-stdio:string:7"


def test_cancelled_in_flight_frame_is_not_interrupted_or_requeued() -> None:
    queue = McpStdioInputQueue()
    queued = queue.offer("in-flight", _frame("in-flight"))
    claimed = queue.claim_next()
    assert claimed is queued

    assert queue.cancel("in-flight") is False
    resolution = queue.resolve(claimed, McpStdioInputWorkerOutcome.NOT_DELIVERED)

    assert resolution.outcome is McpStdioInputWorkerOutcome.NOT_DELIVERED
    assert queue.pending_count == 0
    with pytest.raises(McpStdioInputQueueError, match="cancelled"):
        queue.offer("in-flight", _frame("in-flight"))


def test_disconnect_discards_pending_and_blocks_admission_and_claim_without_shutdown_signal() -> (
    None
):
    queue = McpStdioInputQueue()
    queue.offer("pending", _frame("pending"))

    queue.disconnect()

    assert queue.state is McpStdioInputQueueState.DISCONNECTED
    assert queue.pending_count == 0
    with pytest.raises(McpStdioInputQueueError, match="disconnected") as offered:
        queue.offer("after-disconnect", _frame("after-disconnect"))
    assert offered.value.child_shutdown_requested is False
    with pytest.raises(McpStdioInputQueueError, match="disconnected"):
        queue.claim_next()


def test_ambiguous_worker_result_discards_pending_requests_and_requests_caller_shutdown() -> None:
    queue = McpStdioInputQueue()
    claimed = queue.offer("ambiguous", _frame("ambiguous"))
    queue.offer("must-drop", _frame("must-drop"))
    assert queue.claim_next() is claimed

    resolution = queue.resolve(claimed, McpStdioInputWorkerOutcome.AMBIGUOUS)

    assert resolution.correlation_id == "mcp-stdio:string:ambiguous"
    assert resolution.child_shutdown_requested is True
    assert queue.state is McpStdioInputQueueState.SHUTDOWN_REQUIRED
    assert queue.pending_count == 0
    with pytest.raises(McpStdioInputQueueError, match="shutdown") as blocked:
        queue.offer("blocked", _frame("blocked"))
    assert blocked.value.child_shutdown_requested is True


def test_worker_result_must_match_exact_claimed_object_and_valid_outcome_before_mutation() -> None:
    queue = McpStdioInputQueue()
    claimed = queue.offer("claimed", _frame("claimed"))
    queue.claim_next()
    forged_equal_value = type(claimed)(correlation_id=claimed.correlation_id, frame=claimed.frame)

    with pytest.raises(McpStdioInputQueueError, match="does not match"):
        queue.resolve(forged_equal_value, McpStdioInputWorkerOutcome.DELIVERED)
    with pytest.raises(McpStdioInputQueueError, match="outcome is invalid"):
        queue.resolve(claimed, "delivered")  # type: ignore[arg-type]

    assert queue.resolve(claimed, McpStdioInputWorkerOutcome.DELIVERED).outcome is (
        McpStdioInputWorkerOutcome.DELIVERED
    )


@pytest.mark.parametrize("capacity", (0, 129, True, "2"))
def test_invalid_capacity_is_rejected_before_queue_creation(capacity: object) -> None:
    with pytest.raises(McpStdioInputQueueError, match="capacity is invalid"):
        McpStdioInputQueue(max_pending_frames=capacity)  # type: ignore[arg-type]


def test_invalid_request_or_frame_is_rejected_without_pending_mutation() -> None:
    queue = McpStdioInputQueue()

    with pytest.raises(McpStdioInputQueueError, match="request id is invalid"):
        queue.offer(True, _frame("valid"))  # type: ignore[arg-type]
    with pytest.raises(McpStdioInputQueueError, match="frame is invalid"):
        queue.offer("valid", object())  # type: ignore[arg-type]

    assert queue.pending_count == 0
    assert queue.state is McpStdioInputQueueState.OPEN
