"""Volume 03 Popen stdin ownership boundary를 real process 없이 검증한다."""

from __future__ import annotations

import pytest

from ai_platform.mcp.input_delivery import McpStdioInputDeliveryError, McpStdioInputDeliveryState
from ai_platform.mcp.input_write import McpStdioInputFrame, build_mcp_stdio_input_frame
from ai_platform.mcp.popen_input import McpStdioPopenInputError, McpStdioPopenInputOwner


class _OfflineWriter:
    """write 결과만 계획·기록하는 memory-only binary writer다."""

    def __init__(self, results: list[int | object]) -> None:
        self._results = results
        self.inputs: list[bytes] = []
        self.flush_calls = 0

    def write(self, data: bytes) -> int:
        self.inputs.append(data)
        result = self._results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result  # type: ignore[return-value]

    def flush(self) -> None:
        self.flush_calls += 1


class _OfflinePopen:
    """실제 Popen·pipe·process를 열지 않는 injected process seam이다."""

    def __init__(self, stdin: _OfflineWriter | None, statuses: list[int | None | object]) -> None:
        self.stdin = stdin
        self._statuses = statuses
        self.poll_calls = 0

    def poll(self) -> int | None:
        self.poll_calls += 1
        status = self._statuses.pop(0)
        if isinstance(status, BaseException):
            raise status
        return status  # type: ignore[return-value]


def _frame() -> McpStdioInputFrame:
    return build_mcp_stdio_input_frame(
        {"jsonrpc": "2.0", "id": "popen-input-001", "method": "safe/test"}
    )


def test_live_popen_stdin_snapshot_delivers_one_bounded_frame() -> None:
    writer = _OfflineWriter([_frame().byte_count])
    process = _OfflinePopen(writer, [None])
    owner = McpStdioPopenInputOwner(process)

    receipt = owner.write("popen-input-001", _frame())

    assert receipt.correlation_id == "mcp-stdio:string:popen-input-001"
    assert receipt.write_receipt.byte_count == _frame().byte_count
    assert process.poll_calls == 1
    assert writer.inputs == [_frame().data]
    assert writer.flush_calls == 1
    assert owner.state is McpStdioInputDeliveryState.OPEN


def test_cancelled_request_is_rejected_before_poll_or_writer_io() -> None:
    writer = _OfflineWriter([])
    process = _OfflinePopen(writer, [])
    owner = McpStdioPopenInputOwner(process)
    owner.cancel("cancel-me")

    with pytest.raises(McpStdioInputDeliveryError, match="cancelled"):
        owner.write("cancel-me", _frame())

    assert process.poll_calls == 0
    assert writer.inputs == []
    assert writer.flush_calls == 0


def test_exited_child_disconnects_owner_before_writer_io_and_blocks_future_poll() -> None:
    writer = _OfflineWriter([])
    process = _OfflinePopen(writer, [17])
    owner = McpStdioPopenInputOwner(process)

    with pytest.raises(McpStdioPopenInputError, match="stdin is unavailable") as error:
        owner.write("closed-001", _frame())

    assert error.value.correlation_id == "mcp-stdio:string:closed-001"
    assert error.value.frame_may_be_partial is False
    assert owner.state is McpStdioInputDeliveryState.DISCONNECTED
    assert process.poll_calls == 1
    assert writer.inputs == []

    with pytest.raises(McpStdioInputDeliveryError, match="disconnected"):
        owner.write("closed-002", _frame())
    assert process.poll_calls == 1
    assert writer.inputs == []


def test_poll_failure_is_generic_and_never_reaches_writer() -> None:
    writer = _OfflineWriter([])
    process = _OfflinePopen(writer, [OSError("sensitive child pid 4242")])
    owner = McpStdioPopenInputOwner(process)

    with pytest.raises(McpStdioPopenInputError, match="liveness check failed") as error:
        owner.write("poll-failure", _frame())

    assert "4242" not in str(error.value)
    assert writer.inputs == []
    assert writer.flush_calls == 0
    assert owner.state is McpStdioInputDeliveryState.OPEN


def test_partial_write_failure_keeps_delivery_gate_shutdown_signal() -> None:
    writer = _OfflineWriter([OSError("offline broken pipe")])
    process = _OfflinePopen(writer, [None])
    owner = McpStdioPopenInputOwner(process)

    with pytest.raises(McpStdioInputDeliveryError, match="became ambiguous") as error:
        owner.write("partial-001", _frame())

    assert error.value.frame_may_be_partial is True
    assert error.value.child_shutdown_requested is True
    assert owner.state is McpStdioInputDeliveryState.SHUTDOWN_REQUIRED
    assert len(writer.inputs) == 1


def test_binding_snapshots_stdin_once_even_if_foreign_code_replaces_process_attribute() -> None:
    original_writer = _OfflineWriter([_frame().byte_count])
    replacement_writer = _OfflineWriter([])
    process = _OfflinePopen(original_writer, [None])
    owner = McpStdioPopenInputOwner(process)
    process.stdin = replacement_writer

    owner.write("snapshot-001", _frame())

    assert original_writer.inputs == [_frame().data]
    assert replacement_writer.inputs == []


@pytest.mark.parametrize("stdin", (None, object()))
def test_binding_rejects_missing_or_invalid_stdin_before_poll(stdin: object | None) -> None:
    process = _OfflinePopen(stdin, [])  # type: ignore[arg-type]

    with pytest.raises(McpStdioPopenInputError, match="stdin is unavailable"):
        McpStdioPopenInputOwner(process)

    assert process.poll_calls == 0
