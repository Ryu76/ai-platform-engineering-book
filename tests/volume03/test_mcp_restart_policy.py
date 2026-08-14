"""Volume 03 MCP STDIO finite restart/backoff policy를 process-free fake seam으로 검증한다."""

from __future__ import annotations

import pytest

from ai_platform.mcp.host import McpStdioHostAllowlist, McpStdioHostLaunchPlan, McpStdioServerSpec
from ai_platform.mcp.restart_policy import (
    McpStdioExitClassification,
    McpStdioRestartError,
    McpStdioRestartSupervisor,
)


def _plan(*, restart_limit: int = 2) -> McpStdioHostLaunchPlan:
    return McpStdioHostAllowlist(
        (
            McpStdioServerSpec(
                name="safe-echo",
                argv=("volume03-safe-echo-server", "--stdio"),
                max_stdout_bytes=16_384,
                max_stderr_bytes=4_096,
                shutdown_grace_seconds=2.0,
                restart_limit=restart_limit,
            ),
        )
    ).prepare_launch("safe-echo")


class _OfflineChild:
    def poll(self) -> int | None:
        return None

    def terminate(self) -> None:
        return None

    def wait(self, timeout: float) -> int | None:
        del timeout
        return None

    def kill(self) -> None:
        return None


class _RecordingFactory:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def start(
        self,
        *,
        argv: tuple[str, ...],
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        shell: bool,
    ) -> _OfflineChild:
        self.calls.append(
            {
                "argv": argv,
                "max_stdout_bytes": max_stdout_bytes,
                "max_stderr_bytes": max_stderr_bytes,
                "shell": shell,
            }
        )
        return _OfflineChild()


class _OfflineTime:
    def __init__(self, *, start: float = 100.0, advance_on_sleep: bool = True) -> None:
        self.value = start
        self.advance_on_sleep = advance_on_sleep
        self.clock_calls = 0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        self.clock_calls += 1
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        if self.advance_on_sleep:
            self.value += seconds


def test_unexpected_exits_restart_once_each_with_monotonic_exponential_backoff() -> None:
    factory = _RecordingFactory()
    time = _OfflineTime()
    supervisor = McpStdioRestartSupervisor(
        _plan(), factory, monotonic_clock=time.clock, sleeper=time.sleep
    )

    first = supervisor.observe_exit(1)
    second = supervisor.observe_exit(23)

    assert first.classification is McpStdioExitClassification.UNEXPECTED
    assert first.backoff_seconds == 0.25
    assert first.restart_count == 1
    assert first.child is not None
    assert second.backoff_seconds == 0.5
    assert second.restart_count == 2
    assert supervisor.restart_count == 2
    assert time.sleeps == [0.25, 0.5]
    assert len(factory.calls) == 2
    assert all(call["shell"] is False for call in factory.calls)


def test_clean_exit_does_not_touch_clock_sleeper_or_new_start() -> None:
    factory = _RecordingFactory()
    time = _OfflineTime()
    supervisor = McpStdioRestartSupervisor(
        _plan(), factory, monotonic_clock=time.clock, sleeper=time.sleep
    )

    result = supervisor.observe_exit(0)

    assert result.classification is McpStdioExitClassification.CLEAN
    assert result.backoff_seconds is None
    assert result.child is None
    assert time.clock_calls == 0
    assert time.sleeps == []
    assert factory.calls == []


def test_restart_budget_exhaustion_stops_without_backoff_or_new_start() -> None:
    factory = _RecordingFactory()
    time = _OfflineTime()
    supervisor = McpStdioRestartSupervisor(
        _plan(restart_limit=1), factory, monotonic_clock=time.clock, sleeper=time.sleep
    )

    supervisor.observe_exit(1)
    exhausted = supervisor.observe_exit(2)

    assert exhausted.classification is McpStdioExitClassification.UNEXPECTED
    assert exhausted.restart_count == 1
    assert exhausted.backoff_seconds is None
    assert exhausted.child is None
    assert time.sleeps == [0.25]
    assert len(factory.calls) == 1


@pytest.mark.parametrize("unknown_exit", (None, True, -9, 256, "crashed"))
def test_unknown_exit_is_rejected_before_clock_sleep_or_new_start(unknown_exit: object) -> None:
    factory = _RecordingFactory()
    time = _OfflineTime()
    supervisor = McpStdioRestartSupervisor(
        _plan(), factory, monotonic_clock=time.clock, sleeper=time.sleep
    )

    with pytest.raises(McpStdioRestartError, match="exit code is unknown"):
        supervisor.observe_exit(unknown_exit)  # type: ignore[arg-type]

    assert time.clock_calls == 0
    assert time.sleeps == []
    assert factory.calls == []


def test_clock_failure_is_hidden_and_stops_before_sleep_or_new_start() -> None:
    factory = _RecordingFactory()
    time = _OfflineTime()

    def failing_clock() -> float:
        raise RuntimeError("private clock implementation detail")

    supervisor = McpStdioRestartSupervisor(
        _plan(), factory, monotonic_clock=failing_clock, sleeper=time.sleep
    )

    with pytest.raises(McpStdioRestartError, match="clock failed") as error:
        supervisor.observe_exit(1)

    assert "private clock implementation detail" not in str(error.value)
    assert time.sleeps == []
    assert factory.calls == []


def test_sleeper_failure_is_hidden_and_stops_before_new_start() -> None:
    factory = _RecordingFactory()
    time = _OfflineTime()

    def failing_sleep(seconds: float) -> None:
        del seconds
        raise RuntimeError("private wait implementation detail")

    supervisor = McpStdioRestartSupervisor(
        _plan(), factory, monotonic_clock=time.clock, sleeper=failing_sleep
    )

    with pytest.raises(McpStdioRestartError, match="backoff sleep failed") as error:
        supervisor.observe_exit(1)

    assert "private wait implementation detail" not in str(error.value)
    assert factory.calls == []


def test_early_or_non_monotonic_sleep_completion_stops_before_new_start() -> None:
    factory = _RecordingFactory()
    time = _OfflineTime(advance_on_sleep=False)
    supervisor = McpStdioRestartSupervisor(
        _plan(), factory, monotonic_clock=time.clock, sleeper=time.sleep
    )

    with pytest.raises(McpStdioRestartError, match="did not reach backoff deadline"):
        supervisor.observe_exit(1)

    assert time.sleeps == [0.25]
    assert factory.calls == []


def test_invalid_plan_is_rejected_during_supervisor_construction_before_any_start() -> None:
    factory = _RecordingFactory()
    time = _OfflineTime()

    with pytest.raises(McpStdioRestartError, match="launch plan is invalid"):
        McpStdioRestartSupervisor(
            object(),  # type: ignore[arg-type]
            factory,
            monotonic_clock=time.clock,
            sleeper=time.sleep,
        )

    assert factory.calls == []
