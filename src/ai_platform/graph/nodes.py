"""외부 부작용 없이 상태만 전이하는 Volume 09 학습용 Node."""
from __future__ import annotations

from ai_platform.graph.state import (
    ReviewDecision,
    RouteKind,
    RouterDecision,
    WorkflowState,
    WorkflowStatus,
)


def plan_node(state: WorkflowState) -> WorkflowState:
    """작업을 결정론적인 오프라인 계획으로 바꾼다."""
    if state.status is not WorkflowStatus.PENDING:
        raise ValueError("plan_node requires a pending state")
    return state.record(
        node="plan",
        detail=f"'{state.task}' 작업에 대한 오프라인 계획을 만들었습니다.",
        status=WorkflowStatus.PLANNED,
    )


def route_node(
    state: WorkflowState,
    *,
    decision: RouterDecision | None,
    confidence_threshold: float,
) -> WorkflowState:
    """Router 입력을 검증하고 부족한 결정은 사람 검토 interrupt로 보낸다."""
    if state.status is not WorkflowStatus.PLANNED:
        raise ValueError("route_node requires a planned state")
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be between 0.0 and 1.0")
    if decision is None:
        return state.record(
            node="router",
            detail="Router 결정이 없어 사람의 경로 검토를 기다립니다.",
            status=WorkflowStatus.WAITING_FOR_ROUTE_REVIEW,
        )
    if decision.confidence < confidence_threshold:
        return state.record(
            node="router",
            detail=(
                "Router 신뢰도가 임계값보다 낮아 사람의 경로 검토를 기다립니다: "
                f"{decision.confidence:.2f} < {confidence_threshold:.2f}."
            ),
            status=WorkflowStatus.WAITING_FOR_ROUTE_REVIEW,
        )
    return state.record(
        node="router",
        detail=f"{decision.source}가 {decision.route.value} 경로를 선택했습니다.",
        selected_route=decision.route,
    )


def resolve_route_review_node(state: WorkflowState, *, route: RouteKind) -> WorkflowState:
    """누락되거나 낮은 신뢰도의 Router 결정을 사람이 명시적으로 보완한다."""
    if state.status is not WorkflowStatus.WAITING_FOR_ROUTE_REVIEW:
        raise ValueError("resolve_route_review_node requires a route-review waiting state")
    return state.record(
        node="route_review",
        detail=f"사람 검토자가 {route.value} 경로를 선택했습니다.",
        status=WorkflowStatus.PLANNED,
        selected_route=route,
    )


def specialist_node(state: WorkflowState) -> WorkflowState:
    """선택한 연구·개발·검토 Node를 외부 도구 없이 한 번 실행한다."""
    if state.status is not WorkflowStatus.PLANNED:
        raise ValueError("specialist_node requires a planned state")
    if state.selected_route is None:
        raise ValueError("specialist_node requires a selected route")
    detail_by_route = {
        RouteKind.RESEARCH: "연구 Node가 오프라인 조사 계획을 정리했습니다.",
        RouteKind.DEVELOPMENT: "개발 Node가 오프라인 구현 계획을 정리했습니다.",
        RouteKind.REVIEW: "검토 Node가 오프라인 검토 계획을 정리했습니다.",
    }
    return state.record(
        node=state.selected_route.value,
        detail=detail_by_route[state.selected_route],
    )


def developer_node(state: WorkflowState) -> WorkflowState:
    """Planner의 계획을 소비해 외부 변경 없는 개발 산출물을 준비한다."""
    if state.status is not WorkflowStatus.PLANNED:
        raise ValueError("developer_node requires a planned state")
    return state.record(
        node="developer",
        detail="Developer가 외부 파일을 변경하지 않는 오프라인 구현 초안을 만들었습니다.",
    )


def reviewer_node(state: WorkflowState, *, decision: ReviewDecision) -> WorkflowState:
    """Reviewer 판정으로 다음 승인 경로 또는 검토 거절 END를 선택한다."""
    if state.status is not WorkflowStatus.PLANNED:
        raise ValueError("reviewer_node requires a planned state")
    if decision.approved:
        return state.record(
            node="reviewer",
            detail=f"{decision.source}의 검토 통과: {decision.feedback.strip()}",
            review_approved=True,
        )
    return state.record(
        node="reviewer",
        detail=f"{decision.source}의 검토 거절: {decision.feedback.strip()}",
        status=WorkflowStatus.REVIEW_REJECTED,
        review_approved=False,
    )


