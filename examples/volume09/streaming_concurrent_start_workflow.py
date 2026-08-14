"""동시 Streaming 시작이 하나의 위험 승인 대기만 만드는 Volume 09 오프라인 데모."""
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
    """여덟 개의 동시 새 스트림 중 하나만 approval update까지 기록함을 출력한다."""
    checkpointer = MemoryCheckpointer()
    workflow = StreamingWorkflow(checkpointer=checkpointer)
    run_id = "streaming-concurrent-start-demo-001"
    barrier = Barrier(8)

    def start_once() -> tuple[str, tuple[str, ...]] | str:
        barrier.wait(timeout=5)
        try:
            updates = tuple(
                workflow.stream_new(
                    run_id=run_id,
                    task="학습용 배포를 준비한다",
                    action=ActionKind.DEPLOY,
                )
            )
        except WorkflowRunConflictError:
            return "conflict"
        return updates[-1].state.status.value, tuple(update.event.node for update in updates)

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: start_once(), range(8)))

    waiting = sum(outcome == ("waiting_for_approval", ("plan", "approval")) for outcome in outcomes)
    conflicts = outcomes.count("conflict")
    checkpoint = checkpointer.load(run_id=run_id)
    print(f"waiting={waiting}")
    print(f"conflicts={conflicts}")
    print(f"events={' | '.join(event.node for event in checkpoint.events)}")


if __name__ == "__main__":
    main()
