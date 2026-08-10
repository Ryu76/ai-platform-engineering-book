"""프로세스 재생성 뒤에도 승인 경계를 보존하는 로컬 Checkpoint 예제."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.graph import ActionKind, DeterministicWorkflow, JsonFileCheckpointer


def main() -> None:
    """임시 디렉터리의 JSON Checkpoint에서 위험 작업을 안전하게 재개한다."""
    with TemporaryDirectory(prefix="volume09-checkpoint-") as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        waiting = DeterministicWorkflow(
            checkpointer=JsonFileCheckpointer(path=checkpoint_path)
        ).invoke(
            run_id="persistent-demo-001",
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
        print(f"before_restart={waiting.status}")
        print(f"events={' | '.join(event.node for event in waiting.events)}")

        restarted_workflow = DeterministicWorkflow(
            checkpointer=JsonFileCheckpointer(path=checkpoint_path)
        )
        restored = restarted_workflow.checkpoint(run_id="persistent-demo-001")
        print(f"after_restart={restored.status}")

        completed = restarted_workflow.resume(run_id="persistent-demo-001", approved=True)
        print(f"after_approval={completed.status}")
        print(f"events={' | '.join(event.node for event in completed.events)}")


if __name__ == "__main__":
    main()
