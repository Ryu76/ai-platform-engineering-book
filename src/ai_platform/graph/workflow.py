"""START → plan → approval → execute → END 오프라인 Workflow."""
from __future__ import annotations

from ai_platform.graph.checkpointer import MemoryCheckpointer
from ai_platform.graph.nodes import approval_node, execute_node, plan_node, resolve_approval_node
from ai_platform.graph.state import ActionKind, WorkflowState, WorkflowStatus


class DeterministicWorkflow:
    """사람 승인 interrupt를 갖는 최소 상태형 Workflow를 실행한다.

    구현은 LangGraph가 제공하는 State, Node, Edge, interrupt 개념을 외부 의존성 없이
    학습하기 위한 참조 모델이다. 어떤 ActionKind도 실제 시스템 작업을 실행하지 않는다.
    """

    def __init__(self, *, checkpointer: MemoryCheckpointer | None = None) -> None:
        """선택한 Checkpointer와 Workflow를 연결한다."""
        self._checkpointer = checkpointer or MemoryCheckpointer()

    def invoke(self, *, run_id: str, task: str, action: ActionKind) -> WorkflowState:
        """START에서 승인 interrupt 또는 END까지 한 번 실행한다."""
        state = WorkflowState.start(task=task, action=action)
        state = plan_node(state)
        state = approval_node(state)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def resume(self, *, run_id: str, approved: bool) -> WorkflowState:
        """사람의 명시적 결정을 받은 interrupt만 재개한다."""
        state = self._checkpointer.load(run_id=run_id)
        state = resolve_approval_node(state, approved=approved)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def checkpoint(self, *, run_id: str) -> WorkflowState:
        """검증 또는 표시를 위해 최신 Checkpoint를 읽는다."""
        return self._checkpointer.load(run_id=run_id)
