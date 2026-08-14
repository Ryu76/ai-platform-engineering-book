"""중복 JSON 키 Checkpoint를 fail-closed로 차단하는 오프라인 Volume 09 데모."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.graph import ActionKind, JsonFileCheckpointer, WorkflowState


def main() -> None:
    """유효한 Checkpoint에 중복 키를 삽입한 뒤 복원이 거부됨을 출력한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        checkpointer.save(
            run_id="duplicate-key-demo-001",
            state=WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ),
        )
        valid_payload = checkpoint_path.read_text(encoding="utf-8")
        checkpoint_path.write_text(
            valid_payload.replace(
                '  "schema_version": 2\n}',
                '  "schema_version": 2,\n  "schema_version": 2\n}',
            ),
            encoding="utf-8",
        )

        try:
            checkpointer.load(run_id="duplicate-key-demo-001")
        except ValueError as error:
            print(f"duplicate_key_rejected={error}")


if __name__ == "__main__":
    main()
