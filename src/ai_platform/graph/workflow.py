"""START에서 END까지 전이하는 오프라인 Workflow 참조 모델."""
from __future__ import annotations

from collections.abc import Iterator

from ai_platform.graph.checkpointer import Checkpointer, MemoryCheckpointer
from ai_platform.graph.nodes import (
    approval_node,
    developer_node,
    error_node,
    execute_node,
    plan_node,
    resolve_approval_node,
    resolve_route_review_node,
    retry_execute_node,
    reviewer_node,
    route_node,
    specialist_node,
)
from ai_platform.graph.state import (
    ActionKind,
    RetryPlan,
    ReviewDecision,
    RouteKind,
    RouterDecision,
    StreamUpdate,
    WorkflowState,
    WorkflowStatus,
)


class WorkflowRunConflictError(ValueError):
    """이미 존재하는 run ID의 Checkpoint를 새 시작으로 교체하려 할 때 발생한다."""


class DeterministicWorkflow:
    """사람 승인 interrupt를 갖는 최소 상태형 Workflow를 실행한다.

    구현은 LangGraph가 제공하는 State, Node, Edge, interrupt 개념을 외부 의존성 없이
    학습하기 위한 참조 모델이다. 어떤 ActionKind도 실제 시스템 작업을 실행하지 않는다.
    """

    def __init__(self, *, checkpointer: Checkpointer | None = None) -> None:
        """선택한 Checkpointer와 Workflow를 연결한다."""
        self._checkpointer = checkpointer or MemoryCheckpointer()

    def invoke(self, *, run_id: str, task: str, action: ActionKind) -> WorkflowState:
        """START에서 승인 interrupt 또는 END까지 한 번 실행한다."""
        state = self._initial_state(task=task, action=action)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def invoke_new(self, *, run_id: str, task: str, action: ActionKind) -> WorkflowState:
        """새 run ID에만 시작 상태를 기록해 check-then-save 경쟁을 피한다.

        이 오프라인 Workflow의 Node는 외부 부작용을 만들지 않는다. 실제 위험 작업은
        운영 저장소의 트랜잭션·파일 잠금과 승인 정책을 별도로 사용해야 한다.
        """
        state = self._initial_state(task=task, action=action)
        if not self._checkpointer.save_if_absent(run_id=run_id, state=state):
            raise WorkflowRunConflictError(f"run_id already exists: {run_id}")
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

    @staticmethod
    def _initial_state(*, task: str, action: ActionKind) -> WorkflowState:
        """START부터 승인 interrupt 또는 END까지의 결정론적 초기 전이를 만든다."""
        state = WorkflowState.start(task=task, action=action)
        state = plan_node(state)
        state = approval_node(state)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
        return state


class StreamingWorkflow:
    """완료된 Node 전이를 순서대로 내보내는 오프라인 상태 Streaming Workflow다.

    이 클래스는 LLM 토큰이나 Server-Sent Event를 전송하지 않는다. 각 업데이트는 하나의
    Node 전이 후 저장된 불변 상태다. 위험 작업은 명시적 ``resume_stream(..., approved=True)``
    전까지 approval 업데이트까지만 내보내며 execute 업데이트를 만들지 않는다.
    """

    def __init__(self, *, checkpointer: Checkpointer | None = None) -> None:
        """선택한 Checkpointer와 상태 업데이트 스트림을 연결한다."""
        self._checkpointer = checkpointer or MemoryCheckpointer()

    def stream(
        self, *, run_id: str, task: str, action: ActionKind
    ) -> Iterator[StreamUpdate]:
        """START 뒤 각 완료 Node의 저장된 상태 업데이트를 순서대로 내보낸다."""
        state = WorkflowState.start(task=task, action=action)
        state = plan_node(state)
        yield self._save_and_update(run_id=run_id, state=state)
        state = approval_node(state)
        yield self._save_and_update(run_id=run_id, state=state)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
            yield self._save_and_update(run_id=run_id, state=state)

    def resume_stream(self, *, run_id: str, approved: bool) -> Iterator[StreamUpdate]:
        """사람 결정을 기록한 뒤 허용된 Node 전이만 순서대로 내보낸다."""
        state = self._checkpointer.load(run_id=run_id)
        state = resolve_approval_node(state, approved=approved)
        yield self._save_and_update(run_id=run_id, state=state)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
            yield self._save_and_update(run_id=run_id, state=state)

    def checkpoint(self, *, run_id: str) -> WorkflowState:
        """검증 또는 표시를 위해 최신 Checkpoint를 읽는다."""
        return self._checkpointer.load(run_id=run_id)

    def _save_and_update(self, *, run_id: str, state: WorkflowState) -> StreamUpdate:
        """각 업데이트를 내보내기 전에 Checkpoint와 마지막 이벤트를 고정한다."""
        self._checkpointer.save(run_id=run_id, state=state)
        return StreamUpdate(run_id=run_id, state=state, event=state.events[-1])


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
        checkpointer: Checkpointer | None = None,
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

    def __init__(self, *, checkpointer: Checkpointer | None = None) -> None:
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


