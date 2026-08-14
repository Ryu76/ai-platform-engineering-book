"""고정 Mock 모델 응답을 allowlisted Function Calling 경계로 안전하게 연결한다."""
from __future__ import annotations

import json
from collections.abc import Mapping

from ai_platform.tools.function_calling import (
    dispatch_function_call,
    parse_function_call,
    serialize_function_tools,
)
from ai_platform.tools.registry import SAFE_CALCULATOR, SAFE_TEXT_CASE, ToolRegistry


def mock_model_response(function_tools: tuple[dict[str, object], ...]) -> Mapping[str, object]:
    """네트워크 호출 없이 두 Tool 정의를 받는 Mock의 고정 선택 결과를 반환한다."""
    assert len(function_tools) == 2
    return {
        "id": "call_mock_01",
        "type": "function",
        "function": {
            "name": "safe_text_case",
            "arguments": json.dumps({"text": "Ai Platform", "operation": "upper"}),
        },
    }


def main() -> None:
    """직렬화, Mock 선택, 파싱, allowlist 실행의 네 단계를 재현한다."""
    registry = ToolRegistry((SAFE_CALCULATOR, SAFE_TEXT_CASE))
    function_tools = serialize_function_tools(registry)
    call = parse_function_call(mock_model_response(function_tools))
    result = dispatch_function_call(registry, call)
    print(f"{result.tool_name}: {result.output['text']}")


if __name__ == "__main__":
    main()
