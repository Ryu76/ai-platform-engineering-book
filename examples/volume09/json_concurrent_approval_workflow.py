"""단일 JSON Checkpointer 인스턴스의 동시 승인 단일 소비 예제."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier

from ai_platform.graph import (
    ActionKind,
    ApprovalRequest,
    DeterministicWorkflow,
    JsonFileCheckpointer,
    StartWorkflowRequest,
    WorkflowApiAdapter,
    WorkflowRunConflictError,
)


def main() -> None:
    """여덟 개의 승인 재전송 중 하나만 로컬 JSON Checkpoint를 소비함을 출력한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        adapter = WorkflowApiAdapter(
            workflow=DeterministicWorkflow(checkpointer=checkpointer)
        )
        adapter.start(
            request=StartWorkflowRequest(
                run_id="json-approval-demo-001",
                task="학습용 배포를 준비한다",
                action=ActionKind.DEPLOY,
            )
        )
        barrier = Barrier(8)

        def approve_once() -> str:
            barrier.wait(timeout=5)
            try:
                return adapter.resume(
                    run_id="json-approval-demo-001",
                    request=ApprovalRequest(approved=True),
                ).status.value
            except WorkflowRunConflictError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(lambda _: approve_once(), range(8)))

        completed = checkpointer.load(run_id="json-approval-demo-001")
        print(f"completed={outcomes.count('completed')}")
        print(f"conflicts={outcomes.count('conflict')}")
        print(f"checkpoint={completed.status.value}")
        print(f"events={' | '.join(event.node for event in completed.events)}")


if __name__ == "__main__":
    main()
