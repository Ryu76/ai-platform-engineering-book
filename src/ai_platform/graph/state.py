"""Volume 09에서 사용하는 결정론적 오프라인 Workflow 상태 모델."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class ActionKind(StrEnum):
    """학습용 Workflow가 다루는 작업 종류다.

    이 모듈은 실제 파일 삭제, 배포, 전송을 수행하지 않는다. 위험도와 승인 흐름을
    재현 가능한 상태 전이로만 모델링한다.
    """

    READ = "read"
    TRANSFORM = "transform"
    DELETE = "delete"
    DEPLOY = "deploy"
    SEND = "send"


class RouteKind(StrEnum):
    """오프라인 Router가 선택할 수 있는 학습용 전문 Node다."""

    RESEARCH = "research"
    DEVELOPMENT = "development"
    REVIEW = "review"


class WorkflowStatus(StrEnum):
    """START에서 END까지 이동하는 Workflow의 상태다."""

    PENDING = "pending"
    PLANNED = "planned"
    WAITING_FOR_ROUTE_REVIEW = "waiting_for_route_review"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    READY = "ready"
    COMPLETED = "completed"
    REJECTED = "rejected"
    REVIEW_REJECTED = "review_rejected"
    ERROR = "error"
    FAILED = "failed"


RISKY_ACTIONS = frozenset({ActionKind.DELETE, ActionKind.DEPLOY, ActionKind.SEND})


@dataclass(frozen=True)
class WorkflowEvent:
    """한 Node가 남긴 감사 가능한 결정론적 이벤트다."""

    sequence: int
    node: str
    detail: str


@dataclass(frozen=True)
class StreamUpdate:
    """한 Node 전이 뒤 구독자에게 전달하는 결정론적 상태 업데이트다.

    토큰이나 네트워크 스트림이 아니라, 이미 완료된 한 Node 전이를 나타낸다.
    ``state``는 해당 이벤트를 포함한 불변 스냅샷이므로 구독자는 부분 변경을 추측하지
    않고 상태와 이벤트 순서를 함께 검사할 수 있다.
    """

    run_id: str
    state: WorkflowState
    event: WorkflowEvent


@dataclass(frozen=True)
class RouterDecision:
    """외부 Router를 호출하지 않고 전달받는 결정론적 라우팅 입력이다."""

    route: RouteKind
    confidence: float
    source: str = "offline-router"

    def __post_init__(self) -> None:
        """신뢰도와 출처를 Node 실행 전에 검증한다."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("router confidence must be between 0.0 and 1.0")
        if not self.source.strip():
            raise ValueError("router source must not be empty")


@dataclass(frozen=True)
class ReviewDecision:
    """외부 모델 호출 없이 전달받는 결정론적 Reviewer 판정이다.

    ``approved``는 산출물의 검토 통과만 뜻한다. 위험 ActionKind의 실행 권한은
    별도의 Approval Node에서만 부여할 수 있다.
    """

    approved: bool
    feedback: str
    source: str = "offline-reviewer"

    def __post_init__(self) -> None:
        """감사에 필요한 비어 있지 않은 판정 근거와 출처를 강제한다."""
        if not self.feedback.strip():
            raise ValueError("review feedback must not be empty")
        if not self.source.strip():
            raise ValueError("review source must not be empty")


@dataclass(frozen=True)
class RetryPlan:
    """오프라인 실패 횟수와 재시도 상한을 고정하는 결정론적 입력이다.

    ``failures_before_success``만큼의 실행 시뮬레이션이 실패한 뒤 성공한다. 상한보다
    많은 실패가 필요하면 Error Node는 ``FAILED`` END로 끝낸다.
    """

    failures_before_success: int
    max_retries: int
    source: str = "offline-retry-plan"

    def __post_init__(self) -> None:
        """음수와 감사할 수 없는 출처를 Node 실행 전에 거부한다."""
        if self.failures_before_success < 0:
            raise ValueError("failures_before_success must not be negative")
        if self.max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if not self.source.strip():
            raise ValueError("retry source must not be empty")


@dataclass(frozen=True)
class WorkflowState:
    """Node 사이에서 전달되는 불변 상태다."""

    task: str
    action: ActionKind
    status: WorkflowStatus
    approval_required: bool
    approval_granted: bool | None
    review_approved: bool | None
    selected_route: RouteKind | None
    result: str | None
    events: tuple[WorkflowEvent, ...]
    retry_failures_before_success: int = 0
    retry_max_retries: int = 0
    retry_source: str = "offline-retry-plan"
    attempt_count: int = 0

    @classmethod
    def start(
        cls,
        *,
        task: str,
        action: ActionKind,
        retry_failures_before_success: int = 0,
        retry_max_retries: int = 0,
        retry_source: str = "offline-retry-plan",
    ) -> WorkflowState:
        """검증된 START 상태를 만든다."""
        normalized_task = task.strip()
        if not normalized_task:
            raise ValueError("task must not be empty")
        if retry_failures_before_success < 0:
            raise ValueError("retry_failures_before_success must not be negative")
        if retry_max_retries < 0:
            raise ValueError("retry_max_retries must not be negative")
        if not retry_source.strip():
            raise ValueError("retry_source must not be empty")
        return cls(
            task=normalized_task,
            action=action,
            status=WorkflowStatus.PENDING,
            approval_required=action in RISKY_ACTIONS,
            approval_granted=None,
            review_approved=None,
            selected_route=None,
            result=None,
            events=(),
            retry_failures_before_success=retry_failures_before_success,
            retry_max_retries=retry_max_retries,
            retry_source=retry_source.strip(),
            attempt_count=0,
        )

    def record(
        self,
        *,
        node: str,
        detail: str,
        status: WorkflowStatus | None = None,
        approval_granted: bool | None = None,
        review_approved: bool | None = None,
        selected_route: RouteKind | None = None,
        result: str | None = None,
        attempt_count: int | None = None,
    ) -> WorkflowState:
        """상태 변경과 함께 순서가 정해진 이벤트를 추가한다."""
        event = WorkflowEvent(sequence=len(self.events) + 1, node=node, detail=detail)
        return replace(
            self,
            status=self.status if status is None else status,
            approval_granted=(
                self.approval_granted if approval_granted is None else approval_granted
            ),
            review_approved=(
                self.review_approved if review_approved is None else review_approved
            ),
            selected_route=self.selected_route if selected_route is None else selected_route,
            result=self.result if result is None else result,
            attempt_count=self.attempt_count if attempt_count is None else attempt_count,
            events=(*self.events, event),
        )
