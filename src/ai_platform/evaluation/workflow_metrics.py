"""고정 골든 계약에서 Router 선택과 Agent 작업 성공을 결정론적으로 평가한다."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ai_platform.evaluation.golden_dataset import ExpectedResponse


class WorkflowEvaluationError(ValueError):
    """Router·Agent 평가 입력이 고정 워크플로 계약을 위반할 때 발생한다."""


@dataclass(frozen=True, slots=True)
class WorkflowCase:
    """하나의 질의에 기대 라우트·행동·필수 작업을 고정한 평가 사례다."""

    case_id: str
    expected_route: str
    expected_response: ExpectedResponse
    required_task_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """no-answer와 라우트·작업 라벨의 모순을 평가 전에 차단한다."""
        _require_non_empty("case_id", self.case_id)
        _require_non_empty("expected_route", self.expected_route)
        _validate_identifiers("required task ids", self.required_task_ids)
        if self.expected_response not in {"answer", "abstain"}:
            raise WorkflowEvaluationError("expected_response must be 'answer' or 'abstain'")
        if self.expected_response == "answer" and self.expected_route == "abstain":
            raise WorkflowEvaluationError("answer cases must not use the abstain route")
        if self.expected_response == "answer" and not self.required_task_ids:
            raise WorkflowEvaluationError("answer cases must define at least one required task")
        if self.expected_response == "abstain" and self.expected_route != "abstain":
            raise WorkflowEvaluationError("abstain cases must use the abstain route")
        if self.expected_response == "abstain" and self.required_task_ids:
            raise WorkflowEvaluationError("abstain cases must not define required tasks")


@dataclass(frozen=True, slots=True)
class RecordedWorkflow:
    """라이브 Router·Agent 호출 없이 검토할 수 있는 선택·행동·작업 기록이다."""

    case_id: str
    selected_route: str
    response_mode: ExpectedResponse
    completed_task_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """빈 라우트와 보류 응답의 부수 작업을 허용하지 않는다."""
        _require_non_empty("case_id", self.case_id)
        _require_non_empty("selected_route", self.selected_route)
        _validate_identifiers("completed task ids", self.completed_task_ids)
        if self.response_mode not in {"answer", "abstain"}:
            raise WorkflowEvaluationError("response_mode must be 'answer' or 'abstain'")
        if self.response_mode == "abstain" and self.completed_task_ids:
            raise WorkflowEvaluationError("abstain workflows must not complete tasks")


@dataclass(frozen=True, slots=True)
class WorkflowCaseMetrics:
    """사례별 라우트 일치와 Agent 작업 성공·누락·예상 밖 작업을 보관한다."""

    case_id: str
    route_is_correct: bool
    response_matches_expectation: bool
    task_is_successful: bool
    missing_task_ids: tuple[str, ...]
    unexpected_task_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkflowMetrics:
    """고정 사례 전체에서 계산한 Router 정확도와 Agent Task Success다."""

    cases_evaluated: int
    router_accuracy: float
    agent_task_success_rate: float


def evaluate_workflows(
    cases: Sequence[WorkflowCase],
    recorded_workflows_by_case: Mapping[str, RecordedWorkflow],
) -> WorkflowMetrics:
    """완전한 고정 사례 집합에서 Router와 Agent 기준선을 집계한다."""
    case_metrics = evaluate_workflow_cases(cases, recorded_workflows_by_case)
    count = len(case_metrics)
    return WorkflowMetrics(
        cases_evaluated=count,
        router_accuracy=sum(metric.route_is_correct for metric in case_metrics) / count,
        agent_task_success_rate=sum(metric.task_is_successful for metric in case_metrics)
        / count,
    )


def evaluate_workflow_cases(
    cases: Sequence[WorkflowCase],
    recorded_workflows_by_case: Mapping[str, RecordedWorkflow],
) -> tuple[WorkflowCaseMetrics, ...]:
    """사례 순서대로 Router 선택 및 Agent 작업 실패 원인을 계산한다."""
    _validate_cases(cases)
    case_ids = {case.case_id for case in cases}
    recorded_case_ids = set(recorded_workflows_by_case)
    if case_ids != recorded_case_ids:
        missing = sorted(case_ids - recorded_case_ids)
        unexpected = sorted(recorded_case_ids - case_ids)
        raise WorkflowEvaluationError(
            "recorded workflows must match case ids; "
            f"missing={missing}, unexpected={unexpected}"
        )

    metrics: list[WorkflowCaseMetrics] = []
    for case in cases:
        workflow = recorded_workflows_by_case[case.case_id]
        if workflow.case_id != case.case_id:
            raise WorkflowEvaluationError(
                f"recorded workflow key and case_id must match for {case.case_id}"
            )
        required_tasks = set(case.required_task_ids)
        completed_tasks = set(workflow.completed_task_ids)
        missing_tasks = tuple(
            task_id for task_id in case.required_task_ids if task_id not in completed_tasks
        )
        unexpected_tasks = tuple(
            task_id for task_id in workflow.completed_task_ids if task_id not in required_tasks
        )
        response_matches = workflow.response_mode == case.expected_response
        metrics.append(
            WorkflowCaseMetrics(
                case_id=case.case_id,
                route_is_correct=workflow.selected_route == case.expected_route,
                response_matches_expectation=response_matches,
                task_is_successful=(
                    response_matches and not missing_tasks and not unexpected_tasks
                ),
                missing_task_ids=missing_tasks,
                unexpected_task_ids=unexpected_tasks,
            )
        )
    return tuple(metrics)


def _validate_cases(cases: Sequence[WorkflowCase]) -> None:
    """빈 평가와 중복 사례 ID를 차단한다."""
    if not cases:
        raise WorkflowEvaluationError("at least one workflow case is required")
    case_ids = tuple(case.case_id for case in cases)
    if len(set(case_ids)) != len(case_ids):
        raise WorkflowEvaluationError("workflow case ids must be unique")


def _require_non_empty(field_name: str, value: str) -> None:
    """문자열 식별자의 빈 값과 비문자열 값을 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise WorkflowEvaluationError(f"{field_name} must be a non-empty string")


def _validate_identifiers(field_name: str, identifiers: tuple[str, ...]) -> None:
    """작업 식별자는 중복 없는 비어 있지 않은 문자열이어야 한다."""
    if any(not isinstance(identifier, str) or not identifier.strip() for identifier in identifiers):
        raise WorkflowEvaluationError(f"{field_name} must be non-empty strings")
    if len(set(identifiers)) != len(identifiers):
        raise WorkflowEvaluationError(f"{field_name} must be unique")
