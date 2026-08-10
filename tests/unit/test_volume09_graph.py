"""Volume 09 오프라인 상태형 Workflow의 안전 계약을 검사한다."""
from __future__ import annotations

import pytest

from ai_platform.graph import ActionKind, DeterministicWorkflow, WorkflowState, WorkflowStatus


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
