"""MCP STDIO fair pair drain이 fake in-memory streams만 교대 소비함을 확인한다."""
from __future__ import annotations

from ai_platform.mcp.fair_drain import drain_mcp_stdio_stream_pair_fairly


class OfflineScheduledStream:
    """subprocess·OS pipe 없이 fixed chunks와 scheduler trace만 제공한다."""

    def __init__(self, name: str, chunks: list[bytes], trace: list[str]) -> None:
        self._name = name
        self._chunks = chunks
        self._trace = trace

    def read(self, size: int) -> bytes:
        """요청 ceiling을 넘지 않는 planned chunk 하나만 반환한다."""
        self._trace.append(self._name)
        chunk = self._chunks.pop(0)
        assert len(chunk) <= size
        return chunk


def main() -> None:
    """두 fake output을 decode·subprocess·Tool 실행 없이 round-robin으로 수집한다."""
    trace: list[str] = []
    stdout = OfflineScheduledStream("stdout", [b"out-1", b"out-2", b""], trace)
    stderr = OfflineScheduledStream("stderr", [b"err-1", b"err-2", b""], trace)
    capture = drain_mcp_stdio_stream_pair_fairly(
        stdout, stderr, max_stdout_bytes=1_024, max_stderr_bytes=1_024
    )

    print(f"stdout_bytes: {capture.stdout.byte_count}")
    print(f"stderr_bytes: {capture.stderr.byte_count}")
    print(f"turns: {','.join(trace)}")


if __name__ == "__main__":
    main()
