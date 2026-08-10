"""위험 작업이 사람 승인을 기다리는 오프라인 Workflow 예제."""
from __future__ import annotations

from ai_platform.graph import ActionKind, DeterministicWorkflow


def summarize(*, label: str, state_status: str, result: str | None, events: list[str]) -> None:
    """학습자가 상태 전이만 확인할 수 있도록 안정적인 텍스트를 출력한다."""
    print(f"{label}: status={state_status}")
    print(f"result={result}")
    print(f"events={' | '.join(events)}")


def main() -> None:
    """deploy 작업이 승인 전에는 실행되지 않고 승인 뒤에만 완료됨을 보인다."""
    workflow = DeterministicWorkflow()
    waiting = workflow.invoke(
        run_id="offline-demo-001",
        task="학습용 배포 계획을 검토한다",
        action=ActionKind.DEPLOY,
    )
    summarize(
        label="승인 전",
        state_status=waiting.status,
        result=waiting.result,
        events=[event.node for event in waiting.events],
    )

    completed = workflow.resume(run_id="offline-demo-001", approved=True)
    summarize(
        label="승인 후",
        state_status=completed.status,
        result=completed.result,
        events=[event.node for event in completed.events],
    )


if __name__ == "__main__":
    main()
