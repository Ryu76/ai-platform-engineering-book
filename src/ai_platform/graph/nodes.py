"""외부 부작용 없이 상태만 전이하는 Volume 09 학습용 Node."""
from __future__ import annotations

from ai_platform.graph.state import WorkflowState, WorkflowStatus


def plan_node(state: WorkflowState) -> WorkflowState:
    """작업을 결정론적인 오프라인 계획으로 바꾼다."""
    if state.status is not WorkflowStatus.PENDING:
        raise ValueError("plan_node requires a pending state")
    return state.record(
        node="plan",
        detail=f"'{state.task}' 작업에 대한 오프라인 계획을 만들었습니다.",
        status=WorkflowStatus.PLANNED,
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
