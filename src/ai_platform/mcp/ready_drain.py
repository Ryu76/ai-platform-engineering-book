"""MCP STDIO 두 output을 fake readiness scheduler로 bounded drain한다.

이 module은 selector, thread, async event loop, Popen pipe 또는 child shutdown을 소유하지 않는다.
trusted host가 주입한 fake readiness snapshot에서 ready인 stream만 fixed stdout-then-stderr 순서로
한 번씩 읽는 deterministic model이다. 실제 OS-level backpressure/cancellation adapter는 별도
ownership이다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ai_platform.mcp.fair_drain import McpStdioStreamPairCapture
from ai_platform.mcp.stream_drain import McpStdioReadableBinaryStream, McpStdioStreamCapture

_MAX_STREAM_BYTES = 1_048_576
_MIN_STREAM_BYTES = 1_024
_READ_CHUNK_BYTES = 4_096


class McpStdioReadyDrainError(ValueError):
    """fake readiness scheduling 또는 bounded two-stream drain 실패를 나타낸다."""


@dataclass(frozen=True, slots=True)
class McpStdioReadyChannels:
    """한 scheduler round에서 host가 읽어도 되는 output channel의 immutable snapshot이다."""

    stdout_ready: bool
    stderr_ready: bool

    def __post_init__(self) -> None:
        """truthy object가 아닌 explicit readiness signal만 허용한다."""
        if not isinstance(self.stdout_ready, bool) or not isinstance(self.stderr_ready, bool):
            raise McpStdioReadyDrainError("MCP STDIO readiness flags must be booleans")


@runtime_checkable
class McpStdioReadinessScheduler(Protocol):
    """host-owned output readiness를 한 round씩 제공하는 fake adapter의 최소 계약이다."""

    def next_ready(
        self, *, stdout_open: bool, stderr_open: bool
    ) -> McpStdioReadyChannels:
        """아직 open인 channel 중 이번 round에서 read 가능한 channel만 snapshot으로 반환한다."""


def drain_mcp_stdio_ready_stream_pair(
    stdout_stream: McpStdioReadableBinaryStream,
    stderr_stream: McpStdioReadableBinaryStream,
    scheduler: McpStdioReadinessScheduler,
    *,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> McpStdioStreamPairCapture:
    """ready snapshot마다 ready인 fake stream을 공정하게 한 번씩 bounded drain한다.

    매 snapshot에서 stdout를 먼저, stderr를 다음으로 읽으며 ready인 open channel당 read는 최대
    한 번이다. snapshot이 open channel을 하나도 ready로 선언하지 않거나, 종료한 channel을 다시
    ready로 선언하면 partial capture 없이 종료한다. overflow, malformed data, read/scheduler failure
    뒤에는 이후 read 또는 scheduler call을 하지 않는다.
    """
    _validate_stream(stdout_stream, field_name="stdout stream")
    _validate_stream(stderr_stream, field_name="stderr stream")
    if stdout_stream is stderr_stream:
        raise McpStdioReadyDrainError("stdout and stderr streams must be distinct")
    _validate_scheduler(scheduler)
    _validate_max_bytes(max_stdout_bytes, field_name="stdout byte budget")
    _validate_max_bytes(max_stderr_bytes, field_name="stderr byte budget")

    captures: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    streams = {"stdout": stdout_stream, "stderr": stderr_stream}
    limits = {"stdout": max_stdout_bytes, "stderr": max_stderr_bytes}
    complete = {"stdout": False, "stderr": False}

    while not all(complete.values()):
        ready = _next_ready_snapshot(
            scheduler, stdout_open=not complete["stdout"], stderr_open=not complete["stderr"]
        )
        _validate_snapshot_progress(ready, complete=complete)
        for channel, is_ready in (("stdout", ready.stdout_ready), ("stderr", ready.stderr_ready)):
            if not is_ready:
                continue
            chunk = _read_one_chunk(
                streams[channel],
                channel=channel,
                captured=captures[channel],
                max_bytes=limits[channel],
            )
            if chunk is None:
                complete[channel] = True
            else:
                captures[channel].extend(chunk)

    return McpStdioStreamPairCapture(
        stdout=McpStdioStreamCapture(channel="stdout", data=bytes(captures["stdout"])),
        stderr=McpStdioStreamCapture(channel="stderr", data=bytes(captures["stderr"])),
    )


def _next_ready_snapshot(
    scheduler: McpStdioReadinessScheduler, *, stdout_open: bool, stderr_open: bool
) -> McpStdioReadyChannels:
    """scheduler adapter detail 없이 exactly one trusted readiness snapshot을 얻는다."""
    try:
        ready = scheduler.next_ready(stdout_open=stdout_open, stderr_open=stderr_open)
    except Exception:
        raise McpStdioReadyDrainError("MCP STDIO readiness scheduler failed") from None
    if not isinstance(ready, McpStdioReadyChannels):
        raise McpStdioReadyDrainError("MCP STDIO readiness scheduler returned an invalid snapshot")
    return ready


def _validate_snapshot_progress(ready: McpStdioReadyChannels, *, complete: dict[str, bool]) -> None:
    """stale ready signal과 no-progress wait loop를 read 전에 차단한다."""
    if ready.stdout_ready and complete["stdout"]:
        raise McpStdioReadyDrainError("MCP STDIO readiness scheduler selected closed stdout")
    if ready.stderr_ready and complete["stderr"]:
        raise McpStdioReadyDrainError("MCP STDIO readiness scheduler selected closed stderr")
    if not ready.stdout_ready and not ready.stderr_ready:
        raise McpStdioReadyDrainError("MCP STDIO readiness scheduler made no progress")


def _read_one_chunk(
    stream: McpStdioReadableBinaryStream,
    *,
    channel: str,
    captured: bytearray,
    max_bytes: int,
) -> bytes | None:
    """한 ready turn만 수행하고 raw adapter detail 없이 bounded result만 허용한다."""
    remaining_with_overflow_sentinel = max_bytes - len(captured) + 1
    read_size = min(_READ_CHUNK_BYTES, remaining_with_overflow_sentinel)
    try:
        chunk = stream.read(read_size)
    except Exception:
        raise McpStdioReadyDrainError(f"MCP STDIO {channel} stream read failed") from None
    if not isinstance(chunk, bytes):
        raise McpStdioReadyDrainError(f"MCP STDIO {channel} stream returned non-bytes data")
    if len(chunk) > remaining_with_overflow_sentinel:
        raise McpStdioReadyDrainError(f"MCP STDIO {channel} stream violated read bound")
    if len(captured) + len(chunk) > max_bytes:
        raise McpStdioReadyDrainError(f"MCP STDIO {channel} stream exceeded byte budget")
    if not chunk:
        return None
    return chunk


def _validate_stream(stream: object, *, field_name: str) -> None:
    """readability 외 arbitrary object를 IO 전에 거부한다."""
    if not isinstance(stream, McpStdioReadableBinaryStream):
        raise McpStdioReadyDrainError(f"MCP STDIO {field_name} is invalid")


def _validate_scheduler(scheduler: object) -> None:
    """host-owned fake scheduler seam만 받는다."""
    if not isinstance(scheduler, McpStdioReadinessScheduler):
        raise McpStdioReadyDrainError("MCP STDIO readiness scheduler is invalid")


def _validate_max_bytes(max_bytes: object, *, field_name: str) -> None:
    """각 output이 독립적으로 갖는 finite memory ceiling만 허용한다."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
        raise McpStdioReadyDrainError(f"MCP STDIO {field_name} is invalid")
    if not _MIN_STREAM_BYTES <= max_bytes <= _MAX_STREAM_BYTES:
        raise McpStdioReadyDrainError(f"MCP STDIO {field_name} is invalid")
