"""고정 골든 데이터셋의 라벨·버전·no-answer 계약을 검증한다."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from re import fullmatch
from typing import Literal


class GoldenDatasetError(ValueError):
    """골든 데이터셋이 재현 가능한 라벨 계약을 위반할 때 발생한다."""


ExpectedResponse = Literal["answer", "abstain"]


@dataclass(frozen=True, slots=True)
class GoldenCase:
    """검토 근거와 기대 동작을 포함하는 하나의 고정 평가 사례다."""

    case_id: str
    query: str
    category: str
    expected_response: ExpectedResponse
    relevant_document_ids: tuple[str, ...]
    label_rationale: str
    source_reference: str

    def __post_init__(self) -> None:
        """라벨 모호성, 중복 정답, no-answer 오표기를 조기에 막는다."""
        _require_non_empty("case_id", self.case_id)
        _require_non_empty("query", self.query)
        _require_non_empty("category", self.category)
        _require_non_empty("label_rationale", self.label_rationale)
        _require_non_empty("source_reference", self.source_reference)
        if self.expected_response not in {"answer", "abstain"}:
            raise GoldenDatasetError("expected_response must be 'answer' or 'abstain'")
        has_invalid_document_id = any(
            not isinstance(document_id, str) or not document_id.strip()
            for document_id in self.relevant_document_ids
        )
        if has_invalid_document_id:
            raise GoldenDatasetError("relevant document ids must be non-empty strings")
        if len(set(self.relevant_document_ids)) != len(self.relevant_document_ids):
            raise GoldenDatasetError("relevant document ids must be unique")
        if self.expected_response == "answer" and not self.relevant_document_ids:
            raise GoldenDatasetError("answer cases must have at least one relevant document")
        if self.expected_response == "abstain" and self.relevant_document_ids:
            raise GoldenDatasetError("abstain cases must not have relevant documents")


@dataclass(frozen=True, slots=True)
class GoldenDataset:
    """비교 가능한 평가를 위한 불변 사례 묶음과 명시적 데이터셋 버전이다."""

    dataset_id: str
    version: str
    cases: tuple[GoldenCase, ...]

    def __post_init__(self) -> None:
        """데이터셋 식별자·버전·사례 ID가 하나의 명확한 기준이 되게 한다."""
        _require_non_empty("dataset_id", self.dataset_id)
        if fullmatch(r"\d+\.\d+\.\d+", self.version) is None:
            raise GoldenDatasetError("version must use MAJOR.MINOR.PATCH format")
        if not self.cases:
            raise GoldenDatasetError("a golden dataset requires at least one case")
        case_ids = tuple(case.case_id for case in self.cases)
        if len(set(case_ids)) != len(case_ids):
            raise GoldenDatasetError("golden dataset case ids must be unique")


@dataclass(frozen=True, slots=True)
class GoldenDatasetSummary:
    """외부 호출 없이 생성하는 데이터셋 구성 감사 결과다."""

    dataset_id: str
    version: str
    cases_total: int
    answer_cases: int
    abstain_cases: int
    categories: tuple[tuple[str, int], ...]


def summarize_golden_dataset(dataset: GoldenDataset) -> GoldenDatasetSummary:
    """고정 입력에서 항상 같은 사례 수·기대 동작·카테고리 구성을 반환한다."""
    category_counts = Counter(case.category for case in dataset.cases)
    answer_cases = sum(case.expected_response == "answer" for case in dataset.cases)
    return GoldenDatasetSummary(
        dataset_id=dataset.dataset_id,
        version=dataset.version,
        cases_total=len(dataset.cases),
        answer_cases=answer_cases,
        abstain_cases=len(dataset.cases) - answer_cases,
        categories=tuple(sorted(category_counts.items())),
    )


def _require_non_empty(field_name: str, value: str) -> None:
    """사람이 검토해야 할 텍스트 필드의 빈 값을 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise GoldenDatasetError(f"{field_name} must be a non-empty string")
