"""정규화 뒤 같은 JSON 경로를 쓰는 독립 Checkpointer의 동시 시작 예제."""
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
    """서로 다른 경로 표기의 여덟 시작 중 하나만 승인 대기를 기록한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        alias_directory = Path(directory) / "path-alias"
        alias_directory.mkdir()
        alias_path = alias_directory / ".." / checkpoint_path.name
        adapters = tuple(
            WorkflowApiAdapter(
                workflow=DeterministicWorkflow(
                    checkpointer=JsonFileCheckpointer(
                        path=checkpoint_path if index % 2 == 0 else alias_path
                    )
                )
            )
            for index in range(8)
        )
        request = StartWorkflowRequest(
            run_id="json-normalized-path-start-demo-001",
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

        waiting = JsonFileCheckpointer(path=checkpoint_path).load(run_id=request.run_id)
        print(f"waiting_for_approval={outcomes.count('waiting_for_approval')}")
        print(f"conflicts={outcomes.count('conflict')}")
        print(f"checkpoint={waiting.status.value}")
        print(f"approval_granted={waiting.approval_granted}")
        print(f"events={' | '.join(event.node for event in waiting.events)}")


if __name__ == "__main__":
    main()
