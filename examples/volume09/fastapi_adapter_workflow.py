"""FastAPI handler용 요청·응답 어댑터가 승인 경계를 유지하는 오프라인 예제."""
from __future__ import annotations

from ai_platform.graph import (
    ActionKind,
    ApprovalRequest,
    StartWorkflowRequest,
    WorkflowApiAdapter,
)


def show(*, label: str, status: str, events: list[str]) -> None:
    """HTTP 서버나 외부 부작용 없이 응답 스냅샷을 안정적으로 출력한다."""
    print(f"{label}: status={status}")
    print(f"events={' | '.join(events)}")


def main() -> None:
    """위험 HTTP 요청도 명시적 별도 승인 전에는 실행되지 않음을 보인다."""
    adapter = WorkflowApiAdapter()
    waiting = adapter.start(
        request=StartWorkflowRequest.model_validate(
            {
                "run_id": "api-demo-001",
                "task": "학습용 배포를 준비한다",
                "action": ActionKind.DEPLOY,
            }
        )
    )
    show(
        label="시작 응답",
        status=waiting.status,
        events=[event.node for event in waiting.events],
    )

    completed = adapter.resume(
        run_id="api-demo-001",
        request=ApprovalRequest(approved=True),
    )
    show(
        label="명시적 승인 응답",
        status=completed.status,
        events=[event.node for event in completed.events],
    )


if __name__ == "__main__":
    main()