def approval_node(state: WorkflowState) -> WorkflowState:
    """위험 작업을 interrupt하고 안전 작업만 다음 Edge로 보낸다."""
    if state.status is not WorkflowStatus.PLANNED:
        raise ValueError("approval_node requires a planned state")
    if state.approval_required:
        return state.record(
            node="approval",
            detail=f"{state.action.value} 작업은 사람 승인을 기다립니다.",
            status=WorkflowStatus.WAITING_FOR_APPROVAL,
        )
    return state.record(
        node="approval",
        detail=f"{state.action.value} 작업은 위험 작업이 아니므로 승인 없이 진행합니다.",
        status=WorkflowStatus.READY,
    )


def resolve_approval_node(state: WorkflowState, *, approved: bool) -> WorkflowState:
    """중단된 위험 작업에 대한 명시적인 사람 결정을 기록한다."""
    if state.status is not WorkflowStatus.WAITING_FOR_APPROVAL:
        raise ValueError("resolve_approval_node requires a waiting state")
    if approved:
        return state.record(
            node="approval",
            detail="사람 승인을 받았습니다. 실행 시뮬레이션으로 이동합니다.",
            status=WorkflowStatus.READY,
            approval_granted=True,
        )
    return state.record(
        node="approval",
        detail="사람이 작업을 거절했습니다. 실행하지 않습니다.",
        status=WorkflowStatus.REJECTED,
        approval_granted=False,
    )


def execute_node(state: WorkflowState) -> WorkflowState:
    """READY 상태만 END로 이동시키며 실제 위험 행위는 수행하지 않는다."""
    if state.status is not WorkflowStatus.READY:
        raise ValueError("execute_node requires a ready state")
    result = f"오프라인 시뮬레이션 완료: {state.action.value} / {state.task}"
    return state.record(
        node="execute",
        detail="외부 시스템을 변경하지 않는 결정론적 실행 결과를 만들었습니다.",
        status=WorkflowStatus.COMPLETED,
        result=result,
    )


def retry_execute_node(state: WorkflowState) -> WorkflowState:
    """고정된 실패 계획에 따라 한 번의 오프라인 실행 시도를 기록한다."""
    if state.status is not WorkflowStatus.READY:
        raise ValueError("retry_execute_node requires a ready state")
    attempt_count = state.attempt_count + 1
    if state.attempt_count < state.retry_failures_before_success:
        return state.record(
            node="execute",
            detail=(
                f"{state.retry_source} 계획의 오프라인 실행 시도 {attempt_count}가 "
                "결정론적으로 실패했습니다."
            ),
            status=WorkflowStatus.ERROR,
            attempt_count=attempt_count,
        )
    result = f"오프라인 시뮬레이션 완료: {state.action.value} / {state.task}"
    return state.record(
        node="execute",
        detail=(
            f"{state.retry_source} 계획의 오프라인 실행 시도 {attempt_count}가 "
            "성공했습니다."
        ),
        status=WorkflowStatus.COMPLETED,
        result=result,
        attempt_count=attempt_count,
    )


def error_node(state: WorkflowState) -> WorkflowState:
    """실패를 감사하고, 상한 안에서만 READY 재시도 Edge로 되돌린다."""
    if state.status is not WorkflowStatus.ERROR:
        raise ValueError("error_node requires an error state")
    retries_used = state.attempt_count - 1
    if retries_used < state.retry_max_retries:
        return state.record(
            node="error",
            detail=(
                f"재시도 {retries_used + 1}/{state.retry_max_retries}를 허용합니다. "
                "외부 부작용 없이 실행 시뮬레이션으로 돌아갑니다."
            ),
            status=WorkflowStatus.READY,
        )
    return state.record(
        node="error",
        detail=(
            f"재시도 상한 {state.retry_max_retries}에 도달했습니다. "
            "실행 시뮬레이션을 중단합니다."
        ),
        status=WorkflowStatus.FAILED,
    )
