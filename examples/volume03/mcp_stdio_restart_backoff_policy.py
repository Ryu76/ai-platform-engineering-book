"""MCP STDIO finite restart/backoff intent를 memory-only seams로 확인한다."""

from __future__ import annotations

from ai_platform.mcp.host import McpStdioHostAllowlist, McpStdioServerSpec
from ai_platform.mcp.restart_policy import McpStdioRestartSupervisor


class OfflineChild:
    """실제 process 없이 child shutdown protocol만 만족하는 fake다."""

    def poll(self) -> int | None:
        return None

    def terminate(self) -> None:
        return None

    def wait(self, timeout: float) -> int | None:
        del timeout
        return None

    def kill(self) -> None:
        return None


class OfflineFactory:
    """Popen을 호출하지 않고 allowlisted start request 횟수만 기록한다."""

    def __init__(self) -> None:
        self.start_calls = 0

    def start(
        self,
        *,
        argv: tuple[str, ...],
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        shell: bool,
    ) -> OfflineChild:
        del argv, max_stdout_bytes, max_stderr_bytes, shell
        self.start_calls += 1
        return OfflineChild()


class OfflineMonotonicTime:
    """OS clock/sleep 없이 memory timestamp만 backoff만큼 전진시킨다."""

    def __init__(self) -> None:
        self.timestamp = 100.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.timestamp

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.timestamp += seconds


def main() -> None:
    """nonzero fake exit 하나를 bounded delay 뒤 allowlisted replacement로 모델링한다."""
    plan = McpStdioHostAllowlist(
        (
            McpStdioServerSpec(
                name="safe-echo",
                argv=("volume03-safe-echo-server", "--stdio"),
                max_stdout_bytes=16_384,
                max_stderr_bytes=4_096,
                shutdown_grace_seconds=2.0,
                restart_limit=1,
            ),
        )
    ).prepare_launch("safe-echo")
    factory = OfflineFactory()
    time = OfflineMonotonicTime()
    result = McpStdioRestartSupervisor(
        plan, factory, monotonic_clock=time.clock, sleeper=time.sleep
    ).observe_exit(1)

    print(f"exit_classification: {result.classification}")
    print(f"backoff_seconds: {result.backoff_seconds}")
    print(f"restart_count: {result.restart_count}")
    print(f"offline_start_calls: {factory.start_calls}")


if __name__ == "__main__":
    main()
