"""Volume 03 MCP STDIO bounded stdin writer를 offline binary seam으로 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.mcp.input_write import (
    McpStdioInputFrame,
    McpStdioInputWriteError,
    build_mcp_stdio_input_frame,
    write_mcp_stdio_input_frame,
)


class _FakeBinaryWriter:
    """planned write result만 반환하며 subprocess·OS pipe 없이 bytes를 기록한다."""

    def __init__(
        self, results: list[int | object], *, flush_error: Exception | None = None
    ) -> None:
        self._results = results
        self._flush_error = flush_error
        self.data = bytearray()
        self.write_inputs: list[bytes] = []
        self.flush_calls = 0

    def write(self, data: bytes) -> int:
        self.write_inputs.append(data)
        result = self._results.pop(0)
        if isinstance(result, BaseException):
            raise result
        if isinstance(result, int) and not isinstance(result, bool) and result > 0:
            self.data.extend(data[:result])
        return result  # type: ignore[return-value]

    def flush(self) -> None:
        self.flush_calls += 1
        if self._flush_error is not None:
            raise self._flush_error


def _notification_frame() -> McpStdioInputFrame:
    return build_mcp_stdio_input_frame(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}
    )


def test_writer_sends_valid_immutable_frame_and_flushes_once() -> None:
    frame = _notification_frame()
    writer = _FakeBinaryWriter([frame.byte_count])

    receipt = write_mcp_stdio_input_frame(writer, frame)

    assert receipt.byte_count == frame.byte_count
    assert receipt.write_calls == 1
    assert bytes(writer.data) == frame.data
    assert writer.write_inputs == [frame.data]
    assert writer.flush_calls == 1


def test_writer_continues_after_short_positive_writes_without_reencoding_frame() -> None:
    frame = _notification_frame()
    writer = _FakeBinaryWriter([3, 5, frame.byte_count - 8])

    receipt = write_mcp_stdio_input_frame(writer, frame)

    assert receipt.write_calls == 3
    assert bytes(writer.data) == frame.data
    assert writer.write_inputs == [frame.data, frame.data[3:], frame.data[8:]]
    assert writer.flush_calls == 1


def test_writer_caps_each_binary_write_at_four_kibibytes() -> None:
    frame = build_mcp_stdio_input_frame(
        {
            "jsonrpc": "2.0",
            "id": "large-frame-001",
            "method": "safe/test",
            "params": {"fixed": "x" * 9_000},
        }
    )
    writer = _FakeBinaryWriter([4_096, 4_096, frame.byte_count - 8_192])

    receipt = write_mcp_stdio_input_frame(writer, frame)

    assert receipt.write_calls == 3
    assert [len(data) for data in writer.write_inputs] == [4_096, 4_096, frame.byte_count - 8_192]
    assert max(map(len, writer.write_inputs)) == 4_096
    assert bytes(writer.data) == frame.data


@pytest.mark.parametrize(
    "result",
    (
        0,
        -1,
        True,
        "one",
    ),
)
def test_writer_rejects_zero_or_malformed_write_count_without_retry(result: object) -> None:
    frame = _notification_frame()
    writer = _FakeBinaryWriter([result, frame.byte_count])

    with pytest.raises(McpStdioInputWriteError, match="invalid write count") as error:
        write_mcp_stdio_input_frame(writer, frame)

    assert error.value.frame_may_be_partial is True
    assert len(writer.write_inputs) == 1
    assert writer.flush_calls == 0


def test_writer_rejects_count_larger_than_requested_without_retry() -> None:
    frame = _notification_frame()
    writer = _FakeBinaryWriter([frame.byte_count + 1])

    with pytest.raises(McpStdioInputWriteError, match="invalid write count") as error:
        write_mcp_stdio_input_frame(writer, frame)

    assert error.value.frame_may_be_partial is True
    assert len(writer.write_inputs) == 1
    assert writer.flush_calls == 0


def test_writer_hides_write_exception_detail_and_does_not_flush_or_retry() -> None:
    frame = _notification_frame()
    writer = _FakeBinaryWriter([OSError("offline secret descriptor")])

    with pytest.raises(McpStdioInputWriteError, match="stream write failed") as error:
        write_mcp_stdio_input_frame(writer, frame)

    assert error.value.frame_may_be_partial is True
    assert "secret descriptor" not in str(error.value)
    assert len(writer.write_inputs) == 1
    assert writer.flush_calls == 0


def test_writer_marks_complete_frame_as_ambiguous_when_flush_fails() -> None:
    frame = _notification_frame()
    writer = _FakeBinaryWriter([frame.byte_count], flush_error=OSError("offline flush secret"))

    with pytest.raises(McpStdioInputWriteError, match="stream flush failed") as error:
        write_mcp_stdio_input_frame(writer, frame)

    assert error.value.frame_may_be_partial is True
    assert "flush secret" not in str(error.value)
    assert bytes(writer.data) == frame.data
    assert writer.flush_calls == 1


def test_frame_builder_rejects_raw_invalid_or_oversized_payload_without_writer_io() -> None:
    with pytest.raises(McpStdioInputWriteError, match="input payload is invalid") as error:
        build_mcp_stdio_input_frame({"jsonrpc": "1.0", "method": "bad"})
    assert error.value.frame_may_be_partial is False
    with pytest.raises(McpStdioInputWriteError, match="input payload is invalid"):
        build_mcp_stdio_input_frame(
            {"jsonrpc": "2.0", "method": "safe/test", "params": {"fixed": "x" * 20_000}}
        )


def test_constructor_rejects_non_frame_or_untrusted_raw_bytes_before_write() -> None:
    with pytest.raises(McpStdioInputWriteError, match="input frame is invalid") as error:
        McpStdioInputFrame(b'{"jsonrpc":"2.0","method":"safe/test"}')
    assert error.value.frame_may_be_partial is False

    writer = _FakeBinaryWriter([])
    with pytest.raises(McpStdioInputWriteError, match="input frame is invalid") as error:
        write_mcp_stdio_input_frame(writer, object())  # type: ignore[arg-type]
    assert error.value.frame_may_be_partial is False
    assert writer.write_inputs == []
    assert writer.flush_calls == 0


def test_writer_rejects_invalid_stream_before_frame_write() -> None:
    with pytest.raises(McpStdioInputWriteError, match="input stream is invalid") as error:
        write_mcp_stdio_input_frame(object(), _notification_frame())  # type: ignore[arg-type]

    assert error.value.frame_may_be_partial is False
