"""Volume 03 claimed input queue delivery adapter를 real worker·process 없이 검증한다."""

from __future__ import annotations

import pytest

from ai_platform.mcp.input_delivery import McpStdioInputDeliveryError, McpStdioInputDeliveryReceipt
from ai_platform.mcp.input_queue import (
    McpStdioInputQueue,
    McpStdioInputQueueError,
    McpStdioInputQueueState,
    McpStdioInputWorkerOutcome,
)
from ai_platform.mcp.input_write import (
    McpStdioInputFrame,
    McpStdioInputWriteReceipt,
    build_mcp_stdio_input_frame,
)
from ai_platform.mcp.queued_delivery import (
    McpStdioQueuedDeliveryError,
    deliver_next_mcp_stdio_queued_input,
)


class _OfflineDeliveryOwner:
    """실제 Popen·pipe 없이 planned result와 call만 기록하는 delivery seam이다."""

    def __init__(
        self, results: list[object], *, disconnect_queue: McpStdioInputQueue | None = None
    ) -> None:
        self._results = results
        self._disconnect_queue = disconnect_queue
        self.calls: list[tuple[str | int, McpStdioInputFrame]] = []

    def write(
        self, request_id: str | int, frame: McpStdioInputFrame
    ) -> McpStdioInputDeliveryReceipt:
        self.calls.append((request_id, frame))
        if self._disconnect_queue is not None:
            self._disconnect_queue.disconnect()
        result = self._results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result  # type: ignore[return-value]


def _frame(request_id: str) -> McpStdioInputFrame:
    return build_mcp_stdio_input_frame({"jsonrpc": "2.0", "id": request_id, "method": "safe/test"})


def _receipt(request_id: str, frame: McpStdioInputFrame) -> McpStdioInputDeliveryReceipt:
    return McpStdioInputDeliveryReceipt(
        correlation_id=f"mcp-stdio:string:{request_id}",
        write_receipt=McpStdioInputWriteReceipt(byte_count=frame.byte_count, write_calls=1),
    )


def test_claimed_frame_is_delivered_once_then_resolved_and_next_item_stays_pending() -> None:
    queue = McpStdioInputQueue()
    first = _frame("first")
    second = _frame("second")
    queue.offer("first", first)
    queue.offer("second", second)
    owner = _OfflineDeliveryOwner([_receipt("first", first)])

    result = deliver_next_mcp_stdio_queued_input(queue, owner)

    assert result is not None
    assert result.resolution.outcome is McpStdioInputWorkerOutcome.DELIVERED
    assert result.resolution.child_shutdown_requested is False
    assert owner.calls == [("mcp-stdio:string:first", first)]
    assert queue.pending_count == 1
    assert queue.state is McpStdioInputQueueState.OPEN


def test_empty_open_queue_never_calls_owner() -> None:
    queue = McpStdioInputQueue()
    owner = _OfflineDeliveryOwner([])

    assert deliver_next_mcp_stdio_queued_input(queue, owner) is None
    assert owner.calls == []


@pytest.mark.parametrize(
    "error",
    (
        McpStdioInputDeliveryError(
            "MCP STDIO input delivery was cancelled",
            correlation_id="mcp-stdio:string:cancelled",
            frame_may_be_partial=False,
            child_shutdown_requested=False,
        ),
        McpStdioInputDeliveryError(
            "MCP STDIO input delivery is disconnected",
            correlation_id="mcp-stdio:string:closed",
            frame_may_be_partial=False,
            child_shutdown_requested=False,
        ),
    ),
)
def test_typed_non_partial_delivery_failure_maps_to_not_delivered(error: BaseException) -> None:
    queue = McpStdioInputQueue()
    frame = _frame("not-delivered")
    queue.offer("not-delivered", frame)
    owner = _OfflineDeliveryOwner([error])

    result = deliver_next_mcp_stdio_queued_input(queue, owner)

    assert result is not None
    assert result.resolution.outcome is McpStdioInputWorkerOutcome.NOT_DELIVERED
    assert result.resolution.child_shutdown_requested is False
    assert queue.state is McpStdioInputQueueState.OPEN
    assert queue.pending_count == 0


@pytest.mark.parametrize(
    "result",
    (
        McpStdioInputDeliveryError(
            "MCP STDIO input delivery became ambiguous",
            correlation_id="mcp-stdio:string:partial",
            frame_may_be_partial=True,
            child_shutdown_requested=True,
        ),
        OSError("untrusted adapter detail"),
        object(),
    ),
)
def test_partial_unknown_or_malformed_delivery_result_latches_ambiguous_shutdown(
    result: object,
) -> None:
    queue = McpStdioInputQueue()
    frame = _frame("ambiguous")
    queue.offer("ambiguous", frame)
    queue.offer("must-drop", _frame("must-drop"))
    owner = _OfflineDeliveryOwner([result])

    delivered = deliver_next_mcp_stdio_queued_input(queue, owner)

    assert delivered is not None
    assert delivered.resolution.outcome is McpStdioInputWorkerOutcome.AMBIGUOUS
    assert delivered.resolution.child_shutdown_requested is True
    assert queue.state is McpStdioInputQueueState.SHUTDOWN_REQUIRED
    assert queue.pending_count == 0


def test_disconnect_after_claim_does_not_interrupt_in_flight_delivery_but_blocks_future_claim() -> (
    None
):
    queue = McpStdioInputQueue()
    frame = _frame("in-flight")
    queue.offer("in-flight", frame)
    queue.offer("discard-me", _frame("discard-me"))
    owner = _OfflineDeliveryOwner([_receipt("in-flight", frame)], disconnect_queue=queue)

    result = deliver_next_mcp_stdio_queued_input(queue, owner)

    assert result is not None
    assert result.resolution.outcome is McpStdioInputWorkerOutcome.DELIVERED
    assert queue.state is McpStdioInputQueueState.DISCONNECTED
    assert queue.pending_count == 0
    with pytest.raises(McpStdioInputQueueError, match="disconnected"):
        deliver_next_mcp_stdio_queued_input(queue, owner)


def test_invalid_delivery_owner_is_rejected_before_claim_or_delivery() -> None:
    queue = McpStdioInputQueue()
    frame = _frame("pending")
    queue.offer("pending", frame)

    with pytest.raises(McpStdioQueuedDeliveryError, match="owner is invalid"):
        deliver_next_mcp_stdio_queued_input(queue, object())  # type: ignore[arg-type]

    assert queue.pending_count == 1
    assert queue.claim_next() is not None


def test_mismatched_success_receipt_is_ambiguous_without_reflecting_adapter_detail() -> None:
    queue = McpStdioInputQueue()
    frame = _frame("receipt")
    queue.offer("receipt", frame)
    owner = _OfflineDeliveryOwner(
        [
            McpStdioInputDeliveryReceipt(
                correlation_id="mcp-stdio:string:other",
                write_receipt=McpStdioInputWriteReceipt(byte_count=1, write_calls=0),
            )
        ]
    )

    result = deliver_next_mcp_stdio_queued_input(queue, owner)

    assert result is not None
    assert result.resolution.outcome is McpStdioInputWorkerOutcome.AMBIGUOUS
    assert result.resolution.child_shutdown_requested is True
