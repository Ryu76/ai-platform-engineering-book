"""외부 부작용 없이 Volume 03의 allowlisted 계산기 Tool을 실행한다."""

from ai_platform.tools.registry import SAFE_CALCULATOR, ToolRegistry


def main() -> None:
    """고정된 로컬 입력만 사용해 Tool 호출 결과를 출력한다."""
    registry = ToolRegistry((SAFE_CALCULATOR,))
    result = registry.execute(
        tool_name="safe_calculator",
        arguments={"left": 21, "right": 2, "operation": "multiply"},
    )
    print(result.output["value"])


if __name__ == "__main__":
    main()
