"""MCP STDIO readiness drain이 fake scheduler와 in-memory stream만 소비함을 확인한다."""
from __future__ import annotations

from ai_platform.mcp.ready_drain import (
    McpStdioReadyChannels,
    drain_mcp_stdio_ready_stream_pair,
)


class OfflineReadableStream:
    """subprocess·OS pipe 없이 fixed bytes와 read turn만 기록한다."""

    def __init__(self, name: str, chunks: list[bytes], turns: list[str]) -> None:
        self._name = name
        self._chunks = chunks
        self._turns = turns

    def read(self, size: int) -> bytes:
        """요청 ceiling을 넘지 않는 planned chunk 하나만 반환한다."""
        self._turns.append(self._name)
        chunk = self._chunks.pop(0)
        assert len(chunk) <= size
        return chunk


class OfflineReadinessScheduler:
    """운영 selector 없이 검토된 fixed readiness snapshot만 반환한다."""

    def __init__(self, snapshots: list[McpStdioReadyChannels]) -> None:
        self._snapshots = snapshots

    def next_ready(self, *, stdout_open: bool, stderr_open: bool) -> McpStdioReadyChannels:
        """open state를 path·handle로 해석하지 않고 다음 fixed snapshot을 제공한다."""
        del stdout_open, stderr_open
        return self._snapshots.pop(0)


def main() -> None:
    """두 fake output을 ready turn에서만 bounded 수집하고 Tool을 실행하지 않는다."""
    turns: list[str] = []
    stdout = OfflineReadableStream("stdout", [b"out-1", b"out-2", b""], turns)
    stderr = OfflineReadableStream("stderr", [b"err-1", b"err-2", b""], turns)
    scheduler = OfflineReadinessScheduler([McpStdioReadyChannels(True, True)] * 3)
    capture = drain_mcp_stdio_ready_stream_pair(
        stdout,
        stderr,
        scheduler,
        max_stdout_bytes=1_024,
        max_stderr_bytes=1_024,
    )

    print(f"stdout_bytes: {capture.stdout.byte_count}")
    print(f"stderr_bytes: {capture.stderr.byte_count}")
    print(f"turns: {','.join(turns)}")


if __name__ == "__main__":
    main()
