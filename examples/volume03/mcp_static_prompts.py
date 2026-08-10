"""고정 allowlist MCP Prompt만 나열·조회하며 사용자 입력을 보간하지 않는다."""
from __future__ import annotations

from ai_platform.mcp.prompts import McpPromptCatalog, McpPromptMessage, McpStaticPrompt

PROMPT = McpStaticPrompt(
    name="tool-safety-reminder",
    description="Reminds an agent to keep Tool execution inside reviewed boundaries.",
    messages=(
        McpPromptMessage(
            role="system",
            content="Use only reviewed, allowlisted Tools and request approval when required.",
        ),
    ),
)


def main() -> None:
    """고정 Prompt만 읽고 Tool·파일·셸·네트워크에는 접근하지 않는다."""
    catalog = McpPromptCatalog((PROMPT,))
    listed = catalog.list_prompts()[0]
    prompt = catalog.get_prompt(listed["name"])
    message = prompt["messages"][0]
    assert isinstance(message, dict)
    print(f"{prompt['name']}: {message['role']}: {message['content']}")


if __name__ == "__main__":
    main()
