"""MCP STDIO child stdin의 Popen ownership을 bounded delivery gate에 좁게 연결한다.

이 module은 trusted host가 이미 시작한 Popen-like child의 stdin handle을 한 번 snapshot하여
MCP frame delivery에만 사용한다. Popen start, stdout/stderr drain, pipe close, child shutdown,
thread/event loop, non-blocking I/O와 retry는 소유하지 않는다.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ai_platform.mcp.input_delivery import (
    McpStdioInputDeliveryError,
    McpStdioInputDeliveryGate,
    McpStdioInputDeliveryReceipt,
    McpStdioInputDeliveryState,
)
from ai_platform.mcp.input_write import McpStdioInputFrame, McpStdioWritableBinaryStream
from ai_platform.mcp.stdio import McpStdioError, mcp_stdio_request_correlation_id


class McpStdioPopenInputError(ValueError):
    """Popen stdin binding 전·liveness 확인 중 writer I/O 없이 중단된 오류다."""

    def __init__(self, message: str, *, correlation_id: str | None) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id
        self.frame_may_be_partial = False
        self.child_shutdown_requested = False


@runtime_checkable
class McpStdioPopenStdinProcess(Protocol):
    """Popen process에서 stdin ownership에 필요한 최소 binary seam이다."""

    @property
    def stdin(self) -> McpStdioWritableBinaryStream | None:
        """``stdin=PIPE``로 얻은 binary writable handle 또는 unavailable 상태를 반환한다."""

    def poll(self) -> int | None:
        """child가 실행 중이면 ``None``, 종료했으면 integer exit code를 반환한다."""


class McpStdioPopenInputOwner:
    """한 live Popen stdin snapshot만 delivery gate에 연결하는 host-owned adapter다.

    Construction 뒤 ``process.stdin``을 다시 읽지 않는다. 이것은 host 내부의 single-owner
    convention이며, 다른 code가 raw Popen handle을 별도로 사용하는 것을 OS 차원에서 막지는 않는다.
    Synchronous ``write``는 OS pipe backpressure로 block할 수 있다. 이 adapter는 4 KiB bounded
    write contract를 재사용할 뿐 selector, worker, timeout 또는 cancellation interrupt를
    제공하지 않는다.
    """

    def __init__(self, process: McpStdioPopenStdinProcess) -> None:
        if not isinstance(process, McpStdioPopenStdinProcess):
            raise McpStdioPopenInputError("MCP STDIO Popen process is invalid", correlation_id=None)
        try:
            stdin = process.stdin
        except Exception:
            raise McpStdioPopenInputError(
                "MCP STDIO Popen stdin is unavailable", correlation_id=None
            ) from None
        if not isinstance(stdin, McpStdioWritableBinaryStream):
            raise McpStdioPopenInputError(
                "MCP STDIO Popen stdin is unavailable", correlation_id=None
            )
        self._process = process
        self._stdin = stdin
        self._delivery_gate = McpStdioInputDeliveryGate()

    @property
    def state(self) -> McpStdioInputDeliveryState:
        """captured stdin에서 새 frame을 보낼 수 있는 delivery state를 반환한다."""
        return self._delivery_gate.state

    def cancel(self, request_id: str | int) -> None:
        """아직 시작하지 않은 typed request frame만 차단한다; Popen을 signal/close하지 않는다."""
        self._delivery_gate.cancel(request_id)

    def disconnect(self) -> None:
        """새 frame을 막되 Popen stdin close나 child shutdown은 caller ownership으로 남긴다."""
        self._delivery_gate.disconnect()

    def write(
        self, request_id: str | int, frame: McpStdioInputFrame
    ) -> McpStdioInputDeliveryReceipt:
        """live child의 captured stdin에 한 frame을 전달한다.

        cancelled/disconnected/shutdown-required state는 ``poll``과 writer I/O 전에 existing gate가
        거부한다. live check 뒤 write/flush가 partial delivery를 보고하면 gate가 caller-owned child
        shutdown signal과 ``SHUTDOWN_REQUIRED`` state를 만든다.
        """
        correlation_id = _correlation_id_or_raise(request_id)
        if self.state is not McpStdioInputDeliveryState.OPEN:
            return self._delivery_gate.write(request_id, self._stdin, frame)
        if self._delivery_gate.is_cancelled(request_id):
            return self._delivery_gate.write(request_id, self._stdin, frame)

        exit_code = self._read_exit_code(correlation_id)
        if exit_code is not None:
            self._delivery_gate.disconnect()
            raise McpStdioPopenInputError(
                "MCP STDIO child stdin is unavailable", correlation_id=correlation_id
            )
        try:
            return self._delivery_gate.write(request_id, self._stdin, frame)
        except McpStdioInputDeliveryError:
            raise

    def _read_exit_code(self, correlation_id: str) -> int | None:
        """poll adapter detail과 malformed status를 writer보다 먼저 generic error로 좁힌다."""
        try:
            exit_code = self._process.poll()
        except Exception:
            raise McpStdioPopenInputError(
                "MCP STDIO child liveness check failed", correlation_id=correlation_id
            ) from None
        if exit_code is None:
            return None
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise McpStdioPopenInputError(
                "MCP STDIO child liveness check failed", correlation_id=correlation_id
            )
        return exit_code


def _correlation_id_or_raise(request_id: object) -> str:
    """invalid typed ID를 Popen poll 또는 stdin write 전에 generic error로 바꾼다."""
    try:
        return mcp_stdio_request_correlation_id(request_id)  # type: ignore[arg-type]
    except McpStdioError:
        raise McpStdioPopenInputError(
            "MCP STDIO input request id is invalid", correlation_id=None
        ) from None
