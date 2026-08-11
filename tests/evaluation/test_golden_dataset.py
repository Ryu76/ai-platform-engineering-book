"""Volume 10의 고정 골든 데이터셋 라벨과 버전 계약을 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.evaluation import (
    FIXED_GOLDEN_DATASET,
    FIXED_RETRIEVAL_CASES,
    GoldenCase,
    GoldenDataset,
    GoldenDatasetError,
    summarize_golden_dataset,
)


def test_fixed_golden_dataset_has_a_reproducible_versioned_manifest() -> None:
    """고정 사례의 수·버전·기대 동작·분류는 실행마다 같아야 한다."""
    summary = summarize_golden_dataset(FIXED_GOLDEN_DATASET)

    assert summary.dataset_id == "volume10-support-policy"
    assert summary.version == "1.0.0"
    assert summary.cases_total == 5
    assert summary.answer_cases == 4
    assert summary.abstain_cases == 1
    assert summary.categories == (
        ("facilities", 1),
        ("finance", 1),
        ("identity", 1),
        ("people", 1),
        ("security", 1),
    )


def test_no_answer_case_has_an_explicit_abstain_label_and_stays_out_of_retrieval_recall() -> None:
    """관련 문서가 없는 질의는 검색 Recall 평균에 섞지 않고 별도 정책으로 기록한다."""
    abstain_cases = tuple(
        case for case in FIXED_GOLDEN_DATASET.cases if case.expected_response == "abstain"
    )

    assert len(abstain_cases) == 1
    assert abstain_cases[0].case_id == "office-parking"
    assert abstain_cases[0].relevant_document_ids == ()
    assert {case.case_id for case in FIXED_RETRIEVAL_CASES}.isdisjoint(
        {case.case_id for case in abstain_cases}
    )


@pytest.mark.parametrize(
    ("expected_response", "relevant_document_ids", "message"),
    [
        ("answer", (), "answer cases"),
        ("abstain", ("policy-a",), "abstain cases"),
        ("unknown", (), "expected_response"),
    ],
)
def test_golden_case_rejects_ambiguous_answer_or_no_answer_labels(
    expected_response: str,
    relevant_document_ids: tuple[str, ...],
    message: str,
) -> None:
    """답변과 거절의 기대 동작은 정답 문서 집합과 모순되면 안 된다."""
    with pytest.raises(GoldenDatasetError, match=message):
        GoldenCase(
            case_id="case-a",
            query="질의",
            category="test",
            expected_response=expected_response,  # type: ignore[arg-type]
            relevant_document_ids=relevant_document_ids,
            label_rationale="검토 근거",
            source_reference="fixed-source",
        )


def test_golden_dataset_rejects_duplicate_case_ids_and_non_semantic_versions() -> None:
    """사례 식별자와 버전이 모호하면 회귀 비교의 기준이 될 수 없다."""
    case = GoldenCase(
        case_id="case-a",
        query="질의",
        category="test",
        expected_response="answer",
        relevant_document_ids=("policy-a",),
        label_rationale="검토 근거",
        source_reference="fixed-source",
    )

    with pytest.raises(GoldenDatasetError, match="case ids"):
        GoldenDataset("fixed", "1.0.0", (case, case))
    with pytest.raises(GoldenDatasetError, match="MAJOR.MINOR.PATCH"):
        GoldenDataset("fixed", "version-one", (case,))
