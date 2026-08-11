"""Volume 10 고정 골든 데이터셋과 검색 품질 지표를 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.evaluation import (
    FIXED_RETRIEVAL_CASES,
    FIXED_RETRIEVAL_RESULTS_AT_3,
    RetrievalCase,
    RetrievalEvaluationError,
    evaluate_retrieval,
    evaluate_retrieval_cases,
)


def test_fixed_golden_dataset_has_reproducible_retrieval_metrics() -> None:
    """문서 순위가 같으면 어떤 실행에서도 같은 품질 지표가 나와야 한다."""
    metrics = evaluate_retrieval(FIXED_RETRIEVAL_CASES, FIXED_RETRIEVAL_RESULTS_AT_3, k=3)

    assert metrics.cases_evaluated == 4
    assert metrics.recall_at_k == pytest.approx(0.75)
    assert metrics.precision_at_k == pytest.approx(1 / 3)
    assert metrics.hit_rate_at_k == pytest.approx(0.75)
    assert metrics.mean_reciprocal_rank == pytest.approx(0.625)
    assert metrics.ndcg_at_k == pytest.approx(0.6577324384)


def test_retrieval_metrics_penalize_empty_and_late_ranked_results() -> None:
    """Recall, Precision, Hit Rate, MRR, NDCG의 순위 차이를 분리해 확인한다."""
    cases = (
        RetrievalCase("first", "첫 질의", ("document-a",)),
        RetrievalCase("late", "둘째 질의", ("document-b",)),
    )
    results = {
        "first": ("document-a",),
        "late": ("document-x", "document-y", "document-b"),
    }

    metrics = evaluate_retrieval(cases, results, k=3)

    assert metrics.recall_at_k == pytest.approx(1.0)
    assert metrics.precision_at_k == pytest.approx(1 / 3)
    assert metrics.hit_rate_at_k == pytest.approx(1.0)
    assert metrics.mean_reciprocal_rank == pytest.approx(2 / 3)
    assert metrics.ndcg_at_k == pytest.approx((1 + 1 / 2) / 2)


def test_case_metrics_expose_fixed_failure_and_rank_tradeoffs() -> None:
    """사례별 결과는 평균만으로 숨겨지는 누락과 첫 정답 순위를 보여 준다."""
    case_metrics = evaluate_retrieval_cases(
        FIXED_RETRIEVAL_CASES, FIXED_RETRIEVAL_RESULTS_AT_3, k=3
    )

    assert tuple(metric.case_id for metric in case_metrics) == (
        "access-reset",
        "expense-receipt",
        "incident-response",
        "benefits-enrollment",
    )
    assert case_metrics[1].first_relevant_rank == 2
    assert case_metrics[1].relevant_document_ids_retrieved == ("finance-expense",)
    assert case_metrics[2].relevant_document_ids_retrieved == (
        "operations-runbook",
        "security-incident",
    )
    assert case_metrics[2].precision_at_k == pytest.approx(2 / 3)
    assert case_metrics[3].hit_at_k is False
    assert case_metrics[3].first_relevant_rank is None
    assert case_metrics[3].recall_at_k == pytest.approx(0.0)


@pytest.mark.parametrize("k", [0, -1, True, "3"])
def test_retrieval_metrics_reject_invalid_cutoff(k: object) -> None:
    """모호한 절단 순위를 조용히 변환하지 않는다."""
    with pytest.raises(RetrievalEvaluationError, match="positive integer"):
        evaluate_retrieval(FIXED_RETRIEVAL_CASES, FIXED_RETRIEVAL_RESULTS_AT_3, k=k)  # type: ignore[arg-type]


def test_retrieval_metrics_reject_missing_or_unexpected_case_results() -> None:
    """평가 사례가 일부 빠지면 평균 점수가 왜곡될 수 있으므로 실패시킨다."""
    incomplete_results = {"access-reset": ("identity-access",)}

    with pytest.raises(RetrievalEvaluationError, match="missing="):
        evaluate_retrieval(FIXED_RETRIEVAL_CASES, incomplete_results, k=3)


def test_retrieval_metrics_reject_duplicate_ranked_documents() -> None:
    """같은 정답 문서를 여러 순위에 넣어 점수를 부풀리는 입력을 차단한다."""
    results = dict(FIXED_RETRIEVAL_RESULTS_AT_3)
    results["access-reset"] = ("identity-access", "identity-access")

    with pytest.raises(RetrievalEvaluationError, match="must be unique"):
        evaluate_retrieval(FIXED_RETRIEVAL_CASES, results, k=3)


def test_retrieval_metrics_reject_a_single_string_as_ranked_results() -> None:
    """문자열을 문서 ID 목록으로 잘못 해석해 문자 단위 점수를 내지 않는다."""
    results = dict(FIXED_RETRIEVAL_RESULTS_AT_3)
    results["access-reset"] = "identity-access"

    with pytest.raises(RetrievalEvaluationError, match="sequence of strings"):
        evaluate_retrieval(FIXED_RETRIEVAL_CASES, results, k=3)
