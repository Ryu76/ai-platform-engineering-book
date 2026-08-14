"""재계산된 checksum도 상반된 위험 승인 감사 기록을 우회하지 못하게 하는 오프라인 데모."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.graph import ActionKind, DeterministicWorkflow, JsonFileCheckpointer


def main() -> None:
    """거절·승인이 함께 있는 위험 완료 Checkpoint가 거부됨을 출력한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        run_id = "approval-audit-guard-demo-001"
        waiting = DeterministicWorkflow(checkpointer=checkpointer).invoke(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
        assert waiting.status.value == "waiting_for_approval"

        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        state = payload["checkpoints"][run_id]
        state["status"] = "completed"
        state["approval_granted"] = True
        state["result"] = "오프라인 시뮬레이션 완료: deploy / 학습용 배포를 준비한다"
        state["events"].extend(
            [
                {
                    "sequence": 3,
                    "node": "approval",
                    "detail": "사람이 작업을 거절했습니다. 실행하지 않습니다.",
                },
                {
                    "sequence": 4,
                    "node": "approval",
                    "detail": "사람 승인을 받았습니다. 실행 시뮬레이션으로 이동합니다.",
                },
                {
                    "sequence": 5,
                    "node": "execute",
                    "detail": "외부 시스템을 변경하지 않는 결정론적 실행 결과를 만들었습니다.",
                },
            ]
        )
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
            print(f"conflicting_approval_audit_rejected={error}")


if __name__ == "__main__":
    main()
