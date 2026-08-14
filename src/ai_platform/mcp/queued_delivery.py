"""Claimed MCP STDIO input queue item을 host-owned delivery seam에 한 번 전달한다.

이 module은 worker/thread/event loop/Popen/pipe를 만들거나 child를 signal·close·restart하지 않는다.
이미 claim된 immutable frame 하나를 injected delivery owner에 넘기고 raw adapter detail 없이
queue의 보수적 outcome으로만 resolve한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ai_platform.mcp.input_delivery import McpStdioInputDeliveryError, McpStdioInputDeliveryReceipt
from ai_platform.mcp.input_queue import (
    McpStdioInputQueue,
    McpStdioInputQueueResolution,
    McpStdioInputWorkerOutcome,
)
from ai_platform.mcp.input_write import McpStdioInputFrame


class McpStdioQueuedDeliveryError(ValueError):
    """delivery seam이 claim 전에 유효하지 않아 queue를 변경하지 않았음을 나타낸다."""


@runtime_checkable
class McpStdioQueuedInputDeliveryOwner(Protocol):
    """한 claimed frame을 host-owned stdin delivery boundary로 전달하는 최소 seam이다."""

    def write(
        self, request_id: str | int, frame: McpStdioInputFrame
    ) -> McpStdioInputDeliveryReceipt:
        """local bounded delivery receipt을 반환하거나 typed delivery failure를 보고한다."""


@dataclass(frozen=True, slots=True)
class McpStdioQueuedDeliveryResult:
    """한 claimed item의 detail-free terminal resolution이다."""

    resolution: McpStdioInputQueueResolution


def deliver_next_mcp_stdio_queued_input(
    queue: McpStdioInputQueue, owner: McpStdioQueuedInputDeliveryOwner
) -> McpStdioQueuedDeliveryResult | None:
    """다음 FIFO item 하나를 delivery owner에 한 번만 넘긴 후 보수적으로 resolve한다.

    ``None``은 open queue에 pending item이 없었음을 뜻한다. injected owner의 typed non-partial
    failure는 ``NOT_DELIVERED``로, partial 또는 알 수 없는 failure와 malformed success receipt은
    ``AMBIGUOUS``로 map한다. 후자는 queue의 caller-owned shutdown signal을 latches한다.
    ``disconnect()``가 in-flight claim 뒤 호출되어도 이미 해당 claim의 owner가 정해졌으므로
    이 function은 interrupt하지 않으며, delivery result를 정확히 한 번 resolve한다.
    """
    if not isinstance(queue, McpStdioInputQueue):
        raise McpStdioQueuedDeliveryError("MCP STDIO queued delivery queue is invalid")
    if not isinstance(owner, McpStdioQueuedInputDeliveryOwner):
        raise McpStdioQueuedDeliveryError("MCP STDIO queued delivery owner is invalid")

    item = queue.claim_next()
    if item is None:
        return None

    outcome = _deliver_claimed_item(owner, item.correlation_id, item.frame)
    return McpStdioQueuedDeliveryResult(resolution=queue.resolve(item, outcome))


def _deliver_claimed_item(
    owner: McpStdioQueuedInputDeliveryOwner, correlation_id: str, frame: McpStdioInputFrame
) -> McpStdioInputWorkerOutcome:
    """delivery adapter detail을 raw exception 없이 conservative worker outcome으로 축소한다."""
    try:
        receipt = owner.write(correlation_id, frame)
    except McpStdioInputDeliveryError as error:
        if error.frame_may_be_partial:
            return McpStdioInputWorkerOutcome.AMBIGUOUS
        return McpStdioInputWorkerOutcome.NOT_DELIVERED
    except Exception:
        return McpStdioInputWorkerOutcome.AMBIGUOUS

    if not _is_matching_receipt(receipt, correlation_id, frame):
        return McpStdioInputWorkerOutcome.AMBIGUOUS
    return McpStdioInputWorkerOutcome.DELIVERED


def _is_matching_receipt(receipt: object, correlation_id: str, frame: McpStdioInputFrame) -> bool:
    """malformed local success report도 receiver state가 불명확하므로 ambiguity로 취급한다."""
    return (
        isinstance(receipt, McpStdioInputDeliveryReceipt)
        and receipt.correlation_id == correlation_id
        and receipt.write_receipt.byte_count == frame.byte_count
        and receipt.write_receipt.write_calls >= 1
    )
