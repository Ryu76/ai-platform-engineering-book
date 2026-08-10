"""위험 작업의 승인 경계를 보이는 결정론적 상태 Streaming 예제."""
from __future__ import annotations

from collections.abc import Iterable

from ai_platform.graph import ActionKind, StreamingWorkflow, StreamUpdate


def print_updates(updates: Iterable[StreamUpdate]) -> None:
    """완료된 Node의 순서, 상태, 감사 설명을 한 줄씩 표시한다."""
    for update in updates:
        print(
            f"{update.event.sequence}:{update.event.node} "
            f"status={update.state.status} detail={update.event.detail}"
        )


def main() -> None:
    """실제 배포 없이 approval interrupt 전후의 상태 업데이트를 표시한다."""
    workflow = StreamingWorkflow()
    print("initial_stream")
    print_updates(
        workflow.stream(
            run_id="streaming-demo-001",
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    print(f"checkpoint={workflow.checkpoint(run_id='streaming-demo-001').status}")
    print("approved_resume_stream")
    print_updates(
        workflow.resume_stream(run_id="streaming-demo-001", approved=True)
    )


if __name__ == "__main__":
    main()
