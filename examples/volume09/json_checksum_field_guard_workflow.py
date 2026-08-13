"""JSON Checkpoint checksum 필드 변조를 안전하게 거부하는 오프라인 예제."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.graph import ActionKind, JsonFileCheckpointer, WorkflowState


def main() -> None:
    """유효한 형식의 잘못된 digest도 상태 복원 전에 차단한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        checkpointer.save(
            run_id="json-checksum-field-guard-demo-001",
            state=WorkflowState.start(
                task="로컬 문서를 읽는다", action=ActionKind.READ
            ),
        )
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        payload["payload_sha256"] = "0" * 64
        checkpoint_path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

        try:
            checkpointer.load(run_id="json-checksum-field-guard-demo-001")
        except ValueError as error:
            print(f"checksum_field_rejected={error}")
        else:
            raise AssertionError("replaced checksum field must be rejected")


if __name__ == "__main__":
    main()
