"""START에서 END까지 전이하는 오프라인 Workflow 참조 모델."""
from __future__ import annotations

from ai_platform.graph.checkpointer import MemoryCheckpointer
from ai_platform.graph.nodes import (
    approval_node,
    developer_node,
    execute_node,
    plan_node,
    resolve_approval_node,
    resolve_route_review_node,
    reviewer_node,
    route_node,
    specialist_node,
)
from ai_platform.graph.state import (
    ActionKind,
    ReviewDecision,
    RouteKind,
    RouterDecision,
    WorkflowState,
    WorkflowStatus,
)


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


class RoutedWorkflow:
    """Router 조건 Edge와 사람 경로 검토를 갖는 오프라인 다중 Node Workflow다.

    Router는 호출하지 않는다. 호출자가 전달한 ``RouterDecision``만 소비하고, 누락 또는
    낮은 신뢰도는 안전한 사람 검토 interrupt로 전환한다. 위험 ActionKind는 경로가
    선택된 뒤에도 별도의 승인 없이는 실행 시뮬레이션에 도달하지 못한다.
    """

    def __init__(
        self,
        *,
        confidence_threshold: float = 0.80,
        checkpointer: MemoryCheckpointer | None = None,
    ) -> None:
        """임계값과 선택적 Checkpointer를 검증해 Workflow에 연결한다."""
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        self._confidence_threshold = confidence_threshold
        self._checkpointer = checkpointer or MemoryCheckpointer()

    def invoke(
        self,
        *,
        run_id: str,
        task: str,
        action: ActionKind,
        router_decision: RouterDecision | None,
    ) -> WorkflowState:
        """계획 뒤 Router 조건 Edge를 실행해 경로 검토 또는 END까지 진행한다."""
        state = WorkflowState.start(task=task, action=action)
        state = plan_node(state)
        state = route_node(
            state,
            decision=router_decision,
            confidence_threshold=self._confidence_threshold,
        )
        if state.status is WorkflowStatus.PLANNED:
            state = self._continue_after_route(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def review_route(self, *, run_id: str, route: RouteKind) -> WorkflowState:
        """사람이 경로 검토 interrupt를 해결한 뒤 안전 경계를 다시 평가한다."""
        state = self._checkpointer.load(run_id=run_id)
        state = resolve_route_review_node(state, route=route)
        state = self._continue_after_route(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def resume(self, *, run_id: str, approved: bool) -> WorkflowState:
        """경로가 결정된 위험 작업에 대한 사람 승인을 처리한다."""
        state = self._checkpointer.load(run_id=run_id)
        state = resolve_approval_node(state, approved=approved)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def checkpoint(self, *, run_id: str) -> WorkflowState:
        """검증 또는 표시를 위해 최신 Checkpoint를 읽는다."""
        return self._checkpointer.load(run_id=run_id)

    @staticmethod
    def _continue_after_route(state: WorkflowState) -> WorkflowState:
        """선택된 전문 Node와 승인 조건 Edge를 순서대로 적용한다."""
        state = specialist_node(state)
        state = approval_node(state)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
        return state


class PlannerDeveloperReviewerWorkflow:
    """Planner, Developer, Reviewer 역할과 승인 경계를 보이는 오프라인 Workflow다.

    Reviewer의 통과 판정은 코드·계획 초안의 품질 판단일 뿐 실행 권한이 아니다.
    위험 ActionKind는 검토를 통과한 뒤에도 별도의 사람 승인 interrupt를 거친다.
    """

    def __init__(self, *, checkpointer: MemoryCheckpointer | None = None) -> None:
        """선택한 Checkpointer와 고정 역할 순서의 Workflow를 연결한다."""
        self._checkpointer = checkpointer or MemoryCheckpointer()

    def invoke(
        self,
        *,
        run_id: str,
        task: str,
        action: ActionKind,
        review_decision: ReviewDecision,
    ) -> WorkflowState:
        """계획, 개발, 검토를 순서대로 실행하고 안전 경계에서 멈추거나 끝낸다."""
        state = WorkflowState.start(task=task, action=action)
        state = plan_node(state)
        state = developer_node(state)
        state = reviewer_node(state, decision=review_decision)
        if state.status is WorkflowStatus.PLANNED:
            state = self._continue_after_review(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def resume(self, *, run_id: str, approved: bool) -> WorkflowState:
        """검토를 통과한 위험 작업의 명시적 실행 승인을 처리한다."""
        state = self._checkpointer.load(run_id=run_id)
        state = resolve_approval_node(state, approved=approved)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def checkpoint(self, *, run_id: str) -> WorkflowState:
        """검증 또는 표시를 위해 최신 Checkpoint를 읽는다."""
        return self._checkpointer.load(run_id=run_id)

    @staticmethod
    def _continue_after_review(state: WorkflowState) -> WorkflowState:
        """검토 통과 뒤에도 기존 위험 ActionKind 승인 정책을 적용한다."""
        state = approval_node(state)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
        return state
