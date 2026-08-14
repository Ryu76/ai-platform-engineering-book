"""MCP STDIO child exit 뒤 유한한 restart/backoff intent를 fake seam으로 모델링한다.

이 module은 subprocess, OS clock/sleep API, process signal, pipe 또는 worker를 직접 열지 않는다.
Allowlisted launch plan의 작은 restart budget과 injected monotonic clock/sleeper/factory만 사용해
unexpected exit 뒤 한 child start를 결정한다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from ai_platform.mcp.host import (
    McpStdioChildFactory,
    McpStdioChildProcess,
    McpStdioHostError,
    McpStdioHostLaunchPlan,
    start_mcp_stdio_child,
)

_INITIAL_BACKOFF_SECONDS = 0.25
_MAX_EXIT_CODE = 255


class McpStdioRestartError(ValueError):
    """restart policy가 새 child start 전에 안전하게 중단되었음을 나타낸다."""


class McpStdioExitClassification(StrEnum):
    """platform signal detail을 노출하지 않는 작은 child-exit 분류다."""

    CLEAN = "clean"
    UNEXPECTED = "unexpected"


@dataclass(frozen=True, slots=True)
class McpStdioRestartResult:
    """한 exit observation의 restart 결정과, 시작했다면 새 child snapshot이다."""

    exit_code: int
    classification: McpStdioExitClassification
    restart_count: int
    backoff_seconds: float | None
    child: McpStdioChildProcess | None


class McpStdioRestartSupervisor:
    """한 allowlisted server의 finite unexpected-exit restart policy를 소유한다.

    Clean exit는 restart하지 않는다. Valid non-zero exit만 retry 대상으로 취급하며 plan의
    ``restart_limit``을 다 쓰면 clock, sleeper, factory를 호출하지 않는다. 첫 restart delay는
    0.25초이고 실제 successful restart마다 두 배가 된다. This model deliberately does not
    classify platform signal names, restart after a start failure, or perform any child shutdown.
    """

    def __init__(
        self,
        plan: McpStdioHostLaunchPlan,
        factory: McpStdioChildFactory,
        *,
        monotonic_clock: Callable[[], float],
        sleeper: Callable[[float], None],
    ) -> None:
        if not isinstance(plan, McpStdioHostLaunchPlan):
            raise McpStdioRestartError("MCP STDIO restart launch plan is invalid")
        if not callable(getattr(factory, "start", None)):
            raise McpStdioRestartError("MCP STDIO restart child factory is invalid")
        if not callable(monotonic_clock):
            raise McpStdioRestartError("MCP STDIO restart clock is invalid")
        if not callable(sleeper):
            raise McpStdioRestartError("MCP STDIO restart sleeper is invalid")
        self._plan = plan
        self._factory = factory
        self._monotonic_clock = monotonic_clock
        self._sleeper = sleeper
        self._restart_count = 0

    @property
    def restart_count(self) -> int:
        """성공적으로 시작한 replacement child 수를 반환한다."""
        return self._restart_count

    def observe_exit(self, exit_code: int | None) -> McpStdioRestartResult:
        """한 terminal exit code를 분류하고 필요하면 bounded backoff 뒤 한 번만 시작한다.

        ``None``, bool, platform-specific negative code, 255보다 큰 code는 unknown exit로 취급해
        clock/sleep/start 전에 거부한다. Clock/sleeper/start exception detail은 숨기며, failure는
        budget을 소비하지 않는다. Sleeper 뒤 clock이 deadline에 도달하지 않거나 뒤로 가도
        replacement start를 하지 않는다.
        """
        exit_code = _validated_exit_code(exit_code)
        if exit_code == 0:
            return McpStdioRestartResult(
                exit_code=exit_code,
                classification=McpStdioExitClassification.CLEAN,
                restart_count=self._restart_count,
                backoff_seconds=None,
                child=None,
            )
        if self._restart_count >= self._plan.restart_limit:
            return McpStdioRestartResult(
                exit_code=exit_code,
                classification=McpStdioExitClassification.UNEXPECTED,
                restart_count=self._restart_count,
                backoff_seconds=None,
                child=None,
            )

        backoff_seconds = _INITIAL_BACKOFF_SECONDS * (2**self._restart_count)
        started_at = _read_monotonic_time(self._monotonic_clock)
        deadline = started_at + backoff_seconds
        try:
            self._sleeper(backoff_seconds)
        except Exception:
            raise McpStdioRestartError("MCP STDIO restart backoff sleep failed") from None
        completed_at = _read_monotonic_time(self._monotonic_clock)
        if completed_at < started_at or completed_at < deadline:
            raise McpStdioRestartError("MCP STDIO restart clock did not reach backoff deadline")
        try:
            child = start_mcp_stdio_child(self._plan, self._factory)
        except McpStdioHostError:
            raise McpStdioRestartError("MCP STDIO restart child start failed") from None
        self._restart_count += 1
        return McpStdioRestartResult(
            exit_code=exit_code,
            classification=McpStdioExitClassification.UNEXPECTED,
            restart_count=self._restart_count,
            backoff_seconds=backoff_seconds,
            child=child,
        )


def _validated_exit_code(exit_code: object) -> int:
    """unknown/non-terminal exit status가 restart loop를 열기 전에 막는다."""
    if (
        isinstance(exit_code, bool)
        or not isinstance(exit_code, int)
        or not 0 <= exit_code <= _MAX_EXIT_CODE
    ):
        raise McpStdioRestartError("MCP STDIO restart exit code is unknown")
    return exit_code


def _read_monotonic_time(clock: Callable[[], float]) -> float:
    """clock adapter detail과 NaN/infinity를 새 child start 전에 숨긴다."""
    try:
        timestamp = clock()
    except Exception:
        raise McpStdioRestartError("MCP STDIO restart clock failed") from None
    if (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, (int, float))
        or not isfinite(timestamp)
    ):
        raise McpStdioRestartError("MCP STDIO restart clock returned an invalid timestamp")
    return float(timestamp)
