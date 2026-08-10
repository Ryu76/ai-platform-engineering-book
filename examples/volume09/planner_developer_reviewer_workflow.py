"""검토 통과와 위험 작업의 별도 사람 승인을 보이는 오프라인 Workflow 예제."""
from __future__ import annotations

from ai_platform.graph import ActionKind, PlannerDeveloperReviewerWorkflow, ReviewDecision


def show(*, label: str, status: str, events: list[str]) -> None:
    """상태 전이만 안정적으로 출력한다."""
    print(f"{label}: status={status}")
    print(f"events={' | '.join(events)}")


def main() -> None:
    """Reviewer 통과가 실행 승인을 대체하지 않음을 결정론적으로 보인다."""
    workflow = PlannerDeveloperReviewerWorkflow()
    waiting = workflow.invoke(
        run_id="pdr-demo-001",
        task="학습용 배포 초안을 검토한다",
        action=ActionKind.DEPLOY,
        review_decision=ReviewDecision(approved=True, feedback="롤백 절차가 명확합니다."),
    )
    show(
        label="검토 통과 후",
        status=waiting.status,
        events=[event.node for event in waiting.events],
    )

    completed = workflow.resume(run_id="pdr-demo-001", approved=True)
    show(
        label="사람 실행 승인 후",
        status=completed.status,
        events=[event.node for event in completed.events],
    )


if __name__ == "__main__":
    main()
