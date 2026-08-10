"""제한된 재시도와 Error Node를 보이는 오프라인 Workflow 예제."""
from __future__ import annotations

from ai_platform.graph import ActionKind, RetryPlan, RetryWorkflow


def main() -> None:
    """첫 실패 뒤 한 번만 재시도하여 완료하는 결정론적 경로를 출력한다."""
    state = RetryWorkflow().invoke(
        run_id="retry-demo-001",
        task="로컬 문자열을 변환한다",
        action=ActionKind.TRANSFORM,
        retry_plan=RetryPlan(failures_before_success=1, max_retries=1),
    )
    print(f"status={state.status}")
    print(f"attempts={state.attempt_count}")
    print(f"events={' | '.join(event.node for event in state.events)}")


if __name__ == "__main__":
    main()
