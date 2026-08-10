"""Run an approval-gated Volume 07 delegation workflow with local mock agents only."""

from __future__ import annotations

import argparse

from ai_platform.agents import (
    ApprovalGatedDelegationWorkflow,
    DelegationApproval,
    DelegationPlan,
    DelegationTask,
    DeterministicMockCoordinator,
    DeterministicMockWorker,
    WorkerResponse,
)


def build_workflow() -> ApprovalGatedDelegationWorkflow:
    """Build one reproducible coordinator and two fixed offline workers."""
    coordinator = DeterministicMockCoordinator(
        plans=(
            DelegationPlan(
                "Prepare the tutorial with a bounded local handoff.",
                (
                    DelegationTask("draft", "writer", "Write the deterministic example."),
                    DelegationTask("verify", "checker", "Check the example output."),
                ),
            ),
        )
    )
    workers = {
        "writer": DeterministicMockWorker(
            role="writer", responses=(WorkerResponse("Draft is ready.", True),)
        ),
        "checker": DeterministicMockWorker(
            role="checker", responses=(WorkerResponse("Checks passed.", True),)
        ),
    }
    return ApprovalGatedDelegationWorkflow(
        coordinator=coordinator,
        workers=workers,
        allowed_assignees=frozenset(workers),
        max_tasks=2,
        max_worker_attempts=2,
    )


def main() -> None:
    """Show the manifest first and run no workers without --approve."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", action="store_true", help="explicitly approve the manifest")
    arguments = parser.parse_args()
    approval = DelegationApproval.APPROVED if arguments.approve else DelegationApproval.PENDING
    result = build_workflow().run(
        objective="Create an offline delegation tutorial.", human_approval=approval
    )

    print(f"status={result.status.value}")
    print(f"completed_task_ids={','.join(result.completed_task_ids) or '-'}")
    for message in result.messages:
        print(f"{message.attempt}:{message.role}:{message.task_id or '-'}: {message.content}")


if __name__ == "__main__":
    main()
