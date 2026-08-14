"""승인보다 앞선 위험 execute 감사 이벤트를 차단하는 오프라인 JSON 데모."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ai_platform.graph import ActionKind, DeterministicWorkflow, JsonFileCheckpointer


def main() -> None:
    """재계산 checksum도 승인 전 execute 감사 순서를 우회하지 못함을 출력한다."""
    with TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "checkpoints.json"
        checkpointer = JsonFileCheckpointer(path=checkpoint_path)
        run_id = "execute-after-approval-guard-demo-001"
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
                    "node": "execute",
                    "detail": "외부 시스템을 변경하지 않는 결정론적 실행 결과를 만들었습니다.",
                },
                {
                    "sequence": 4,
                    "node": "approval",
                    "detail": "사람 승인을 받았습니다. 실행 시뮬레이션으로 이동합니다.",
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
            print(f"execute_before_approval_rejected={error}")


if __name__ == "__main__":
    main()
