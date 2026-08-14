"""Volume 03의 fake readiness-driven MCP STDIO pair drain을 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.mcp.ready_drain import (
    McpStdioReadyChannels,
    McpStdioReadyDrainError,
    drain_mcp_stdio_ready_stream_pair,
)


class _FakeReadableStream:
    """OS pipe 없이 planned output과 read turn만 메모리에 보관한다."""

    def __init__(self, name: str, chunks: list[bytes | object], trace: list[str]) -> None:
        self._name = name
        self._chunks = chunks
        self._trace = trace
        self.read_sizes: list[int] = []

    def read(self, size: int) -> bytes:
        self._trace.append(self._name)
        self.read_sizes.append(size)
        chunk = self._chunks.pop(0)
        if isinstance(chunk, BaseException):
            raise chunk
        return chunk  # type: ignore[return-value]


class _FakeScheduler:
    """정해진 readiness snapshot만 반환하고 open state를 기록한다."""

    def __init__(self, snapshots: list[object]) -> None:
        self._snapshots = snapshots
        self.open_states: list[tuple[bool, bool]] = []

    def next_ready(self, *, stdout_open: bool, stderr_open: bool) -> McpStdioReadyChannels:
        self.open_states.append((stdout_open, stderr_open))
        snapshot = self._snapshots.pop(0)
        if isinstance(snapshot, BaseException):
            raise snapshot
        return snapshot  # type: ignore[return-value]


def test_drain_reads_each_ready_stream_once_in_fixed_fair_order_per_snapshot() -> None:
    turns: list[str] = []
    stdout = _FakeReadableStream("stdout", [b"out-1", b"out-2", b""], turns)
    stderr = _FakeReadableStream("stderr", [b"err-1", b"err-2", b""], turns)
    scheduler = _FakeScheduler([McpStdioReadyChannels(True, True)] * 3)

    capture = drain_mcp_stdio_ready_stream_pair(
        stdout, stderr, scheduler, max_stdout_bytes=1_024, max_stderr_bytes=1_024
    )

    assert capture.stdout.data == b"out-1out-2"
    assert capture.stderr.data == b"err-1err-2"
    assert turns == ["stdout", "stderr", "stdout", "stderr", "stdout", "stderr"]
    assert scheduler.open_states == [(True, True), (True, True), (True, True)]
    assert stdout.read_sizes == [1_025, 1_020, 1_015]
    assert stderr.read_sizes == [1_025, 1_020, 1_015]


def test_drain_skips_unready_channel_and_tells_scheduler_when_stdout_reaches_eof() -> None:
    turns: list[str] = []
    stdout = _FakeReadableStream("stdout", [b""], turns)
    stderr = _FakeReadableStream("stderr", [b"one", b"two", b""], turns)
    scheduler = _FakeScheduler(
        [
            McpStdioReadyChannels(True, True),
            McpStdioReadyChannels(False, True),
            McpStdioReadyChannels(False, True),
        ]
    )

    capture = drain_mcp_stdio_ready_stream_pair(
        stdout, stderr, scheduler, max_stdout_bytes=1_024, max_stderr_bytes=1_024
    )

    assert capture.stdout.data == b""
    assert capture.stderr.data == b"onetwo"
    assert turns == ["stdout", "stderr", "stderr", "stderr"]
    assert scheduler.open_states == [(True, True), (False, True), (False, True)]


def test_no_ready_channel_fails_without_read_or_second_scheduler_call() -> None:
    turns: list[str] = []
    stdout = _FakeReadableStream("stdout", [b"must-not-be-read"], turns)
    stderr = _FakeReadableStream("stderr", [b"must-not-be-read"], turns)
    scheduler = _FakeScheduler(
        [McpStdioReadyChannels(False, False), McpStdioReadyChannels(True, True)]
    )

    with pytest.raises(McpStdioReadyDrainError, match="scheduler made no progress"):
        drain_mcp_stdio_ready_stream_pair(
            stdout, stderr, scheduler, max_stdout_bytes=1_024, max_stderr_bytes=1_024
        )

    assert turns == []
    assert scheduler.open_states == [(True, True)]


def test_stale_closed_channel_ready_signal_fails_before_any_new_read() -> None:
    turns: list[str] = []
    stdout = _FakeReadableStream("stdout", [b""], turns)
    stderr = _FakeReadableStream("stderr", [b"safe", b"must-not-be-read"], turns)
    scheduler = _FakeScheduler(
        [McpStdioReadyChannels(True, True), McpStdioReadyChannels(True, False)]
    )

    with pytest.raises(McpStdioReadyDrainError, match="selected closed stdout"):
        drain_mcp_stdio_ready_stream_pair(
            stdout, stderr, scheduler, max_stdout_bytes=1_024, max_stderr_bytes=1_024
        )

    assert turns == ["stdout", "stderr"]
    assert scheduler.open_states == [(True, True), (False, True)]


def test_stdout_overflow_stops_before_ready_stderr_or_later_scheduler_round() -> None:
    turns: list[str] = []
    stdout = _FakeReadableStream("stdout", [b"a" * 1_025], turns)
    stderr = _FakeReadableStream("stderr", [b"must-not-be-read"], turns)
    scheduler = _FakeScheduler(
        [McpStdioReadyChannels(True, True), McpStdioReadyChannels(True, True)]
    )

    with pytest.raises(McpStdioReadyDrainError, match="stdout stream exceeded byte budget"):
        drain_mcp_stdio_ready_stream_pair(
            stdout, stderr, scheduler, max_stdout_bytes=1_024, max_stderr_bytes=1_024
        )

    assert turns == ["stdout"]
    assert scheduler.open_states == [(True, True)]


def test_scheduler_failure_and_invalid_snapshot_hide_adapter_details_before_reading() -> None:
    for snapshot, message in (
        (RuntimeError("secret selector handle"), "scheduler failed"),
        (object(), "scheduler returned an invalid snapshot"),
    ):
        turns: list[str] = []
        stdout = _FakeReadableStream("stdout", [b"must-not-be-read"], turns)
        stderr = _FakeReadableStream("stderr", [b"must-not-be-read"], turns)
        scheduler = _FakeScheduler([snapshot])

        with pytest.raises(McpStdioReadyDrainError, match=message) as error:
            drain_mcp_stdio_ready_stream_pair(
                stdout, stderr, scheduler, max_stdout_bytes=1_024, max_stderr_bytes=1_024
            )

        assert "secret selector handle" not in str(error.value)
        assert turns == []
        assert scheduler.open_states == [(True, True)]


@pytest.mark.parametrize("value", (1, "yes", None))
def test_ready_channels_rejects_non_boolean_flags(value: object) -> None:
    with pytest.raises(McpStdioReadyDrainError, match="flags must be booleans"):
        McpStdioReadyChannels(stdout_ready=value, stderr_ready=False)  # type: ignore[arg-type]


def test_drain_rejects_invalid_scheduler_stream_or_budget_before_io() -> None:
    turns: list[str] = []
    stream = _FakeReadableStream("stdout", [b"must-not-be-read"], turns)
    scheduler = _FakeScheduler([McpStdioReadyChannels(True, True)])

    with pytest.raises(McpStdioReadyDrainError, match="scheduler is invalid"):
        drain_mcp_stdio_ready_stream_pair(
            stream, _FakeReadableStream("stderr", [b"unused"], turns), object(),
            max_stdout_bytes=1_024, max_stderr_bytes=1_024  # type: ignore[arg-type]
        )
    with pytest.raises(McpStdioReadyDrainError, match="stderr byte budget is invalid"):
        drain_mcp_stdio_ready_stream_pair(
            stream, _FakeReadableStream("stderr", [b"unused"], turns), scheduler,
            max_stdout_bytes=1_024, max_stderr_bytes=True  # type: ignore[arg-type]
        )
    with pytest.raises(McpStdioReadyDrainError, match="stdout stream is invalid"):
        drain_mcp_stdio_ready_stream_pair(
            object(), _FakeReadableStream("stderr", [b"unused"], turns), scheduler,
            max_stdout_bytes=1_024, max_stderr_bytes=1_024  # type: ignore[arg-type]
        )

    assert turns == []
    assert scheduler.open_states == []
