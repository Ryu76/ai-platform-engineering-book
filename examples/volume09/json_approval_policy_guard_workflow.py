"""재계산된 checksum도 위험 승인 정책을 우회하지 못하게 하는 오프라인 데모."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.graph import ActionKind, JsonFileCheckpointer, WorkflowState, WorkflowStatus


def main() -> None:
    """위험 작업을 READY로 바꾼 재계산 Checkpoint가 거부됨을 출력한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        run_id = "approval-policy-guard-demo-001"
        checkpointer.save(
            run_id=run_id,
            state=WorkflowState.start(
                task="학습용 배포를 준비한다", action=ActionKind.DEPLOY
            ).record(
                node="plan",
                detail="오프라인 계획을 만듭니다.",
                status=WorkflowStatus.PLANNED,
            ),
        )
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        state = payload["checkpoints"][run_id]
        state["status"] = "ready"
        state["approval_required"] = False
        state["approval_granted"] = True
        canonical_payload = json.dumps(
            {
                "schema_version": payload["schema_version"],
                "checkpoints": payload["checkpoints"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        payload["payload_sha256"] = hashlib.sha256(canonical_payload).hexdigest()
        checkpoint_path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )

        try:
            checkpointer.load(run_id=run_id)
        except ValueError as error:
            print(f"approval_policy_bypass_rejected={error}")


if __name__ == "__main__":
    main()
