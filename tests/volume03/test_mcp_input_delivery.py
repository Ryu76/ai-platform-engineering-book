"""Volume 03 MCP STDIO cancellation/disconnect policy를 fake writer로 검증한다."""

from __future__ import annotations

import pytest

from ai_platform.mcp.input_delivery import (
    McpStdioInputDeliveryError,
    McpStdioInputDeliveryGate,
    McpStdioInputDeliveryState,
)
from ai_platform.mcp.input_write import McpStdioInputFrame, build_mcp_stdio_input_frame


class _FakeBinaryWriter:
    """계획된 결과만 반환하는 memory-only writer이며 실제 child stdin이 아니다."""

    def __init__(self, results: list[int | object]) -> None:
        self._results = results
        self.write_inputs: list[bytes] = []
        self.flush_calls = 0

    def write(self, data: bytes) -> int:
        self.write_inputs.append(data)
        result = self._results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result  # type: ignore[return-value]

    def flush(self) -> None:
        self.flush_calls += 1


def _frame() -> McpStdioInputFrame:
    return build_mcp_stdio_input_frame(
        {"jsonrpc": "2.0", "id": "delivery-001", "method": "safe/test"}
    )


def test_cancelled_typed_request_is_rejected_before_any_writer_io() -> None:
    gate = McpStdioInputDeliveryGate()
    gate.cancel("7")
    writer = _FakeBinaryWriter([])

    with pytest.raises(McpStdioInputDeliveryError, match="cancelled") as error:
        gate.write("7", writer, _frame())

    assert error.value.correlation_id == "mcp-stdio:string:7"
    assert error.value.frame_may_be_partial is False
    assert error.value.child_shutdown_requested is False
    assert writer.write_inputs == []
    assert writer.flush_calls == 0


def test_string_and_integer_jsonrpc_ids_do_not_share_cancellation_state() -> None:
    gate = McpStdioInputDeliveryGate()
    gate.cancel("7")
    frame = _frame()
    writer = _FakeBinaryWriter([frame.byte_count])

    receipt = gate.write(7, writer, frame)

    assert receipt.correlation_id == "mcp-stdio:integer:7"
    assert receipt.write_receipt.byte_count == frame.byte_count
    assert bytes(writer.write_inputs[0]) == frame.data


def test_explicit_disconnect_rejects_new_frame_without_shutdown_side_effect() -> None:
    gate = McpStdioInputDeliveryGate()
    gate.disconnect()
    writer = _FakeBinaryWriter([])

    with pytest.raises(McpStdioInputDeliveryError, match="disconnected") as error:
        gate.write("request-1", writer, _frame())

    assert error.value.frame_may_be_partial is False
    assert error.value.child_shutdown_requested is False
    assert gate.state is McpStdioInputDeliveryState.DISCONNECTED
    assert writer.write_inputs == []


def test_partial_write_failure_requests_caller_owned_shutdown_and_blocks_future_frames() -> None:
    gate = McpStdioInputDeliveryGate()
    writer = _FakeBinaryWriter([OSError("offline secret pipe descriptor")])

    with pytest.raises(McpStdioInputDeliveryError, match="delivery became ambiguous") as error:
        gate.write("request-1", writer, _frame())

    assert error.value.correlation_id == "mcp-stdio:string:request-1"
    assert error.value.frame_may_be_partial is True
    assert error.value.child_shutdown_requested is True
    assert "secret pipe" not in str(error.value)
    assert gate.state is McpStdioInputDeliveryState.SHUTDOWN_REQUIRED
    assert len(writer.write_inputs) == 1
    assert writer.flush_calls == 0

    next_writer = _FakeBinaryWriter([])
    with pytest.raises(McpStdioInputDeliveryError, match="shutdown") as blocked:
        gate.write("request-2", next_writer, _frame())
    assert blocked.value.frame_may_be_partial is False
    assert blocked.value.child_shutdown_requested is True
    assert next_writer.write_inputs == []


def test_invalid_request_id_is_rejected_before_writer_io() -> None:
    gate = McpStdioInputDeliveryGate()
    writer = _FakeBinaryWriter([])

    with pytest.raises(McpStdioInputDeliveryError, match="request id is invalid") as error:
        gate.write(True, writer, _frame())  # type: ignore[arg-type]

    assert error.value.frame_may_be_partial is False
    assert error.value.child_shutdown_requested is False
    assert writer.write_inputs == []
