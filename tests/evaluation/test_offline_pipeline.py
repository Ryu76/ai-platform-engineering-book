"""Volume 10 미니 프로젝트의 고정 오프라인 평가 파이프라인을 검증한다."""
from __future__ import annotations

from dataclasses import replace

import pytest

from ai_platform.evaluation import (
    FIXED_BASELINE_EVALUATION_INPUT,
    FIXED_CANDIDATE_EVALUATION_INPUT,
    FIXED_REGRESSION_POLICIES,
    OfflineEvaluationError,
    RetrievalCase,
    compare_snapshots,
    format_offline_evaluation_report,
    run_offline_evaluation,
)


def test_fixed_pipeline_runs_all_domains_and_preserves_no_answer_separation() -> None:
    """기준선은 다섯 전체 사례와 네 검색 사례의 고정 수치를 함께 계산한다."""
    run = run_offline_evaluation(FIXED_BASELINE_EVALUATION_INPUT)

    assert run.dataset_id == "volume10-support-policy"
    assert run.dataset_version == "1.0.0"
    assert run.case_ids == (
        "access-reset",
        "expense-receipt",
        "incident-response",
        "benefits-enrollment",
        "office-parking",
    )
    assert run.retrieval_metrics.cases_evaluated == 4
    assert run.retrieval_metrics.recall_at_k == pytest.approx(0.75)
    assert run.answer_metrics.answer_accuracy == pytest.approx(0.8)
    assert run.workflow_metrics.router_accuracy == pytest.approx(0.8)
    assert run.workflow_metrics.agent_task_success_rate == pytest.approx(0.6)
    assert run.usage_metrics.p95_latency_ms == 340
    assert run.usage_metrics.total_tokens == 1240
    assert run.usage_metrics.total_cost_micro_usd == 5240


def test_fixed_candidate_pipeline_uses_its_run_snapshots_for_regression_rejection() -> None:
    """전체 파이프라인에서 얻은 스냅샷도 Recall 회귀로 후보를 거부한다."""
    baseline = run_offline_evaluation(FIXED_BASELINE_EVALUATION_INPUT)
    candidate = run_offline_evaluation(FIXED_CANDIDATE_EVALUATION_INPUT)

    report = compare_snapshots(
        baseline.regression_snapshot(),
        candidate.regression_snapshot(),
        FIXED_REGRESSION_POLICIES,
    )

    assert candidate.retrieval_metrics.recall_at_k == pytest.approx(0.5)
    assert candidate.workflow_metrics.agent_task_success_rate == pytest.approx(0.8)
    assert candidate.usage_metrics.p95_latency_ms == 300
    assert candidate.usage_metrics.total_tokens == 1220
    assert candidate.usage_metrics.total_cost_micro_usd == 5080
    assert report.is_approved is False
    assert report.metric_results[0].status == "regression"


def test_pipeline_rejects_reordered_full_case_contract() -> None:
    """답변·워크플로·사용량에서 사례 순서를 바꾸어 선택 편향을 만들 수 없다."""
    with pytest.raises(OfflineEvaluationError, match="answer case ids and order"):
        replace(
            FIXED_BASELINE_EVALUATION_INPUT,
            answer_cases=tuple(reversed(FIXED_BASELINE_EVALUATION_INPUT.answer_cases)),
        )


def test_pipeline_rejects_retrieval_case_outside_full_contract() -> None:
    """검색 부분집합은 전체 골든 사례 집합 밖의 사례를 넣을 수 없다."""
    unexpected_case = RetrievalCase("unknown", "고정되지 않은 질의", ("unknown-doc",))
    with pytest.raises(OfflineEvaluationError, match="subset of case ids"):
        replace(
            FIXED_BASELINE_EVALUATION_INPUT,
            retrieval_cases=(unexpected_case,),
            ranked_document_ids_by_case={"unknown": ("unknown-doc",)},
        )


def test_text_report_is_deterministic_and_includes_rejection_reason() -> None:
    """교육용 리포트는 단위·순서·회귀 원인을 외부 상태 없이 고정한다."""
    baseline = run_offline_evaluation(FIXED_BASELINE_EVALUATION_INPUT)
    candidate = run_offline_evaluation(FIXED_CANDIDATE_EVALUATION_INPUT)
    regression_report = compare_snapshots(
        baseline.regression_snapshot(),
        candidate.regression_snapshot(),
        FIXED_REGRESSION_POLICIES,
    )

    text = format_offline_evaluation_report(baseline, candidate, regression_report)

    assert text.splitlines()[:11] == [
        "Dataset: volume10-support-policy@1.0.0",
        "Evaluation cases: 5",
        "Retrieval cases: 4",
        "Baseline:",
        "  Recall@3: 0.750000",
        "  Answer accuracy: 0.800000",
        "  Router accuracy: 0.800000",
        "  Agent task success rate: 0.600000",
        "  P95 latency (ms): 340",
        "  Total tokens: 1240",
        "  Total cost (USD): 0.005240",
    ]
    assert "Regression decision: REJECT" in text
    assert "retrieval.recall_at_3: status=regression; delta=-0.250000" in text
