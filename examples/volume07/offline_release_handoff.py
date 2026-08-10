"""Prepare an approval-gated, local release handoff with deterministic mock agents only."""

from __future__ import annotations

import argparse

from ai_platform.agents import (
    AgentResponse,
    ApprovalGatedReleaseHandoffWorkflow,
    DeterministicMockAgent,
    HumanApproval,
    ReviewDecision,
)


def mock_agent(role: str, *responses: AgentResponse) -> DeterministicMockAgent:
    """Create one fixed local role without an API, tool, or deployment client."""
    return DeterministicMockAgent(role=role, responses=responses)


def build_workflow() -> ApprovalGatedReleaseHandoffWorkflow:
    """Build a reproducible plan-to-handoff path whose final role is DevOps."""
    return ApprovalGatedReleaseHandoffWorkflow(
        planner=mock_agent("planner", AgentResponse("Plan: prepare a local release candidate.")),
        developer=mock_agent("developer", AgentResponse("Draft: bounded handoff implementation.")),
        reviewer=mock_agent(
            "reviewer",
            AgentResponse(
                "Review: the candidate is ready for QA.", ReviewDecision.APPROVE
            ),
        ),
        qa=mock_agent("qa", AgentResponse("QA: deterministic checks passed.")),
        devops=mock_agent(
            "devops", AgentResponse("Handoff: local release notes are ready; no deployment ran.")
        ),
        max_review_cycles=2,
    )


def main() -> None:
    """Show the review audit first; call QA and DevOps only with --approve."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", action="store_true", help="explicitly approve QA and handoff")
    arguments = parser.parse_args()
    approval = HumanApproval.APPROVED if arguments.approve else HumanApproval.PENDING
    result = build_workflow().run(
        task="Prepare a release handoff without deploying anything.", human_approval=approval
    )

    print(f"status={result.status.value}")
    print(f"handoff_note={result.handoff_note or '-'}")
    for message in result.messages:
        print(f"{message.iteration}:{message.role}: {message.content}")


if __name__ == "__main__":
    main()
