"""같은 JSON 경로를 여는 독립 Checkpointer의 동시 시작 안전성 예제."""
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
    """8개 독립 인스턴스가 같은 파일의 위험 run을 한 번만 만든다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        adapters = tuple(
            WorkflowApiAdapter(
                workflow=DeterministicWorkflow(
                    checkpointer=JsonFileCheckpointer(path=checkpoint_path)
                )
            )
            for _ in range(8)
        )
        request = StartWorkflowRequest(
            run_id="json-shared-path-start-demo-001",
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
        barrier = Barrier(8)

        def start_once(index: int) -> str:
            barrier.wait(timeout=5)
            try:
                return adapters[index].start(request=request).status.value
            except WorkflowRunConflictError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(start_once, range(8)))

        waiting = JsonFileCheckpointer(path=checkpoint_path).load(
            run_id="json-shared-path-start-demo-001"
        )
        print(f"waiting_for_approval={outcomes.count('waiting_for_approval')}")
        print(f"conflicts={outcomes.count('conflict')}")
        print(f"checkpoint={waiting.status.value}")
        print(f"events={' | '.join(event.node for event in waiting.events)}")


if __name__ == "__main__":
    main()
