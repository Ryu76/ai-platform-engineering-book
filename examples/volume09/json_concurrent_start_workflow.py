"""단일 JSON Checkpointer 인스턴스의 동시 시작 단일 생성 예제."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier

from ai_platform.graph import (
    ActionKind,
    DeterministicWorkflow,
    JsonFileCheckpointer,
    StartWorkflowRequest,
    WorkflowApiAdapter,
    WorkflowRunConflictError,
)


def main() -> None:
    """여덟 개의 시작 재전송 중 하나만 위험 작업의 승인 대기를 만든다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        adapter = WorkflowApiAdapter(
            workflow=DeterministicWorkflow(checkpointer=checkpointer)
        )
        request = StartWorkflowRequest(
            run_id="json-start-demo-001",
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
        barrier = Barrier(8)

        def start_once() -> str:
            barrier.wait(timeout=5)
            try:
                return adapter.start(request=request).status.value
            except WorkflowRunConflictError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(lambda _: start_once(), range(8)))

        waiting = checkpointer.load(run_id="json-start-demo-001")
        print(f"waiting_for_approval={outcomes.count('waiting_for_approval')}")
        print(f"conflicts={outcomes.count('conflict')}")
        print(f"checkpoint={waiting.status.value}")
        print(f"events={' | '.join(event.node for event in waiting.events)}")


if __name__ == "__main__":
    main()
