"""JSON Checkpoint hard link 별칭을 안전하게 거부하는 오프라인 예제."""
from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.graph import ActionKind, JsonFileCheckpointer, WorkflowState


def main() -> None:
    """원자적 교체 전에 기존 hard link 별칭을 명시적으로 차단한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        checkpointer.save(
            run_id="json-hard-link-guard-demo-001",
            state=WorkflowState.start(
                task="로컬 문서를 읽는다", action=ActionKind.READ
            ),
        )
        hard_link_path = Path(directory) / "checkpoints-hard-link.json"
        os.link(checkpoint_path, hard_link_path)

        try:
            JsonFileCheckpointer(path=hard_link_path)
        except ValueError as error:
            print(f"hard_link_rejected={error}")
        else:
            raise AssertionError("existing hard link must be rejected")


if __name__ == "__main__":
    main()
