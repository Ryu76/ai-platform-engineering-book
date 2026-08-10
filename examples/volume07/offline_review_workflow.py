"""Run the Volume 07 review workflow entirely with deterministic local mock agents."""

from __future__ import annotations

import argparse

from ai_platform.agents import (
    AgentResponse,
    BoundedReviewWorkflow,
    DeterministicMockAgent,
    HumanApproval,
    ReviewDecision,
)


def mock_agent(role: str, *responses: AgentResponse) -> DeterministicMockAgent:
    """Build a role with fixed local responses; no API client or tool is involved."""
    return DeterministicMockAgent(role=role, responses=responses)


def build_workflow() -> BoundedReviewWorkflow:
    """Build one reproducible planner-to-QA demonstration workflow."""
    return BoundedReviewWorkflow(
        planner=mock_agent(
            "planner", AgentResponse("Plan: define the offline acceptance criteria.")
        ),
        researcher=mock_agent(
            "researcher", AgentResponse("Evidence: use only repository-local fixtures.")
        ),
        developer=mock_agent("developer", AgentResponse("Draft: bounded workflow implementation.")),
        reviewer=mock_agent(
            "reviewer",
            AgentResponse("Review: acceptance criteria are met.", ReviewDecision.APPROVE),
        ),
        qa=mock_agent("qa", AgentResponse("QA: deterministic checks passed.")),
        max_review_cycles=2,
    )


def main() -> None:
    """Print the audit trail and leave QA paused unless a human passes --approve."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", action="store_true", help="explicitly approve QA after review")
    arguments = parser.parse_args()
    approval = HumanApproval.APPROVED if arguments.approve else HumanApproval.PENDING
    result = build_workflow().run(
        task="Publish an offline multi-agent example.", human_approval=approval
    )

    print(f"status={result.status.value}")
    print(f"review_cycles={result.review_cycles}")
    for message in result.messages:
        print(f"{message.iteration}:{message.role}: {message.content}")


if __name__ == "__main__":
    main()
