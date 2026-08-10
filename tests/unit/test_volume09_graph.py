"""Volume 09 오프라인 상태형 Workflow의 안전 계약을 검사한다."""
from __future__ import annotations

import pytest

from ai_platform.graph import (
    ActionKind,
    DeterministicWorkflow,
    PlannerDeveloperReviewerWorkflow,
    RetryPlan,
    RetryWorkflow,
    ReviewDecision,
    RoutedWorkflow,
    RouteKind,
    RouterDecision,
    WorkflowState,
    WorkflowStatus,
)


def test_safe_action_reaches_end_without_human_approval() -> None:
    """읽기 작업은 START부터 END까지 결정론적으로 완료한다."""
    workflow = DeterministicWorkflow()

    state = workflow.invoke(run_id="safe-001", task="로컬 문서를 읽는다", action=ActionKind.READ)

    assert state.status is WorkflowStatus.COMPLETED
    assert state.approval_required is False
    assert state.approval_granted is None
    assert state.result == "오프라인 시뮬레이션 완료: read / 로컬 문서를 읽는다"
    assert [event.node for event in state.events] == ["plan", "approval", "execute"]


def test_risky_action_interrupts_before_execution_and_can_resume_after_approval() -> None:
    """배포는 명시적 사람 승인 전에는 결과를 만들거나 실행하지 않는다."""
    workflow = DeterministicWorkflow()

    waiting = workflow.invoke(
        run_id="deploy-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.result is None
    assert waiting.approval_granted is None
    assert [event.node for event in waiting.events] == ["plan", "approval"]
    assert workflow.checkpoint(run_id="deploy-001") == waiting

    completed = workflow.resume(run_id="deploy-001", approved=True)

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.approval_granted is True
    assert completed.result == "오프라인 시뮬레이션 완료: deploy / 학습용 배포를 준비한다"
    assert [event.node for event in completed.events] == ["plan", "approval", "approval", "execute"]


def test_rejected_risky_action_stops_without_execution() -> None:
    """거절 결정은 END의 rejected 상태로 끝나며 execute Node에 닿지 않는다."""
    workflow = DeterministicWorkflow()
    workflow.invoke(run_id="delete-001", task="임시 파일을 삭제한다", action=ActionKind.DELETE)

    rejected = workflow.resume(run_id="delete-001", approved=False)

    assert rejected.status is WorkflowStatus.REJECTED
    assert rejected.approval_granted is False
    assert rejected.result is None
    assert [event.node for event in rejected.events] == ["plan", "approval", "approval"]


def test_resume_requires_an_existing_waiting_checkpoint() -> None:
    """없는 실행 ID나 완료된 Workflow는 재개할 수 없다."""
    workflow = DeterministicWorkflow()

    with pytest.raises(KeyError, match="checkpoint not found"):
        workflow.resume(run_id="missing", approved=True)

    workflow.invoke(run_id="complete-001", task="로컬 문서를 읽는다", action=ActionKind.READ)
    with pytest.raises(ValueError, match="waiting state"):
        workflow.resume(run_id="complete-001", approved=True)


def test_state_rejects_empty_task() -> None:
    """상태 입력 검증이 빈 작업을 Node까지 전달하지 않는다."""
    with pytest.raises(ValueError, match="task must not be empty"):
        WorkflowState.start(task="  ", action=ActionKind.READ)


def test_high_confidence_router_decision_uses_selected_specialist_node() -> None:
    """신뢰도 높은 Router 입력은 조건 Edge로 개발 Node를 선택해 완료한다."""
    workflow = RoutedWorkflow(confidence_threshold=0.80)

    completed = workflow.invoke(
        run_id="route-001",
        task="로컬 문자열을 정규화한다",
        action=ActionKind.TRANSFORM,
        router_decision=RouterDecision(route=RouteKind.DEVELOPMENT, confidence=0.92),
    )

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.selected_route is RouteKind.DEVELOPMENT
    assert completed.result == "오프라인 시뮬레이션 완료: transform / 로컬 문자열을 정규화한다"
    assert [event.node for event in completed.events] == [
        "plan",
        "router",
        "development",
        "approval",
        "execute",
    ]


def test_missing_router_decision_waits_for_human_route_review_then_completes() -> None:
    """Router 입력이 없으면 전문 Node나 execute 전에 사람 경로 검토에서 중단한다."""
    workflow = RoutedWorkflow()

    waiting = workflow.invoke(
        run_id="route-missing-001",
        task="로컬 문서의 근거를 조사한다",
        action=ActionKind.READ,
        router_decision=None,
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_ROUTE_REVIEW
    assert waiting.selected_route is None
    assert waiting.result is None
    assert [event.node for event in waiting.events] == ["plan", "router"]

    completed = workflow.review_route(run_id="route-missing-001", route=RouteKind.RESEARCH)

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.selected_route is RouteKind.RESEARCH
    assert [event.node for event in completed.events] == [
        "plan",
        "router",
        "route_review",
        "research",
        "approval",
        "execute",
    ]


def test_low_confidence_risky_route_needs_route_review_and_separate_approval() -> None:
    """낮은 신뢰도와 위험 작업은 사람 경로 검토와 실행 승인을 모두 요구한다."""
    workflow = RoutedWorkflow(confidence_threshold=0.80)
    waiting = workflow.invoke(
        run_id="route-risky-001",
        task="학습용 메시지를 전송한다",
        action=ActionKind.SEND,
        router_decision=RouterDecision(route=RouteKind.REVIEW, confidence=0.79),
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_ROUTE_REVIEW
    assert "execute" not in [event.node for event in waiting.events]

    awaiting_approval = workflow.review_route(
        run_id="route-risky-001", route=RouteKind.REVIEW
    )

    assert awaiting_approval.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert awaiting_approval.approval_granted is None
    assert "execute" not in [event.node for event in awaiting_approval.events]

    rejected = workflow.resume(run_id="route-risky-001", approved=False)

    assert rejected.status is WorkflowStatus.REJECTED
    assert "execute" not in [event.node for event in rejected.events]


def test_router_decision_rejects_invalid_confidence() -> None:
    """Router 입력은 Node 실행 전에 유효한 신뢰도 범위를 강제한다."""
    with pytest.raises(ValueError, match="router confidence"):
        RouterDecision(route=RouteKind.RESEARCH, confidence=1.01)


def test_planner_developer_reviewer_safe_workflow_completes_in_role_order() -> None:
    """검토를 통과한 안전 작업은 고정된 역할 순서로 오프라인 완료한다."""
    workflow = PlannerDeveloperReviewerWorkflow()

    completed = workflow.invoke(
        run_id="pdr-safe-001",
        task="로컬 문자열을 정규화하는 초안을 검토한다",
        action=ActionKind.TRANSFORM,
        review_decision=ReviewDecision(approved=True, feedback="테스트 가능한 초안입니다."),
    )

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.review_approved is True
    assert completed.approval_granted is None
    assert [event.node for event in completed.events] == [
        "plan",
        "developer",
        "reviewer",
        "approval",
        "execute",
    ]


def test_reviewer_rejection_ends_before_approval_and_execution() -> None:
    """Reviewer 거절은 실행 권한이나 execute Node 없이 별도 END로 끝난다."""
    workflow = PlannerDeveloperReviewerWorkflow()

    rejected = workflow.invoke(
        run_id="pdr-review-rejected-001",
        task="학습용 변경 초안을 검토한다",
        action=ActionKind.DEPLOY,
        review_decision=ReviewDecision(approved=False, feedback="영향 범위가 빠졌습니다."),
    )

    assert rejected.status is WorkflowStatus.REVIEW_REJECTED
    assert rejected.review_approved is False
    assert rejected.approval_granted is None
    assert rejected.result is None
    assert [event.node for event in rejected.events] == ["plan", "developer", "reviewer"]


def test_risky_reviewed_workflow_requires_separate_human_approval() -> None:
    """Reviewer 통과는 위험 작업의 사람 실행 승인을 대체하지 않는다."""
    workflow = PlannerDeveloperReviewerWorkflow()
    waiting = workflow.invoke(
        run_id="pdr-risky-001",
        task="학습용 배포 초안을 검토한다",
        action=ActionKind.DEPLOY,
        review_decision=ReviewDecision(approved=True, feedback="롤백 절차가 명확합니다."),
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.review_approved is True
    assert waiting.approval_granted is None
    assert [event.node for event in waiting.events] == [
        "plan",
        "developer",
        "reviewer",
        "approval",
    ]
    assert "execute" not in [event.node for event in waiting.events]

    completed = workflow.resume(run_id="pdr-risky-001", approved=True)

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.approval_granted is True
    assert [event.node for event in completed.events] == [
        "plan",
        "developer",
        "reviewer",
        "approval",
        "approval",
        "execute",
    ]


def test_review_decision_rejects_blank_audit_fields() -> None:
    """Reviewer 판정은 재현 가능한 감사 근거와 출처를 요구한다."""
    with pytest.raises(ValueError, match="review feedback"):
        ReviewDecision(approved=True, feedback=" ")

    with pytest.raises(ValueError, match="review source"):
        ReviewDecision(approved=True, feedback="통과", source=" ")


def test_retry_workflow_recovers_within_its_fixed_retry_limit() -> None:
    """첫 실패 뒤 Error Node가 허용한 한 번의 재시도로 안전 작업을 완료한다."""
    workflow = RetryWorkflow()

    completed = workflow.invoke(
        run_id="retry-recover-001",
        task="로컬 문자열을 변환한다",
        action=ActionKind.TRANSFORM,
        retry_plan=RetryPlan(failures_before_success=1, max_retries=1),
    )

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.attempt_count == 2
    assert [event.node for event in completed.events] == [
        "plan",
        "approval",
        "execute",
        "error",
        "execute",
    ]


def test_retry_workflow_ends_at_error_node_when_retry_limit_is_exhausted() -> None:
    """실패가 상한을 넘으면 추가 시도 없이 FAILED END로 종료한다."""
    failed = RetryWorkflow().invoke(
        run_id="retry-failed-001",
        task="로컬 문자열을 변환한다",
        action=ActionKind.TRANSFORM,
        retry_plan=RetryPlan(failures_before_success=2, max_retries=1),
    )

    assert failed.status is WorkflowStatus.FAILED
    assert failed.result is None
    assert failed.attempt_count == 2
    assert [event.node for event in failed.events] == [
        "plan",
        "approval",
        "execute",
        "error",
        "execute",
        "error",
    ]


def test_retry_workflow_requires_approval_before_a_risky_attempt_or_retry() -> None:
    """위험 작업은 재시도 계획이 있어도 승인 전에는 실행 시도를 시작하지 않는다."""
    workflow = RetryWorkflow()
    waiting = workflow.invoke(
        run_id="retry-risky-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
        retry_plan=RetryPlan(failures_before_success=1, max_retries=1),
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.attempt_count == 0
    assert "execute" not in [event.node for event in waiting.events]

    rejected = workflow.resume(run_id="retry-risky-001", approved=False)

    assert rejected.status is WorkflowStatus.REJECTED
    assert rejected.attempt_count == 0
    assert "execute" not in [event.node for event in rejected.events]


def test_retry_plan_rejects_negative_limits_and_blank_source() -> None:
    """재시도 입력은 재현 가능한 양수 범위와 감사 출처를 강제한다."""
    with pytest.raises(ValueError, match="failures_before_success"):
        RetryPlan(failures_before_success=-1, max_retries=0)

    with pytest.raises(ValueError, match="max_retries"):
        RetryPlan(failures_before_success=0, max_retries=-1)

    with pytest.raises(ValueError, match="retry source"):
        RetryPlan(failures_before_success=0, max_retries=0, source=" ")
