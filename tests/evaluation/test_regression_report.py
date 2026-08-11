"""Volume 10의 고정 기준선·후보 회귀 리포트 계약을 검증한다."""
from __future__ import annotations

import math

import pytest

from ai_platform.evaluation import (
    FIXED_BASELINE_SNAPSHOT,
    FIXED_CANDIDATE_SNAPSHOT,
    FIXED_REGRESSION_POLICIES,
    EvaluationSnapshot,
    MetricValue,
    RegressionEvaluationError,
    RegressionPolicy,
    compare_snapshots,
)


def _snapshot(*, value: float = 0.8) -> EvaluationSnapshot:
    return EvaluationSnapshot(
        dataset_id="fixed-dataset",
        dataset_version="1.0.0",
        case_ids=("case-a", "case-b"),
        metrics=(MetricValue("quality", value), MetricValue("cost_micro_usd", 100)),
    )


def _policies() -> tuple[RegressionPolicy, ...]:
    return (
        RegressionPolicy("quality", "higher_is_better", allowed_degradation=0.01),
        RegressionPolicy("cost_micro_usd", "lower_is_better"),
    )


def test_report_rejects_quality_regression_even_when_cost_improves() -> None:
    """비용 개선이 무허용 품질 하락을 상쇄해 승인하지 못하게 한다."""
    candidate = EvaluationSnapshot(
        dataset_id="fixed-dataset",
        dataset_version="1.0.0",
        case_ids=("case-a", "case-b"),
        metrics=(MetricValue("quality", 0.75), MetricValue("cost_micro_usd", 90)),
    )

    report = compare_snapshots(_snapshot(), candidate, _policies())

    assert report.dataset_id == "fixed-dataset"
    assert report.dataset_version == "1.0.0"
    assert report.cases_evaluated == 2
    assert report.is_approved is False
    assert tuple(result.status for result in report.metric_results) == ("regression", "improved")
    assert report.metric_results[0].delta == pytest.approx(-0.05)
    assert report.metric_results[0].allowed_degradation == pytest.approx(0.01)


def test_report_allows_a_boundary_degradation_and_preserves_policy_order() -> None:
    """허용 저하와 같은 값은 통과하며 출력 순서는 정책 순서로 고정한다."""
    candidate = EvaluationSnapshot(
        dataset_id="fixed-dataset",
        dataset_version="1.0.0",
        case_ids=("case-a", "case-b"),
        metrics=(MetricValue("quality", 0.79), MetricValue("cost_micro_usd", 100)),
    )

    report = compare_snapshots(_snapshot(), candidate, _policies())

    assert report.is_approved is True
    assert tuple(result.metric_id for result in report.metric_results) == (
        "quality",
        "cost_micro_usd",
    )
    assert tuple(result.status for result in report.metric_results) == (
        "within_tolerance",
        "within_tolerance",
    )


@pytest.mark.parametrize(
    "candidate",
    [
        EvaluationSnapshot(
            "other-dataset",
            "1.0.0",
            ("case-a", "case-b"),
            (MetricValue("quality", 0.8), MetricValue("cost_micro_usd", 100)),
        ),
        EvaluationSnapshot(
            "fixed-dataset",
            "2.0.0",
            ("case-a", "case-b"),
            (MetricValue("quality", 0.8), MetricValue("cost_micro_usd", 100)),
        ),
        EvaluationSnapshot(
            "fixed-dataset",
            "1.0.0",
            ("case-b", "case-a"),
            (MetricValue("quality", 0.8), MetricValue("cost_micro_usd", 100)),
        ),
    ],
)
def test_report_rejects_a_changed_dataset_version_or_case_order(
    candidate: EvaluationSnapshot,
) -> None:
    """다른 평가 계약의 수치를 기준선과 직접 비교하지 않는다."""
    with pytest.raises(RegressionEvaluationError, match="must match"):
        compare_snapshots(_snapshot(), candidate, _policies())


def test_report_rejects_missing_metric_policy_or_candidate_metric() -> None:
    """모든 비교 지표에는 후보 값과 정확히 하나의 정책이 필요하다."""
    missing_candidate_metric = EvaluationSnapshot(
        "fixed-dataset", "1.0.0", ("case-a", "case-b"), (MetricValue("quality", 0.8),)
    )

    with pytest.raises(RegressionEvaluationError, match="metric ids must match"):
        compare_snapshots(_snapshot(), missing_candidate_metric, _policies())
    with pytest.raises(RegressionEvaluationError, match="policies must match"):
        compare_snapshots(
            _snapshot(),
            _snapshot(),
            (RegressionPolicy("quality", "higher_is_better"),),
        )


def test_fixed_candidate_report_rejects_retrieval_regression_despite_other_improvements() -> None:
    """다섯 고정 사례의 교육용 후보는 회수율 하락 때문에 승인되지 않는다."""
    report = compare_snapshots(
        FIXED_BASELINE_SNAPSHOT, FIXED_CANDIDATE_SNAPSHOT, FIXED_REGRESSION_POLICIES
    )

    assert report.cases_evaluated == 5
    assert report.is_approved is False
    assert tuple(result.status for result in report.metric_results) == (
        "regression",
        "within_tolerance",
        "improved",
        "improved",
        "improved",
    )
    assert report.metric_results[0].baseline_value == pytest.approx(0.75)
    assert report.metric_results[0].candidate_value == pytest.approx(0.5)
    assert report.metric_results[3].candidate_value == pytest.approx(300)
    assert report.metric_results[4].candidate_value == pytest.approx(5080)


@pytest.mark.parametrize("value", [math.nan, math.inf, True])
def test_metric_values_reject_non_finite_or_boolean_values(value: float) -> None:
    """NaN·무한대·불리언은 정렬 가능한 수치 비교로 위장할 수 없다."""
    with pytest.raises(RegressionEvaluationError, match="finite number"):
        MetricValue("quality", value)


def test_policy_rejects_invalid_direction_and_negative_tolerance() -> None:
    """방향과 허용 저하는 명시적이고 유한한 계약이어야 한다."""
    with pytest.raises(RegressionEvaluationError, match="direction"):
        RegressionPolicy("quality", "sideways")  # type: ignore[arg-type]
    with pytest.raises(RegressionEvaluationError, match="non-negative"):
        RegressionPolicy("quality", "higher_is_better", -0.01)
