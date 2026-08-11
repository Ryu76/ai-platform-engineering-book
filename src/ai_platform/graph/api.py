"""FastAPI handler가 소비할 수 있는 오프라인 Workflow 요청·응답 어댑터.

이 모듈은 웹 서버를 만들거나 HTTP 요청을 전송하지 않는다. 프로젝트에 FastAPI 의존성이
선언되기 전에도, 이후 FastAPI route가 그대로 사용할 수 있는 엄격한 요청·응답 계약과
위험 작업의 승인 경계를 제공한다.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from ai_platform.graph.state import ActionKind, WorkflowEvent, WorkflowState, WorkflowStatus
from ai_platform.graph.workflow import DeterministicWorkflow, WorkflowRunConflictError


class StartWorkflowRequest(BaseModel):
    """``POST /workflows`` 본문에 해당하는 검증된 오프라인 시작 요청이다."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    run_id: str = Field(min_length=1, max_length=128)
    task: str = Field(min_length=1, max_length=1_000)
    action: ActionKind


class ApprovalRequest(BaseModel):
    """``POST /workflows/{run_id}/approval``의 명시적 사람 결정이다.

    ``StrictBool``은 JSON 문자열 ``"true"``나 숫자를 승인으로 강제 변환하지 않는다.
    인증·인가·승인자 신원은 이 오프라인 학습 계약의 범위 밖이며, 실제 서버에서 별도로
    검증해야 한다.
    """

    model_config = ConfigDict(extra="forbid")

    approved: StrictBool


class RunIdPath(BaseModel):
    """승인 route의 경로 매개변수에 적용할 run ID 계약이다."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    run_id: str = Field(min_length=1, max_length=128)


class WorkflowEventResponse(BaseModel):
    """외부 응답에 포함할 한 개의 결정론적 감사 이벤트다."""

    model_config = ConfigDict(frozen=True)

    sequence: int
    node: str
    detail: str

    @classmethod
    def from_event(cls, event: WorkflowEvent) -> WorkflowEventResponse:
        """도메인 이벤트를 공개 응답 스키마로 복사한다."""
        return cls(sequence=event.sequence, node=event.node, detail=event.detail)


class WorkflowResponse(BaseModel):
    """FastAPI가 JSON으로 직렬화할 수 있는 불변 Workflow 상태 스냅샷이다."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    action: ActionKind
    status: WorkflowStatus
    approval_required: bool
    approval_granted: bool | None
    result: str | None
    events: tuple[WorkflowEventResponse, ...]

    @classmethod
    def from_state(cls, *, run_id: str, state: WorkflowState) -> WorkflowResponse:
        """저장된 상태 전체가 아닌 공개 실행 요약을 일관되게 만든다."""
        return cls(
            run_id=run_id,
            action=state.action,
            status=state.status,
            approval_required=state.approval_required,
            approval_granted=state.approval_granted,
            result=state.result,
            events=tuple(WorkflowEventResponse.from_event(event) for event in state.events),
        )


class WorkflowApiAdapter:
    """검증된 HTTP 입력을 오프라인 Workflow 호출로 연결하는 프레임워크 독립 어댑터다.

    어댑터는 ``DeterministicWorkflow``만 호출한다. 네트워크, 실제 배포·삭제·전송, 자동
    승인은 수행하지 않는다. 위험 ActionKind는 ``start``에서 approval interrupt 응답을
    반환하고, 호출자가 별도 ``ApprovalRequest(approved=True)``를 제출할 때만 완료한다.
    """

    def __init__(self, *, workflow: DeterministicWorkflow | None = None) -> None:
        """테스트 가능한 Workflow 구현을 주입하거나 기본 오프라인 구현을 사용한다."""
        self._workflow = workflow or DeterministicWorkflow()

    def start(self, *, request: StartWorkflowRequest) -> WorkflowResponse:
        """새 run ID만 시작하고 현재 상태를 HTTP 응답 계약으로 변환한다.

        시작 요청 재전송이 기존 승인 대기 Checkpoint를 안전 작업이나 다른 작업으로
        바꾸지 못하게 한다. Checkpointer의 ``save_if_absent``가 한 번의 생성으로 이
        판단과 저장을 묶는다. 실제 HTTP route는 이 오류를 409 Conflict 등 자신의
        전송 계층 오류로 매핑할 수 있다.
        """
        state = self._workflow.invoke_new(
            run_id=request.run_id,
            task=request.task,
            action=request.action,
        )
        return WorkflowResponse.from_state(run_id=request.run_id, state=state)

    def resume(
        self, *, run_id: str, request: ApprovalRequest
    ) -> WorkflowResponse:
        """명시적 승인 요청으로 이미 중단된 위험 작업만 재개한다.

        동시 승인 재전송 중 먼저 상태를 소비한 요청 뒤에 도착한 요청은 Workflow의
        내부 ``waiting state`` 오류를 외부의 충돌 계약으로 변환한다. 다른 입력 검증
        오류는 숨기지 않는다.
        """
        normalized_run_id = _validated_run_id(run_id)
        try:
            state = self._workflow.resume(
                run_id=normalized_run_id,
                approved=request.approved,
            )
        except ValueError as error:
            if "waiting state" not in str(error):
                raise
            raise WorkflowRunConflictError(
                f"workflow approval is no longer pending: {normalized_run_id}"
            ) from error
        return WorkflowResponse.from_state(run_id=normalized_run_id, state=state)



def _validated_run_id(run_id: str) -> str:
    """경로 매개변수도 시작 요청과 같은 비어 있지 않은 식별자 계약을 적용한다."""
    return RunIdPath(run_id=run_id).run_id
