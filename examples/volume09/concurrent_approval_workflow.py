"""동시 승인 재전송이 하나의 오프라인 실행 결과만 기록하는 예제."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from ai_platform.graph import (
    ActionKind,
    ApprovalRequest,
    DeterministicWorkflow,
    MemoryCheckpointer,
    StartWorkflowRequest,
    WorkflowApiAdapter,
    WorkflowRunConflictError,
)


def main() -> None:
    """여덟 개의 승인 요청 중 하나만 Checkpoint를 소비함을 출력한다."""
    checkpointer = MemoryCheckpointer()
    adapter = WorkflowApiAdapter(workflow=DeterministicWorkflow(checkpointer=checkpointer))
    adapter.start(
        request=StartWorkflowRequest(
            run_id="approval-demo-001",
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def approve_once() -> str:
        barrier.wait(timeout=5)
        try:
            return adapter.resume(
                run_id="approval-demo-001",
                request=ApprovalRequest(approved=True),
            ).status.value
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: approve_once(), range(8)))

    completed = checkpointer.load(run_id="approval-demo-001")
    print(f"completed={outcomes.count('completed')}")
    print(f"conflicts={outcomes.count('conflict')}")
    print(f"checkpoint={completed.status.value}")
    print(f"events={' | '.join(event.node for event in completed.events)}")


if __name__ == "__main__":
    main()
