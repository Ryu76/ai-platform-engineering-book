"""고정 allowlist MCP Prompt를 실행·보간 없이 제공하는 교육용 모델."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


class McpPromptError(ValueError):
    """정적 MCP Prompt 계약 또는 allowlist를 벗어난 요청일 때 발생한다."""


@dataclass(frozen=True, slots=True)
class McpPromptMessage:
    """고정 role/content만 가진 정적 Prompt message다."""

    role: str
    content: str

    def __post_init__(self) -> None:
        """역할과 짧은 내장 텍스트라는 최소 계약을 확인한다."""
        if self.role not in {"system", "user", "assistant"}:
            raise McpPromptError("MCP prompt message role must be system, user, or assistant")
        if not self.content.strip():
            raise McpPromptError("MCP prompt message content must not be empty")
        if len(self.content) > 4096:
            raise McpPromptError("MCP prompt message content must be at most 4096 characters")


@dataclass(frozen=True, slots=True)
class McpStaticPrompt:
    """보간 변수나 handler 없이 고정 message만 가진 allowlisted Prompt 정의다."""

    name: str
    description: str
    messages: tuple[McpPromptMessage, ...]

    def __post_init__(self) -> None:
        """이름·설명과 작고 고정된 message 목록을 보장한다."""
        if not self.name.strip():
            raise McpPromptError("MCP prompt name must not be empty")
        if not self.description.strip():
            raise McpPromptError("MCP prompt description must not be empty")
        if not isinstance(self.messages, tuple) or not self.messages:
            raise McpPromptError("MCP static prompt must contain at least one message")
        if len(self.messages) > 8:
            raise McpPromptError("MCP static prompt must contain at most 8 messages")
        if not all(isinstance(message, McpPromptMessage) for message in self.messages):
            raise McpPromptError("MCP static prompt messages must be McpPromptMessage values")
        object.__setattr__(
            self,
            "messages",
            tuple(
                McpPromptMessage(role=message.role, content=message.content)
                for message in self.messages
            ),
        )


class McpPromptCatalog:
    """명시적으로 등록한 정적 Prompt만 이름으로 조회한다.

    이 클래스는 MCP SDK, STDIO, 네트워크, subprocess, 파일 API와 사용자 입력 보간을
    사용하지 않는다. 이름은 정규화하지 않고 정확히 일치하는 allowlist key로만 사용한다.
    """

    def __init__(self, prompts: tuple[McpStaticPrompt, ...]) -> None:
        names = [prompt.name for prompt in prompts]
        if len(names) != len(set(names)):
            raise McpPromptError("MCP prompt names must be unique")
        self._prompts = MappingProxyType(
            {
                prompt.name: McpStaticPrompt(
                    name=prompt.name,
                    description=prompt.description,
                    messages=prompt.messages,
                )
                for prompt in prompts
            }
        )

    def list_prompts(self) -> tuple[dict[str, str], ...]:
        """MCP `prompts/list` 모양의 metadata snapshot만 반환한다."""
        return tuple(
            {"name": prompt.name, "description": prompt.description}
            for prompt in self._prompts.values()
        )

    def get_prompt(self, name: str) -> dict[str, object]:
        """allowlisted Prompt의 고정 message snapshot만 반환하고 보간하지 않는다."""
        prompt = self._prompts.get(name)
        if prompt is None:
            raise McpPromptError(f"MCP prompt is not allowlisted: {name}")
        return {
            "name": prompt.name,
            "description": prompt.description,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in prompt.messages
            ],
        }
