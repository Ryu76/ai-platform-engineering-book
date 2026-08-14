"""MCP STDIO stdin delivery의 cancellation·disconnect·partial-frame 정책 경계.

이 module은 Popen, pipe, child shutdown, retry, durable idempotency 또는 network를 소유하지 않는다.
신뢰된 host가 typed JSON-RPC ID와 injected writer를 제공하면 새 frame을 쓸 수 있는 상태만 좁게
확인한다. write 중 partial delivery 가능성이 발생하면 host가 child shutdown을 검토해야 한다는
상태만 남기고 이후 frame을 막는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_platform.mcp.input_write import (
    McpStdioInputFrame,
    McpStdioInputWriteError,
    McpStdioInputWriteReceipt,
    McpStdioWritableBinaryStream,
    write_mcp_stdio_input_frame,
)
from ai_platform.mcp.stdio import McpStdioError, mcp_stdio_request_correlation_id


class McpStdioInputDeliveryState(StrEnum):
    """한 host-owned stdin writer의 새 frame 전송 가능 상태다."""

    OPEN = "open"
    DISCONNECTED = "disconnected"
    SHUTDOWN_REQUIRED = "shutdown_required"


class McpStdioInputDeliveryError(ValueError):
    """delivery policy가 writer 호출 전 또는 후에 안전하게 중단됐음을 나타낸다.

    ``frame_may_be_partial``은 해당 호출의 receiver가 frame prefix 또는 complete frame을 받았을 수
    있음을 뜻한다. ``child_shutdown_requested``는 이 module이 child를 종료했다는 뜻이 아니라,
    host가 별도의 shutdown ownership 경계에서 검토해야 한다는 explicit signal이다.
    """

    def __init__(
        self,
        message: str,
        *,
        correlation_id: str | None,
        frame_may_be_partial: bool,
        child_shutdown_requested: bool,
    ) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id
        self.frame_may_be_partial = frame_may_be_partial
        self.child_shutdown_requested = child_shutdown_requested


@dataclass(frozen=True, slots=True)
class McpStdioInputDeliveryReceipt:
    """local writer flush success를 typed request ID에 결속한 record이며 peer receipt은 아니다."""

    correlation_id: str
    write_receipt: McpStdioInputWriteReceipt


class McpStdioInputDeliveryGate:
    """취소·연결 해제·partial frame ambiguity를 새 stdin write와 분리하는 host-owned gate다."""

    def __init__(self) -> None:
        self._state = McpStdioInputDeliveryState.OPEN
        self._cancelled_correlation_ids: set[str] = set()

    @property
    def state(self) -> McpStdioInputDeliveryState:
        """현재 writer에서 새 frame을 보낼 수 있는지 반환한다."""
        return self._state

    def cancel(self, request_id: str | int) -> None:
        """같은 typed JSON-RPC ID의 아직 시작하지 않은 전송만 차단한다."""
        correlation_id = _correlation_id_or_raise(request_id)
        self._cancelled_correlation_ids.add(correlation_id)

    def disconnect(self) -> None:
        """명시적 disconnect 뒤 새 frame 전송을 막는다; pipe나 child는 직접 건드리지 않는다."""
        if self._state is McpStdioInputDeliveryState.OPEN:
            self._state = McpStdioInputDeliveryState.DISCONNECTED

    def write(
        self,
        request_id: str | int,
        stream: McpStdioWritableBinaryStream,
        frame: McpStdioInputFrame,
    ) -> McpStdioInputDeliveryReceipt:
        """open·not-cancelled typed ID의 immutable frame만 기존 bounded writer로 넘긴다.

        writer가 partial-frame 가능성을 알리면 blind retry하지 않고 gate를
        ``SHUTDOWN_REQUIRED``로 전환한다. child 종료와 durable idempotency 판단은 caller가 소유한다.
        """
        correlation_id = _correlation_id_or_raise(request_id)
        self._reject_unavailable_state(correlation_id)
        if correlation_id in self._cancelled_correlation_ids:
            raise McpStdioInputDeliveryError(
                "MCP STDIO input delivery was cancelled",
                correlation_id=correlation_id,
                frame_may_be_partial=False,
                child_shutdown_requested=False,
            )
        try:
            write_receipt = write_mcp_stdio_input_frame(stream, frame)
        except McpStdioInputWriteError as error:
            if error.frame_may_be_partial:
                self._state = McpStdioInputDeliveryState.SHUTDOWN_REQUIRED
                raise McpStdioInputDeliveryError(
                    "MCP STDIO input delivery became ambiguous",
                    correlation_id=correlation_id,
                    frame_may_be_partial=True,
                    child_shutdown_requested=True,
                ) from None
            raise McpStdioInputDeliveryError(
                "MCP STDIO input delivery is invalid",
                correlation_id=correlation_id,
                frame_may_be_partial=False,
                child_shutdown_requested=False,
            ) from None
        return McpStdioInputDeliveryReceipt(
            correlation_id=correlation_id,
            write_receipt=write_receipt,
        )

    def _reject_unavailable_state(self, correlation_id: str) -> None:
        if self._state is McpStdioInputDeliveryState.DISCONNECTED:
            raise McpStdioInputDeliveryError(
                "MCP STDIO input delivery is disconnected",
                correlation_id=correlation_id,
                frame_may_be_partial=False,
                child_shutdown_requested=False,
            )
        if self._state is McpStdioInputDeliveryState.SHUTDOWN_REQUIRED:
            raise McpStdioInputDeliveryError(
                "MCP STDIO input delivery requires child shutdown",
                correlation_id=correlation_id,
                frame_may_be_partial=False,
                child_shutdown_requested=True,
            )


def _correlation_id_or_raise(request_id: object) -> str:
    """typed JSON-RPC ID 오류를 writer 전에 generic delivery 오류로 바꾼다."""
    try:
        return mcp_stdio_request_correlation_id(request_id)  # type: ignore[arg-type]
    except McpStdioError:
        raise McpStdioInputDeliveryError(
            "MCP STDIO input delivery request id is invalid",
            correlation_id=None,
            frame_may_be_partial=False,
            child_shutdown_requested=False,
        ) from None
