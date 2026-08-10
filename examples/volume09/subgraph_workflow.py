"""Subgraph의 검토 통과가 위험 작업의 실행 승인을 대체하지 않는 오프라인 예제."""
from __future__ import annotations

from ai_platform.graph import ActionKind, ReviewDecision, SubgraphWorkflow


def show(*, label: str, status: str, events: list[str]) -> None:
    """외부 부작용 없이 상태 전이만 안정적으로 출력한다."""
    print(f"{label}: status={status}")
    print(f"events={' | '.join(events)}")


def main() -> None:
    """부모 승인 경계가 Subgraph 완료 뒤에도 유지됨을 결정론적으로 보인다."""
    workflow = SubgraphWorkflow()
    waiting = workflow.invoke(
        run_id="subgraph-demo-001",
        task="학습용 배포 초안을 검토한다",
        action=ActionKind.DEPLOY,
        review_decision=ReviewDecision(approved=True, feedback="검토 기준을 충족합니다."),
    )
    show(
        label="Subgraph 검토 통과 후",
        status=waiting.status,
        events=[event.node for event in waiting.events],
    )

    completed = workflow.resume(run_id="subgraph-demo-001", approved=True)
    show(
        label="부모 Workflow의 사람 실행 승인 후",
        status=completed.status,
        events=[event.node for event in completed.events],
    )


if __name__ == "__main__":
    main()
