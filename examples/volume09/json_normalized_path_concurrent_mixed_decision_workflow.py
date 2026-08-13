"""정규화 뒤 같은 JSON 경로를 쓰는 독립 Checkpointer의 동시 상반 승인 예제."""
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
    """승인과 거절이 경합해도 하나의 엄격한 Boolean 결정만 기록한다."""
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
        run_id = "json-normalized-path-mixed-decision-demo-001"
        adapters[0].start(
            request=StartWorkflowRequest(
                run_id=run_id,
                task="학습용 배포를 준비한다",
                action=ActionKind.DEPLOY,
            )
        )
        decisions = (True, False, True, False, True, False, True, False)
        barrier = Barrier(len(decisions))

        def decide_once(index: int) -> str:
            barrier.wait(timeout=5)
            try:
                return adapters[index].resume(
                    run_id=run_id,
                    request=ApprovalRequest(approved=decisions[index]),
                ).status.value
            except WorkflowRunConflictError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=len(decisions)) as executor:
            outcomes = list(executor.map(decide_once, range(len(decisions))))

        terminal = JsonFileCheckpointer(path=checkpoint_path).load(run_id=run_id)
        print(f"completed={outcomes.count('completed')}")
        print(f"rejected={outcomes.count('rejected')}")
        print(f"conflicts={outcomes.count('conflict')}")
        print(f"checkpoint={terminal.status.value}")
        print(f"approval_granted={terminal.approval_granted}")
        print(f"events={' | '.join(event.node for event in terminal.events)}")


if __name__ == "__main__":
    main()
