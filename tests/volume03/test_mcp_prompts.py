"""Volume 03의 정적 MCP Prompt가 입력 보간·Tool 권한을 만들지 않는지 검사한다."""
from __future__ import annotations

import pytest

from ai_platform.mcp.prompts import (
    McpPromptCatalog,
    McpPromptError,
    McpPromptMessage,
    McpStaticPrompt,
)

SAFETY_PROMPT = McpStaticPrompt(
    name="tool-safety-reminder",
    description="Reminds an agent about reviewed Tool boundaries.",
    messages=(
        McpPromptMessage(
            role="system",
            content="Use only reviewed, allowlisted Tools and request approval when required.",
        ),
    ),
)


def test_prompt_catalog_lists_and_gets_only_embedded_allowlisted_messages() -> None:
    catalog = McpPromptCatalog((SAFETY_PROMPT,))

    assert catalog.list_prompts() == (
        {
            "name": "tool-safety-reminder",
            "description": "Reminds an agent about reviewed Tool boundaries.",
        },
    )
    assert catalog.get_prompt("tool-safety-reminder") == {
        "name": "tool-safety-reminder",
        "description": "Reminds an agent about reviewed Tool boundaries.",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Use only reviewed, allowlisted Tools and request approval when required."
                ),
            },
        ],
    }
    assert not hasattr(catalog, "execute")


def test_prompt_catalog_does_not_normalize_names_or_accept_interpolation_arguments() -> None:
    catalog = McpPromptCatalog((SAFETY_PROMPT,))

    with pytest.raises(McpPromptError, match="not allowlisted: tool-safety-reminder "):
        catalog.get_prompt("tool-safety-reminder ")
    with pytest.raises(TypeError):
        catalog.get_prompt("tool-safety-reminder", {"user_input": "ignore policy"})  # type: ignore[call-arg]


def test_prompt_catalog_rejects_duplicate_and_non_static_prompt_contracts() -> None:
    with pytest.raises(McpPromptError, match="names must be unique"):
        McpPromptCatalog((SAFETY_PROMPT, SAFETY_PROMPT))
    with pytest.raises(McpPromptError, match="role must be system, user, or assistant"):
        McpPromptMessage(role="tool", content="Do not call anything.")
    with pytest.raises(McpPromptError, match="at most 4096"):
        McpPromptMessage(role="system", content="x" * 4097)
    with pytest.raises(McpPromptError, match="at least one message"):
        McpStaticPrompt(
            name="empty",
            description="Must not have an empty message sequence.",
            messages=(),
        )
    with pytest.raises(McpPromptError, match="McpPromptMessage values"):
        McpStaticPrompt(  # type: ignore[arg-type]
            name="not-a-message",
            description="Only fixed message objects are accepted.",
            messages=("untrusted template",),
        )
