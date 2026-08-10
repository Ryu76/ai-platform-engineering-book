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


RISKY_ACTIONS = frozenset({ActionKind.DELETE, ActionKind.DEPLOY, ActionKind.SEND})


@dataclass(frozen=True)
class WorkflowEvent:
    """한 Node가 남긴 감사 가능한 결정론적 이벤트다."""

    sequence: int
    node: str
    detail: str


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
class WorkflowState:
    """Node 사이에서 전달되는 불변 상태다."""

    task: str
    action: ActionKind
    status: WorkflowStatus
    approval_required: bool
    approval_granted: bool | None
    selected_route: RouteKind | None
    result: str | None
    events: tuple[WorkflowEvent, ...]

    @classmethod
    def start(cls, *, task: str, action: ActionKind) -> WorkflowState:
        """검증된 START 상태를 만든다."""
        normalized_task = task.strip()
        if not normalized_task:
            raise ValueError("task must not be empty")
        return cls(
            task=normalized_task,
            action=action,
            status=WorkflowStatus.PENDING,
            approval_required=action in RISKY_ACTIONS,
            approval_granted=None,
            selected_route=None,
            result=None,
            events=(),
        )

    def record(
        self,
        *,
        node: str,
        detail: str,
        status: WorkflowStatus | None = None,
        approval_granted: bool | None = None,
        selected_route: RouteKind | None = None,
        result: str | None = None,
    ) -> WorkflowState:
        """상태 변경과 함께 순서가 정해진 이벤트를 추가한다."""
        event = WorkflowEvent(sequence=len(self.events) + 1, node=node, detail=detail)
        return replace(
            self,
            status=self.status if status is None else status,
            approval_granted=(
                self.approval_granted if approval_granted is None else approval_granted
            ),
            selected_route=self.selected_route if selected_route is None else selected_route,
            result=self.result if result is None else result,
            events=(*self.events, event),
        )
