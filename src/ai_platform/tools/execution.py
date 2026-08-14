"""allowlisted Tool 실행에 제한된 timeout과 재시도를 적용하는 안전한 경계."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from queue import Empty, Queue
from threading import Thread

from ai_platform.tools.registry import ToolRegistry, ToolRegistryError, ToolResult


class RetryableToolError(Exception):
    """명시적으로 재시도해도 되는 일시적, 부작용 없는 Tool 실패다."""


class ToolExecutionTimeoutError(ToolRegistryError):
    """한 Tool 시도가 정해진 시간 안에 끝나지 않았을 때 발생한다."""


class ToolRetryExhaustedError(ToolRegistryError):
    """재시도 가능한 실패가 허용된 시도 횟수를 모두 사용했을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class ToolExecutionPolicy:
    """한 Tool 요청에 적용할 작은 timeout과 총 시도 횟수의 상한이다."""

    timeout_seconds: float
    max_attempts: int = 1

    def __post_init__(self) -> None:
        """정책이 무한 대기나 무제한 재시도를 만들지 못하게 제한한다."""
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ToolRegistryError("timeout_seconds must be a positive finite number")
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or not 1 <= self.max_attempts <= 3
        ):
            raise ToolRegistryError("max_attempts must be an integer from 1 through 3")


def execute_with_policy(
    registry: ToolRegistry,
    *,
    tool_name: str,
    arguments: Mapping[str, object],
    policy: ToolExecutionPolicy,
) -> ToolResult:
    """기존 allowlist 경계를 매 시도 통과시키고 명시적 일시 오류만 제한 재시도한다."""
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return _execute_once(
                registry,
                tool_name=tool_name,
                arguments=arguments,
                timeout_seconds=policy.timeout_seconds,
            )
        except RetryableToolError as error:
            if attempt == policy.max_attempts:
                raise ToolRetryExhaustedError(
                    f"retryable tool failure after {policy.max_attempts} attempt(s): {tool_name}"
                ) from error
    raise AssertionError("the bounded retry loop must return or raise")


def _execute_once(
    registry: ToolRegistry,
    *,
    tool_name: str,
    arguments: Mapping[str, object],
    timeout_seconds: float,
) -> ToolResult:
    """한 allowlisted 실행을 daemon worker에서 기다리며 완료 결과 또는 예외를 전달한다."""
    completion: Queue[ToolResult | Exception] = Queue(maxsize=1)

    def invoke() -> None:
        try:
            completion.put(registry.execute(tool_name=tool_name, arguments=arguments))
        except Exception as error:
            completion.put(error)

    worker = Thread(target=invoke, daemon=True)
    worker.start()
    try:
        outcome = completion.get(timeout=timeout_seconds)
    except Empty as error:
        raise ToolExecutionTimeoutError(
            f"tool execution timed out after {timeout_seconds} second(s): {tool_name}"
        ) from error
    if isinstance(outcome, Exception):
        raise outcome
    return outcome
