"""동시 스트리밍 승인이 한 번만 오프라인 실행되는 Volume 09 데모."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from ai_platform.graph import (
    ActionKind,
    MemoryCheckpointer,
    StreamingWorkflow,
    WorkflowRunConflictError,
)


def main() -> None:
    """여덟 개의 동시 승인 재전송 중 하나만 execute update를 내보냄을 출력한다."""
    checkpointer = MemoryCheckpointer()
    workflow = StreamingWorkflow(checkpointer=checkpointer)
    run_id = "streaming-concurrent-approval-demo-001"
    list(
        workflow.stream(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def approve_once() -> tuple[str, tuple[str, ...]] | str:
        barrier.wait(timeout=5)
        try:
            updates = tuple(workflow.resume_stream(run_id=run_id, approved=True))
        except WorkflowRunConflictError:
            return "conflict"
        return updates[-1].state.status.value, tuple(
            update.event.node for update in updates
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: approve_once(), range(8)))

    completed = sum(
        outcome == ("completed", ("approval", "execute")) for outcome in outcomes
    )
    conflicts = outcomes.count("conflict")
    terminal = checkpointer.load(run_id=run_id)
    print(f"completed={completed}")
    print(f"conflicts={conflicts}")
    print(f"events={' | '.join(event.node for event in terminal.events)}")


if __name__ == "__main__":
    main()
