"""Shared configuration primitives for the practical examples."""
from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True, slots=True)
class LlmSettings:
    """Runtime settings; the provider secret is never embedded in source."""

    model: str
    api_key: str | None

    @classmethod
    def from_environment(cls) -> LlmSettings:
        """Load optional credentials without making a network request."""
        return cls(model=getenv("LLM_MODEL", ""), api_key=getenv("OPENAI_API_KEY"))
