"""MCP STDIO stdin의 bounded queue admission과 worker-result policy를 분리한다.

이 module은 worker, thread, event loop, Popen, pipe, 실제 write, retry 또는 child shutdown을
소유하지 않는다. host가 immutable frame을 queue에 넣고 한 worker가 claim한 뒤 typed outcome만
되돌려 주면, overload·disconnect·partial-frame ambiguity에서 다음 frame을 안전하게 막는다.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum

from ai_platform.mcp.input_write import McpStdioInputFrame
from ai_platform.mcp.stdio import McpStdioError, mcp_stdio_request_correlation_id

_MAX_PENDING_FRAMES = 128


class McpStdioInputQueueState(StrEnum):
    """새 frame admission과 claimed worker 결과를 처리할 수 있는 queue state다."""

    OPEN = "open"
    DISCONNECTED = "disconnected"
    SHUTDOWN_REQUIRED = "shutdown_required"


class McpStdioInputWorkerOutcome(StrEnum):
    """worker가 raw adapter detail 없이 반환하는 한 frame의 delivery outcome이다."""

    DELIVERED = "delivered"
    NOT_DELIVERED = "not_delivered"
    AMBIGUOUS = "ambiguous"


class McpStdioInputQueueError(ValueError):
    """queue policy가 I/O 없이 admission 또는 state transition을 거부했음을 나타낸다."""

    def __init__(
        self,
        message: str,
        *,
        correlation_id: str | None,
        child_shutdown_requested: bool,
    ) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id
        self.child_shutdown_requested = child_shutdown_requested


@dataclass(frozen=True, slots=True)
class McpStdioQueuedInput:
    """한 worker만 claim할 수 있는 typed correlation과 immutable frame snapshot이다."""

    correlation_id: str
    frame: McpStdioInputFrame


@dataclass(frozen=True, slots=True)
class McpStdioInputQueueResolution:
    """raw writer receipt가 아닌 queue policy의 terminal worker-result record다."""

    correlation_id: str
    outcome: McpStdioInputWorkerOutcome
    child_shutdown_requested: bool


class McpStdioInputQueue:
    """single-worker bounded admission과 disconnect/ambiguity latch를 제공하는 host-owned queue다.

    ``max_pending_frames``는 worker가 아직 claim하지 않은 frame 수의 upper bound다. claim한
    in-flight frame은 worker가 별도 ownership으로 처리하므로 pending budget에 포함하지 않는다.
    ``cancel``과 ``disconnect``는 running worker를 interrupt하지 않으며, worker는 claim한 item의
    outcome을 정확히 한 번 ``resolve``해야 한다.
    """

    def __init__(self, *, max_pending_frames: int = 16) -> None:
        if (
            isinstance(max_pending_frames, bool)
            or not isinstance(max_pending_frames, int)
            or not 1 <= max_pending_frames <= _MAX_PENDING_FRAMES
        ):
            raise McpStdioInputQueueError(
                "MCP STDIO input queue capacity is invalid",
                correlation_id=None,
                child_shutdown_requested=False,
            )
        self._max_pending_frames = max_pending_frames
        self._state = McpStdioInputQueueState.OPEN
        self._pending: deque[McpStdioQueuedInput] = deque()
        self._pending_correlation_ids: set[str] = set()
        self._cancelled_correlation_ids: set[str] = set()
        self._in_flight: McpStdioQueuedInput | None = None

    @property
    def state(self) -> McpStdioInputQueueState:
        """새 frame admission 상태를 반환한다."""
        return self._state

    @property
    def pending_count(self) -> int:
        """worker가 아직 claim하지 않은 frame 수를 반환한다."""
        return len(self._pending)

    def offer(self, request_id: str | int, frame: McpStdioInputFrame) -> McpStdioQueuedInput:
        """open queue에 immutable frame 하나를 FIFO pending record로 넣는다; writer I/O는 없다."""
        correlation_id = _correlation_id_or_raise(request_id)
        if not isinstance(frame, McpStdioInputFrame):
            raise McpStdioInputQueueError(
                "MCP STDIO input queue frame is invalid",
                correlation_id=correlation_id,
                child_shutdown_requested=False,
            )
        self._reject_unavailable_state(correlation_id)
        if correlation_id in self._cancelled_correlation_ids:
            raise McpStdioInputQueueError(
                "MCP STDIO input queue delivery was cancelled",
                correlation_id=correlation_id,
                child_shutdown_requested=False,
            )
        if correlation_id in self._pending_correlation_ids or (
            self._in_flight is not None and self._in_flight.correlation_id == correlation_id
        ):
            raise McpStdioInputQueueError(
                "MCP STDIO input queue request is already unsettled",
                correlation_id=correlation_id,
                child_shutdown_requested=False,
            )
        if len(self._pending) >= self._max_pending_frames:
            raise McpStdioInputQueueError(
                "MCP STDIO input queue is full",
                correlation_id=correlation_id,
                child_shutdown_requested=False,
            )
        item = McpStdioQueuedInput(correlation_id=correlation_id, frame=frame)
        self._pending.append(item)
        self._pending_correlation_ids.add(correlation_id)
        return item

    def cancel(self, request_id: str | int) -> bool:
        """아직 claim되지 않은 typed request를 제거하고 이후 같은 ID의 admission을 막는다."""
        correlation_id = _correlation_id_or_raise(request_id)
        self._cancelled_correlation_ids.add(correlation_id)
        if correlation_id not in self._pending_correlation_ids:
            return False
        self._pending = deque(
            item for item in self._pending if item.correlation_id != correlation_id
        )
        self._pending_correlation_ids.remove(correlation_id)
        return True

    def disconnect(self) -> None:
        """pending frame을 버리고 새 admission/claim을 막는다.

        In-flight worker는 직접 중단하지 않는다.
        """
        if self._state is McpStdioInputQueueState.OPEN:
            self._state = McpStdioInputQueueState.DISCONNECTED
            self._pending.clear()
            self._pending_correlation_ids.clear()

    def claim_next(self) -> McpStdioQueuedInput | None:
        """open queue의 다음 FIFO frame을 단일 worker에 넘긴다; I/O나 worker 생성은 하지 않는다."""
        self._reject_unavailable_state(None)
        if self._in_flight is not None:
            raise McpStdioInputQueueError(
                "MCP STDIO input queue worker already owns a frame",
                correlation_id=self._in_flight.correlation_id,
                child_shutdown_requested=False,
            )
        if not self._pending:
            return None
        item = self._pending.popleft()
        self._pending_correlation_ids.remove(item.correlation_id)
        self._in_flight = item
        return item

    def resolve(
        self, item: McpStdioQueuedInput, outcome: McpStdioInputWorkerOutcome
    ) -> McpStdioInputQueueResolution:
        """claim한 exact item의 worker outcome을 한 번 기록한다.

        Ambiguity만 shutdown-required state로 승격한다.
        """
        if not isinstance(item, McpStdioQueuedInput) or item is not self._in_flight:
            raise McpStdioInputQueueError(
                "MCP STDIO input queue worker result does not match in-flight frame",
                correlation_id=None,
                child_shutdown_requested=False,
            )
        if not isinstance(outcome, McpStdioInputWorkerOutcome):
            raise McpStdioInputQueueError(
                "MCP STDIO input queue worker outcome is invalid",
                correlation_id=item.correlation_id,
                child_shutdown_requested=False,
            )
        self._in_flight = None
        if outcome is McpStdioInputWorkerOutcome.AMBIGUOUS:
            self._state = McpStdioInputQueueState.SHUTDOWN_REQUIRED
            self._pending.clear()
            self._pending_correlation_ids.clear()
            return McpStdioInputQueueResolution(
                correlation_id=item.correlation_id,
                outcome=outcome,
                child_shutdown_requested=True,
            )
        return McpStdioInputQueueResolution(
            correlation_id=item.correlation_id,
            outcome=outcome,
            child_shutdown_requested=False,
        )

    def _reject_unavailable_state(self, correlation_id: str | None) -> None:
        if self._state is McpStdioInputQueueState.DISCONNECTED:
            raise McpStdioInputQueueError(
                "MCP STDIO input queue is disconnected",
                correlation_id=correlation_id,
                child_shutdown_requested=False,
            )
        if self._state is McpStdioInputQueueState.SHUTDOWN_REQUIRED:
            raise McpStdioInputQueueError(
                "MCP STDIO input queue requires child shutdown",
                correlation_id=correlation_id,
                child_shutdown_requested=True,
            )


def _correlation_id_or_raise(request_id: object) -> str:
    """invalid typed ID를 queue mutation 전에 generic error로 바꾼다."""
    try:
        return mcp_stdio_request_correlation_id(request_id)  # type: ignore[arg-type]
    except McpStdioError:
        raise McpStdioInputQueueError(
            "MCP STDIO input queue request id is invalid",
            correlation_id=None,
            child_shutdown_requested=False,
        ) from None
