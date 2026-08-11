"""Volume 10의 고정 Router·Agent Task Success 평가 계약을 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.evaluation import (
    FIXED_GOLDEN_DATASET,
    FIXED_RECORDED_WORKFLOWS,
    FIXED_WORKFLOW_CASES,
    RecordedWorkflow,
    WorkflowCase,
    WorkflowEvaluationError,
    evaluate_workflow_cases,
    evaluate_workflows,
)


def test_fixed_workflows_have_reproducible_router_and_task_metrics() -> None:
    """같은 고정 선택·작업 기록은 항상 동일한 품질 기준선을 만든다."""
    metrics = evaluate_workflows(FIXED_WORKFLOW_CASES, FIXED_RECORDED_WORKFLOWS)

    assert metrics.cases_evaluated == 5
    assert metrics.router_accuracy == pytest.approx(0.8)
    assert metrics.agent_task_success_rate == pytest.approx(0.6)


def test_workflow_cases_share_the_versioned_golden_case_ids() -> None:
    """Router·Agent 평가가 다른 사례 집합으로 기준선을 바꾸지 않게 한다."""
    assert tuple(case.case_id for case in FIXED_WORKFLOW_CASES) == tuple(
        case.case_id for case in FIXED_GOLDEN_DATASET.cases
    )


def test_case_metrics_expose_missing_tasks_and_no_answer_route_failure() -> None:
    """평균이 숨기는 미완료 작업과 no-answer 라우팅·행동 실패를 확인한다."""
    case_metrics = evaluate_workflow_cases(FIXED_WORKFLOW_CASES, FIXED_RECORDED_WORKFLOWS)

    assert tuple(metric.case_id for metric in case_metrics) == (
        "access-reset",
        "expense-receipt",
        "incident-response",
        "benefits-enrollment",
        "office-parking",
    )
    assert case_metrics[3].route_is_correct is True
    assert case_metrics[3].task_is_successful is False
    assert case_metrics[3].missing_task_ids == (
        "provide-enrollment-window-and-application-flow",
    )
    assert case_metrics[4].route_is_correct is False
    assert case_metrics[4].response_matches_expectation is False
    assert case_metrics[4].task_is_successful is False
    assert case_metrics[4].unexpected_task_ids == ("issue-parking-pass",)


def test_workflow_metrics_reject_missing_or_unexpected_records() -> None:
    """일부 성공 사례만 집계해 지표를 좋게 보이게 하는 입력을 거부한다."""
    incomplete = {"access-reset": FIXED_RECORDED_WORKFLOWS["access-reset"]}

    with pytest.raises(WorkflowEvaluationError, match="missing="):
        evaluate_workflows(FIXED_WORKFLOW_CASES, incomplete)


def test_workflow_metrics_reject_record_key_and_payload_case_id_mismatch() -> None:
    """사전 키와 기록 내부 ID가 다르면 다른 라벨로 측정하지 않는다."""
    workflows = dict(FIXED_RECORDED_WORKFLOWS)
    workflows["access-reset"] = RecordedWorkflow(
        case_id="expense-receipt",
        selected_route="identity",
        response_mode="answer",
        completed_task_ids=("verify-identity-and-reset-access",),
    )

    with pytest.raises(WorkflowEvaluationError, match="key and case_id"):
        evaluate_workflows(FIXED_WORKFLOW_CASES, workflows)


@pytest.mark.parametrize(
    ("expected_route", "expected_response", "tasks", "message"),
    [
        ("abstain", "answer", ("task-a",), "must not use"),
        ("identity", "abstain", (), "must use"),
        ("abstain", "abstain", ("task-a",), "must not define"),
        ("identity", "answer", (), "must define"),
    ],
)
def test_workflow_cases_reject_ambiguous_route_and_task_contracts(
    expected_route: str,
    expected_response: str,
    tasks: tuple[str, ...],
    message: str,
) -> None:
    """기대 응답·라우트·필수 작업의 모순을 조용히 계산하지 않는다."""
    with pytest.raises(WorkflowEvaluationError, match=message):
        WorkflowCase(
            case_id="case-a",
            expected_route=expected_route,
            expected_response=expected_response,  # type: ignore[arg-type]
            required_task_ids=tasks,
        )


def test_recorded_abstention_rejects_completed_tasks() -> None:
    """보류 응답이 외부 작업을 완료한 것처럼 기록되는 것을 막는다."""
    with pytest.raises(WorkflowEvaluationError, match="must not complete"):
        RecordedWorkflow("case-a", "abstain", "abstain", ("task-a",))