class PlannerDeveloperReviewerSubgraph:
    """계획·개발·검토만 담당하는 재사용 가능한 오프라인 Subgraph다.

    Subgraph는 부모 Workflow의 실행 권한을 가지지 않는다. Reviewer 판정은 산출물
    검토만 끝내며, 부모가 위험 ActionKind에 대한 Approval Node를 별도로 적용한다.
    """

    def invoke(
        self, *, state: WorkflowState, review_decision: ReviewDecision
    ) -> WorkflowState:
        """PENDING 입력을 고정 역할 순서의 검토 완료 또는 거절 상태로 전이한다."""
        state = plan_node(state)
        state = developer_node(state)
        return reviewer_node(state, decision=review_decision)


class SubgraphWorkflow:
    """재사용 Subgraph 뒤에도 부모 승인 경계를 유지하는 오프라인 Workflow다.

    ``PlannerDeveloperReviewerSubgraph``는 산출물 검토까지만 수행한다. 부모는
    Subgraph가 ``PLANNED`` 상태를 반환한 경우에만 Approval Node를 실행하고, 위험
    작업은 명시적 사람 승인 전까지 execute Node에 도달하지 못하게 한다.
    """

    def __init__(
        self,
        *,
        subgraph: PlannerDeveloperReviewerSubgraph | None = None,
        checkpointer: Checkpointer | None = None,
    ) -> None:
        """주입 가능한 Subgraph와 Checkpointer를 부모 Workflow에 연결한다."""
        self._subgraph = subgraph or PlannerDeveloperReviewerSubgraph()
        self._checkpointer = checkpointer or MemoryCheckpointer()

    def invoke(
        self,
        *,
        run_id: str,
        task: str,
        action: ActionKind,
        review_decision: ReviewDecision,
    ) -> WorkflowState:
        """START에서 Subgraph를 호출하고 부모 승인 interrupt 또는 END까지 진행한다."""
        state = WorkflowState.start(task=task, action=action)
        state = self._subgraph.invoke(state=state, review_decision=review_decision)
        if state.status is WorkflowStatus.PLANNED:
            state = self._continue_after_subgraph(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def resume(self, *, run_id: str, approved: bool) -> WorkflowState:
        """Subgraph 완료 뒤 중단된 위험 작업의 사람 승인만 재개한다."""
        state = self._checkpointer.load(run_id=run_id)
        state = resolve_approval_node(state, approved=approved)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def checkpoint(self, *, run_id: str) -> WorkflowState:
        """검증 또는 표시를 위해 부모 Workflow의 최신 Checkpoint를 읽는다."""
        return self._checkpointer.load(run_id=run_id)

    @staticmethod
    def _continue_after_subgraph(state: WorkflowState) -> WorkflowState:
        """검토 통과 뒤 부모의 위험 작업 승인 정책을 적용한다."""
        state = approval_node(state)
        if state.status is WorkflowStatus.READY:
            state = execute_node(state)
        return state


class RetryWorkflow:
    """제한된 재시도와 Error Node를 갖는 오프라인 참조 Workflow다.

    실패 여부는 ``RetryPlan``으로 고정하므로 시간, 네트워크, 외부 도구에 의존하지
    않는다. 위험 ActionKind는 첫 실행과 모든 재시도 전에 같은 사람 승인 경계를
    통과해야 하며, 승인 거절 시 시도 자체가 시작되지 않는다.
    """

    def __init__(self, *, checkpointer: Checkpointer | None = None) -> None:
        """선택한 Checkpointer와 재시도 Workflow를 연결한다."""
        self._checkpointer = checkpointer or MemoryCheckpointer()

    def invoke(
        self,
        *,
        run_id: str,
        task: str,
        action: ActionKind,
        retry_plan: RetryPlan,
    ) -> WorkflowState:
        """계획과 승인 뒤, 성공·상한 실패·승인 interrupt까지 진행한다."""
        state = WorkflowState.start(
            task=task,
            action=action,
            retry_failures_before_success=retry_plan.failures_before_success,
            retry_max_retries=retry_plan.max_retries,
            retry_source=retry_plan.source,
        )
        state = plan_node(state)
        state = approval_node(state)
        if state.status is WorkflowStatus.READY:
            state = self._run_with_retries(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def resume(self, *, run_id: str, approved: bool) -> WorkflowState:
        """위험 작업의 명시적 사람 결정을 기록한 뒤에만 시도를 시작한다."""
        state = self._checkpointer.load(run_id=run_id)
        state = resolve_approval_node(state, approved=approved)
        if state.status is WorkflowStatus.READY:
            state = self._run_with_retries(state)
        self._checkpointer.save(run_id=run_id, state=state)
        return state

    def checkpoint(self, *, run_id: str) -> WorkflowState:
        """검증 또는 표시를 위해 최신 Checkpoint를 읽는다."""
        return self._checkpointer.load(run_id=run_id)

    @staticmethod
    def _run_with_retries(state: WorkflowState) -> WorkflowState:
        """Error Node가 READY를 반환하는 동안에만 재시도를 반복한다."""
        while state.status is WorkflowStatus.READY:
            state = retry_execute_node(state)
            if state.status is WorkflowStatus.ERROR:
                state = error_node(state)
        return state
