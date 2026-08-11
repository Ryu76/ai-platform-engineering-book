"""정규화 뒤 같은 JSON 경로를 쓰는 독립 Checkpointer의 동시 거절 예제."""
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
    """서로 다른 경로 표기의 여덟 거절 중 하나만 오프라인 비실행 종료를 기록한다."""
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
        run_id = "json-normalized-path-rejection-demo-001"
        adapters[0].start(
            request=StartWorkflowRequest(
                run_id=run_id,
                task="학습용 배포를 준비한다",
                action=ActionKind.DEPLOY,
            )
        )
        barrier = Barrier(8)

        def reject_once(index: int) -> str:
            barrier.wait(timeout=5)
            try:
                return adapters[index].resume(
                    run_id=run_id,
                    request=ApprovalRequest(approved=False),
                ).status.value
            except WorkflowRunConflictError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(reject_once, range(8)))

        rejected = JsonFileCheckpointer(path=checkpoint_path).load(run_id=run_id)
        print(f"rejected={outcomes.count('rejected')}")
        print(f"conflicts={outcomes.count('conflict')}")
        print(f"checkpoint={rejected.status.value}")
        print(f"approval_granted={rejected.approval_granted}")
        print(f"events={' | '.join(event.node for event in rejected.events)}")


if __name__ == "__main__":
    main()
