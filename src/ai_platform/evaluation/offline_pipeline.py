"""고정 입력을 한 번에 실행하고 읽을 수 있는 오프라인 평가 리포트를 만든다."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ai_platform.evaluation.answer_metrics import (
    AnswerCase,
    AnswerMetrics,
    RecordedAnswer,
    evaluate_answers,
)
from ai_platform.evaluation.regression_report import (
    EvaluationSnapshot,
    MetricValue,
    RegressionReport,
)
from ai_platform.evaluation.retrieval_metrics import (
    RetrievalCase,
    RetrievalMetrics,
    evaluate_retrieval,
)
from ai_platform.evaluation.usage_metrics import (
    RecordedUsage,
    TokenPricing,
    UsageCase,
    UsageMetrics,
    evaluate_usage,
)
from ai_platform.evaluation.workflow_metrics import (
    RecordedWorkflow,
    WorkflowCase,
    WorkflowMetrics,
    evaluate_workflows,
)


class OfflineEvaluationError(ValueError):
    """오프라인 평가 입력이 하나의 고정 골든 계약을 따르지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class OfflineEvaluationInput:
    """한 데이터셋 버전의 검색·답변·워크플로·사용량 고정 입력을 묶는다."""

    dataset_id: str
    dataset_version: str
    case_ids: tuple[str, ...]
    retrieval_cases: Sequence[RetrievalCase]
    ranked_document_ids_by_case: Mapping[str, Sequence[str]]
    answer_cases: Sequence[AnswerCase]
    recorded_answers_by_case: Mapping[str, RecordedAnswer]
    workflow_cases: Sequence[WorkflowCase]
    recorded_workflows_by_case: Mapping[str, RecordedWorkflow]
    usage_cases: Sequence[UsageCase]
    recorded_usage_by_case: Mapping[str, RecordedUsage]
    token_pricing: TokenPricing
    retrieval_k: int = 3

    def __post_init__(self) -> None:
        """부분 제출, ID 순서 변경, no-answer의 검색 분모 혼입을 예방한다."""
        _validate_case_ids(self.case_ids)
        _validate_full_case_contract("answer", self.case_ids, self.answer_cases)
        _validate_full_case_contract("workflow", self.case_ids, self.workflow_cases)
        _validate_full_case_contract("usage", self.case_ids, self.usage_cases)
        retrieval_case_ids = tuple(case.case_id for case in self.retrieval_cases)
        if not retrieval_case_ids:
            raise OfflineEvaluationError("retrieval case ids must not be empty")
        if len(set(retrieval_case_ids)) != len(retrieval_case_ids):
            raise OfflineEvaluationError("retrieval case ids must be unique")
        if not set(retrieval_case_ids).issubset(self.case_ids):
            raise OfflineEvaluationError("retrieval case ids must be a subset of case ids")
        if self.retrieval_k < 1 or isinstance(self.retrieval_k, bool):
            raise OfflineEvaluationError("retrieval_k must be a positive integer")
        _require_non_empty("dataset_id", self.dataset_id)
        _require_non_empty("dataset_version", self.dataset_version)


@dataclass(frozen=True, slots=True)
class OfflineEvaluationRun:
    """한 고정 입력에서 계산한 전 평가 영역의 결정론적 결과다."""

    dataset_id: str
    dataset_version: str
    case_ids: tuple[str, ...]
    retrieval_metrics: RetrievalMetrics
    answer_metrics: AnswerMetrics
    workflow_metrics: WorkflowMetrics
    usage_metrics: UsageMetrics

    def regression_snapshot(self) -> EvaluationSnapshot:
        """현재 회귀 게이트가 비교하는 다섯 지표의 스냅샷을 반환한다."""
        return EvaluationSnapshot(
            dataset_id=self.dataset_id,
            dataset_version=self.dataset_version,
            case_ids=self.case_ids,
            metrics=(
                MetricValue("retrieval.recall_at_3", self.retrieval_metrics.recall_at_k),
                MetricValue("answer.answer_accuracy", self.answer_metrics.answer_accuracy),
                MetricValue(
                    "workflow.agent_task_success_rate",
                    self.workflow_metrics.agent_task_success_rate,
                ),
                MetricValue("usage.p95_latency_ms", self.usage_metrics.p95_latency_ms),
                MetricValue(
                    "usage.total_cost_micro_usd", self.usage_metrics.total_cost_micro_usd
                ),
            ),
        )


