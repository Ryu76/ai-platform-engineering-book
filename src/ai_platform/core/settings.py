"""Shared configuration primitives for the practical examples."""

from dataclasses import dataclass
from os import getenv

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class LlmSettings:
    """Runtime settings; the provider secret is never embedded in source."""

    model: str
    api_key: str | None
    base_url: str
    timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "LlmSettings":
        """Load optional credentials without making a network request."""
        timeout_text = getenv("LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
        try:
            timeout_seconds = float(timeout_text)
        except ValueError as error:
            raise ValueError("LLM_TIMEOUT_SECONDS must be a number") from error
        if timeout_seconds <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS must be greater than zero")
        return cls(
            model=getenv("LLM_MODEL", ""),
            api_key=getenv("OPENAI_API_KEY"),
            base_url=getenv("LLM_BASE_URL") or DEFAULT_BASE_URL,
            timeout_seconds=timeout_seconds,
        )
