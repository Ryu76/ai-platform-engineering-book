"""Run a bounded conflict-resolution workflow with local mock agents only."""

from __future__ import annotations

import argparse

from ai_platform.agents import (
    BoundedConflictResolutionWorkflow,
    ConflictApproval,
    ConflictProposal,
    DeterministicMockConflictAgent,
)


def build_workflow() -> BoundedConflictResolutionWorkflow:
    """Build two reproducible, local agents that reach an exact consensus."""
    planner = DeterministicMockConflictAgent(
        role="planner",
        proposals=(
            ConflictProposal(
                "offline tutorial",
                "Use a tutorial that never sends data to a live service.",
            ),
        ),
    )
    reviewer = DeterministicMockConflictAgent(
        role="reviewer",
        proposals=(
            ConflictProposal(
                "offline tutorial",
                "The proposed tutorial has a reviewable local boundary.",
            ),
        ),
    )
    return BoundedConflictResolutionWorkflow(
        agents={"planner": planner, "reviewer": reviewer},
        max_agents=2,
        max_rounds=2,
    )


def main() -> None:
    """Show a consensus recommendation, then complete only with --approve."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", action="store_true", help="explicitly approve consensus")
    arguments = parser.parse_args()
    approval = ConflictApproval.APPROVED if arguments.approve else ConflictApproval.PENDING
    result = build_workflow().run(
        objective="Choose a safe tutorial plan.", human_approval=approval
    )

    print(f"status={result.status.value}")
    print(f"consensus_option={result.consensus_option or '-'}")
    for message in result.messages:
        print(f"{message.round}:{message.role}: {message.content}")


if __name__ == "__main__":
    main()