def run_offline_evaluation(inputs: OfflineEvaluationInput) -> OfflineEvaluationRun:
    """외부 호출 없이 하나의 고정 계약의 모든 평가 지표를 계산한다."""
    retrieval_metrics = evaluate_retrieval(
        inputs.retrieval_cases,
        inputs.ranked_document_ids_by_case,
        k=inputs.retrieval_k,
    )
    answer_metrics = evaluate_answers(inputs.answer_cases, inputs.recorded_answers_by_case)
    workflow_metrics = evaluate_workflows(
        inputs.workflow_cases, inputs.recorded_workflows_by_case
    )
    usage_metrics = evaluate_usage(
        inputs.usage_cases, inputs.recorded_usage_by_case, inputs.token_pricing)
    return OfflineEvaluationRun(
        dataset_id=inputs.dataset_id,
        dataset_version=inputs.dataset_version,
        case_ids=inputs.case_ids,
        retrieval_metrics=retrieval_metrics,
        answer_metrics=answer_metrics,
        workflow_metrics=workflow_metrics,
        usage_metrics=usage_metrics,
    )


def format_offline_evaluation_report(
    baseline: OfflineEvaluationRun,
    candidate: OfflineEvaluationRun,
    regression_report: RegressionReport,
) -> str:
    """기준선·후보·회귀 결정을 안정된 줄 순서의 텍스트로 렌더링한다."""
    _validate_report_contract(baseline, candidate, regression_report)
    return "\n".join(
        (
            f"Dataset: {baseline.dataset_id}@{baseline.dataset_version}",
            f"Evaluation cases: {len(baseline.case_ids)}",
            f"Retrieval cases: {baseline.retrieval_metrics.cases_evaluated}",
            "Baseline:",
            *_format_run_metrics(baseline),
            "Candidate:",
            *_format_run_metrics(candidate),
            f"Regression decision: {'APPROVE' if regression_report.is_approved else 'REJECT'}",
            *(
                f"{result.metric_id}: status={result.status}; delta={result.delta:+.6f}"
                for result in regression_report.metric_results
            ),
        )
    )


def _format_run_metrics(run: OfflineEvaluationRun) -> tuple[str, ...]:
    """한 실행 결과의 핵심 지표를 교육용으로 고정된 순서와 단위로 포맷한다."""
    return (
        f"  Recall@3: {run.retrieval_metrics.recall_at_k:.6f}",
        f"  Answer accuracy: {run.answer_metrics.answer_accuracy:.6f}",
        f"  Router accuracy: {run.workflow_metrics.router_accuracy:.6f}",
        f"  Agent task success rate: {run.workflow_metrics.agent_task_success_rate:.6f}",
        f"  P95 latency (ms): {run.usage_metrics.p95_latency_ms}",
        f"  Total tokens: {run.usage_metrics.total_tokens}",
        f"  Total cost (USD): {run.usage_metrics.total_cost_micro_usd / 1_000_000:.6f}",
    )


def _validate_report_contract(
    baseline: OfflineEvaluationRun,
    candidate: OfflineEvaluationRun,
    regression_report: RegressionReport,
) -> None:
    """보고서의 세 부분이 같은 데이터셋·버전·전체 사례 계약을 사용하게 한다."""
    if (
        baseline.dataset_id != candidate.dataset_id
        or baseline.dataset_id != regression_report.dataset_id
    ):
        raise OfflineEvaluationError("report dataset ids must match")
    if (
        baseline.dataset_version != candidate.dataset_version
        or baseline.dataset_version != regression_report.dataset_version
    ):
        raise OfflineEvaluationError("report dataset versions must match")
    if len(baseline.case_ids) != regression_report.cases_evaluated:
        raise OfflineEvaluationError("report case count must match baseline case ids")


def _validate_case_ids(case_ids: tuple[str, ...]) -> None:
    """데이터셋 사례 순서는 비어 있지 않고 중복이 없어야 한다."""
    if not case_ids:
        raise OfflineEvaluationError("case ids must not be empty")
    if any(not isinstance(case_id, str) or not case_id.strip() for case_id in case_ids):
        raise OfflineEvaluationError("case ids must contain non-empty strings")
    if len(set(case_ids)) != len(case_ids):
        raise OfflineEvaluationError("case ids must be unique")


def _validate_full_case_contract(
    label: str, case_ids: tuple[str, ...], cases: Sequence[object]) -> None:
    """답변·워크플로·사용량은 no-answer를 포함한 전체 사례·순서를 공유해야 한다."""
    observed_case_ids = tuple(getattr(case, "case_id", None) for case in cases)
    if observed_case_ids != case_ids:
        raise OfflineEvaluationError(f"{label} case ids and order must match case ids")


def _require_non_empty(field_name: str, value: str) -> None:
    """데이터셋 ID와 버전의 빈 값·비문자열을 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise OfflineEvaluationError(f"{field_name} must be a non-empty string")
