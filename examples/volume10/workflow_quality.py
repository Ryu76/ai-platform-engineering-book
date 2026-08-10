"""고정 Router 선택과 Agent Task Success를 외부 호출 없이 평가한다."""
from __future__ import annotations

from ai_platform.evaluation import (
    FIXED_RECORDED_WORKFLOWS,
    FIXED_WORKFLOW_CASES,
    evaluate_workflows,
)


def main() -> None:
    """고정 워크플로 평가 기준선을 사람이 읽을 수 있는 형식으로 출력한다."""
    metrics = evaluate_workflows(FIXED_WORKFLOW_CASES, FIXED_RECORDED_WORKFLOWS)
    print(f"Evaluation cases: {metrics.cases_evaluated}")
    print(f"Router accuracy: {metrics.router_accuracy:.6f}")
    print(f"Agent task success rate: {metrics.agent_task_success_rate:.6f}")


if __name__ == "__main__":
    main()
