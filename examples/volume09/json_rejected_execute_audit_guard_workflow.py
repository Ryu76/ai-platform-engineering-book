"""거절된 위험 JSON Checkpoint의 위조 execute 감사 이벤트를 차단하는 오프라인 데모."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.graph import ActionKind, DeterministicWorkflow, JsonFileCheckpointer


def main() -> None:
    """정상 거절 이력 뒤의 execute 이벤트가 복원 전에 거부됨을 출력한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        run_id = "rejected-execute-audit-guard-demo-001"
        workflow = DeterministicWorkflow(checkpointer=checkpointer)
        workflow.invoke(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
        rejected = workflow.resume(run_id=run_id, approved=False)
        assert rejected.status.value == "rejected"

        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        state = payload["checkpoints"][run_id]
        state["events"].append(
            {
                "sequence": 4,
                "node": "execute",
                "detail": "외부 시스템을 변경하지 않는 결정론적 실행 결과를 만들었습니다.",
            }
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
            print(f"rejected_execute_audit_rejected={error}")


if __name__ == "__main__":
    main()
