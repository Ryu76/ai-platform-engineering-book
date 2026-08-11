"""Reviewed, offline Prompt test data for repeatable version comparisons."""
from __future__ import annotations

import re
from dataclasses import dataclass

from ai_platform.prompts.prompt_runner import Category, PromptComparisonCase, PromptVersionError
from ai_platform.prompts.prompt_templates import _require_text

_CASE_ID_PATTERN = re.compile(r"[a-z][a-z0-9-]*\Z")


@dataclass(frozen=True, slots=True)
class PromptTestCase:
    """One human-reviewed input, expected category, and purpose for Prompt testing.

    This is test fixture data. It neither calls a model nor treats an expected value as a
    prediction. Keep production customer data and secrets out of these records.
    """

    case_id: str
    user_input: str
    expected_category: Category
    purpose: str
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate each fixture before a comparison can depend on it."""
        case_id = _require_text("case_id", self.case_id)
        if not _CASE_ID_PATTERN.fullmatch(case_id):
            raise PromptVersionError(
                "case_id must start with a lowercase letter and use only lowercase letters, "
                "digits, or hyphens"
            )
        _require_text("user_input", self.user_input)
        _require_text("purpose", self.purpose)
        if self.expected_category not in {"billing", "technical", "unknown"}:
            raise PromptVersionError("expected_category must be billing, technical, or unknown")
        if not isinstance(self.tags, tuple) or not self.tags:
            raise PromptVersionError("tags must be a non-empty tuple")
        if any(not isinstance(tag, str) or not tag.strip() for tag in self.tags):
            raise PromptVersionError("tags must contain only non-empty strings")

    def to_comparison_case(self) -> PromptComparisonCase:
        """Create the existing comparison contract without changing reviewed data."""
        return PromptComparisonCase(
            case_id=self.case_id.strip(),
            user_input=self.user_input.strip(),
            expected_category=self.expected_category,
        )


@dataclass(frozen=True, slots=True)
class PromptTestDataset:
    """A named immutable collection of reviewed Prompt test cases."""

    name: str
    cases: tuple[PromptTestCase, ...]

    def __post_init__(self) -> None:
        """Reject empty, mistyped, or duplicate fixture collections fail-closed."""
        _require_text("name", self.name)
        if not isinstance(self.cases, tuple) or not self.cases or not all(
            isinstance(case, PromptTestCase) for case in self.cases
        ):
            raise PromptVersionError("cases must be a non-empty tuple of PromptTestCase values")
        case_ids = tuple(case.case_id.strip() for case in self.cases)
        if len(set(case_ids)) != len(case_ids):
            raise PromptVersionError("cases must not contain duplicate case_id values")

    def comparison_cases(self) -> tuple[PromptComparisonCase, ...]:
        """Return stable, ordered cases suitable for every Prompt-version comparison."""
        return tuple(case.to_comparison_case() for case in self.cases)

    def cases_with_tag(self, tag: str) -> tuple[PromptTestCase, ...]:
        """Return reviewed cases for one tag while preserving their original order."""
        normalized_tag = _require_text("tag", tag).strip()
        return tuple(case for case in self.cases if normalized_tag in case.tags)
