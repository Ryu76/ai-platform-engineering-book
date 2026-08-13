"""JSON Checkpoint checksum 불일치를 안전하게 거부하는 오프라인 예제."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.graph import ActionKind, JsonFileCheckpointer, WorkflowState


def main() -> None:
    """유효한 JSON의 변경도 checksum 불일치로 재개 전에 차단한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        checkpointer.save(
            run_id="json-checksum-guard-demo-001",
            state=WorkflowState.start(
                task="로컬 문서를 읽는다", action=ActionKind.READ
            ),
        )
        checkpoint_path.write_text(
            checkpoint_path.read_text(encoding="utf-8").replace(
                "로컬 문서를 읽는다", "로컬 문서를 변경한다"
            ),
            encoding="utf-8",
        )

        try:
            checkpointer.load(run_id="json-checksum-guard-demo-001")
        except ValueError as error:
            print(f"checksum_mismatch_rejected={error}")
        else:
            raise AssertionError("stale checksum must be rejected")


if __name__ == "__main__":
    main()
