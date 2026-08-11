"""Offline release-candidate reports for the Volume 02 Prompt mini project."""
from __future__ import annotations

from dataclasses import dataclass

from ai_platform.prompts.prompt_runner import (
    PromptVersionComparison,
    PromptVersionError,
    RecordedClassification,
    VersionedPrompt,
    compare_recorded_classifications,
)
from ai_platform.prompts.prompt_test_data import PromptTestDataset


@dataclass(frozen=True, slots=True)
class PromptRegressionReport:
    """A minimal, non-sensitive report for one reviewed Prompt-version comparison.

    The report stores only dataset and comparison metadata. It deliberately excludes raw
    user inputs and recorded responses so a caller does not accidentally treat this
    educational artifact as a customer-data log or a model invocation record.
    """

    dataset_name: str
    comparison: PromptVersionComparison

    @property
    def failed_case_ids(self) -> tuple[str, ...]:
        """Return stable IDs whose JSON or expected category did not pass review."""
        return tuple(
            case.case_id
            for case in self.comparison.cases
            if not case.schema_valid or not case.category_matches
        )

    @property
    def is_release_candidate(self) -> bool:
        """Require every reviewed case to pass before human release review.

        This flag is not an automatic deployment decision. It only shows that the fixed,
        reviewed records meet this small offline contract.
        """
        return not self.failed_case_ids


def evaluate_prompt_records(
    dataset: PromptTestDataset,
    prompt: VersionedPrompt,
    recorded_outputs: tuple[RecordedClassification, ...],
) -> PromptRegressionReport:
    """Evaluate fixed records against one version without calling an LLM or network.

    The underlying comparison requires a non-empty, one-to-one case/result mapping and
    records invalid JSON as a failure. Contract violations raise ``PromptVersionError``
    instead of being repaired or silently omitted.
    """
    if not isinstance(dataset, PromptTestDataset):
        raise PromptVersionError("dataset must be a PromptTestDataset instance")
    comparison = compare_recorded_classifications(
        prompt,
        dataset.comparison_cases(),
        recorded_outputs,
    )
    return PromptRegressionReport(dataset.name.strip(), comparison)
