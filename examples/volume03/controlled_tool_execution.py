"""순수한 allowlisted Tool의 제한된 재시도를 외부 호출 없이 시연한다."""
from __future__ import annotations

from collections.abc import Mapping

from ai_platform.tools.execution import RetryableToolError, ToolExecutionPolicy, execute_with_policy
from ai_platform.tools.registry import ToolRegistry, ToolSpec


def main() -> None:
    """첫 일시 실패 뒤 두 번째 시도에서 고정된 문자열을 반환한다."""
    attempts = 0

    def flaky_upper(arguments: Mapping[str, object]) -> Mapping[str, object]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RetryableToolError("test-only temporary failure")
        text = arguments["text"]
        assert isinstance(text, str)
        return {"text": text.upper()}

    retryable_upper = ToolSpec(
        name="retryable_upper",
        description="테스트용 일시 실패 뒤 문자열을 대문자로 만드는 순수 Tool입니다.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        handler=flaky_upper,
    )
    result = execute_with_policy(
        ToolRegistry((retryable_upper,)),
        tool_name="retryable_upper",
        arguments={"text": "ai platform"},
        policy=ToolExecutionPolicy(timeout_seconds=0.5, max_attempts=2),
    )
    print(f"{result.tool_name}: {result.output['text']} ({attempts} attempts)")


if __name__ == "__main__":
    main()
