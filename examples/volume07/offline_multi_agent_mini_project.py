"""Run the Volume 07 offline mini project with deterministic local Mock agents only.

Each workflow has its own approval flag. Omitting a flag leaves that stage at its
explicit human-approval gate; this script does not invoke live APIs, tools, secrets,
or deployments.
"""

from __future__ import annotations

import argparse

from ai_platform.agents import (
    AgentResponse,
    ApprovalGatedDelegationWorkflow,
    ApprovalGatedReleaseHandoffWorkflow,
    BoundedConflictResolutionWorkflow,
    BoundedReviewWorkflow,
    ConflictApproval,
    ConflictProposal,
    DelegationApproval,
    DelegationPlan,
    DelegationTask,
    DeterministicMockAgent,
    DeterministicMockConflictAgent,
    DeterministicMockCoordinator,
    DeterministicMockWorker,
    HumanApproval,
    ReviewDecision,
    WorkerResponse,
)


def mock_agent(role: str, response: AgentResponse) -> DeterministicMockAgent:
    """Create one local role with exactly one immutable scripted response."""
    return DeterministicMockAgent(role=role, responses=(response,))


def build_review_workflow() -> BoundedReviewWorkflow:
    """Build a review path that has one bounded review cycle before its QA gate."""
    return BoundedReviewWorkflow(
        planner=mock_agent("planner", AgentResponse("Plan: define local acceptance criteria.")),
        researcher=mock_agent("researcher", AgentResponse("Evidence: use only local fixtures.")),
        developer=mock_agent("developer", AgentResponse("Draft: offline multi-agent guide.")),
        reviewer=mock_agent(
            "reviewer",
            AgentResponse("Review: local acceptance criteria are met.", ReviewDecision.APPROVE),
        ),
        qa=mock_agent("qa", AgentResponse("QA: local deterministic checks passed.")),
        max_review_cycles=1,
    )


def build_delegation_workflow() -> ApprovalGatedDelegationWorkflow:
    """Build a two-task manifest with fixed, bounded local worker outcomes."""
    coordinator = DeterministicMockCoordinator(
        plans=(
            DelegationPlan(
                "Prepare the local tutorial assets.",
                (
                    DelegationTask("draft", "writer", "Write the local tutorial draft."),
                    DelegationTask("verify", "checker", "Verify the tutorial locally."),
                ),
            ),
        )
    )
    workers = {
        "writer": DeterministicMockWorker(
            role="writer", responses=(WorkerResponse("Draft asset is ready.", True),)
        ),
        "checker": DeterministicMockWorker(
            role="checker", responses=(WorkerResponse("Local verification passed.", True),)
        ),
    }
    return ApprovalGatedDelegationWorkflow(
        coordinator=coordinator,
        workers=workers,
        allowed_assignees=frozenset(workers),
        max_tasks=2,
        max_worker_attempts=1,
    )


def build_conflict_workflow() -> BoundedConflictResolutionWorkflow:
    """Build two peers that make one exact-consensus local recommendation."""
    return BoundedConflictResolutionWorkflow(
        agents={
            "planner": DeterministicMockConflictAgent(
                role="planner",
                proposals=(ConflictProposal("offline tutorial", "Keep every step local."),),
            ),
            "reviewer": DeterministicMockConflictAgent(
                role="reviewer",
                proposals=(
                    ConflictProposal("offline tutorial", "The local plan remains auditable."),
                ),
            ),
        },
        max_agents=2,
        max_rounds=1,
    )


def build_release_workflow() -> ApprovalGatedReleaseHandoffWorkflow:
    """Build a local handoff path; its DevOps Mock creates a note, never deploys."""
    return ApprovalGatedReleaseHandoffWorkflow(
        planner=mock_agent("planner", AgentResponse("Plan: prepare a local release candidate.")),
        developer=mock_agent("developer", AgentResponse("Draft: local release handoff.")),
        reviewer=mock_agent(
            "reviewer",
            AgentResponse("Review: candidate is ready for local QA.", ReviewDecision.APPROVE),
        ),
        qa=mock_agent("qa", AgentResponse("QA: local handoff checks passed.")),
        devops=mock_agent(
            "devops", AgentResponse("Handoff: local release note ready; no deployment ran.")
        ),
        max_review_cycles=1,
    )


def main() -> None:
    """Run four isolated local stages, approving only the gates selected by a human."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--approve-review", action="store_true", help="approve the review workflow QA gate"
    )
    parser.add_argument(
        "--approve-delegation", action="store_true", help="approve the delegation manifest"
    )
    parser.add_argument(
        "--approve-conflict", action="store_true", help="approve the consensus"
    )
    parser.add_argument(
        "--approve-release", action="store_true", help="approve QA and local handoff"
    )
    arguments = parser.parse_args()

    review_approval = HumanApproval.APPROVED if arguments.approve_review else HumanApproval.PENDING
    delegation_approval = (
        DelegationApproval.APPROVED if arguments.approve_delegation else DelegationApproval.PENDING
    )
    conflict_approval = (
        ConflictApproval.APPROVED if arguments.approve_conflict else ConflictApproval.PENDING
    )
    release_approval = (
        HumanApproval.APPROVED if arguments.approve_release else HumanApproval.PENDING
    )

    review_result = build_review_workflow().run(
        task="Prepare the offline multi-agent tutorial.", human_approval=review_approval
    )
    delegation_result = build_delegation_workflow().run(
        objective="Prepare local tutorial assets.", human_approval=delegation_approval
    )
    conflict_result = build_conflict_workflow().run(
        objective="Choose the tutorial execution boundary.", human_approval=conflict_approval
    )
    release_result = build_release_workflow().run(
        task="Prepare the local tutorial handoff.", human_approval=release_approval
    )

    print(f"review_status={review_result.status.value}")
    print(f"delegation_status={delegation_result.status.value}")
    print(f"delegation_completed_task_ids={','.join(delegation_result.completed_task_ids) or '-'}")
    print(f"conflict_status={conflict_result.status.value}")
    print(f"conflict_consensus_option={conflict_result.consensus_option or '-'}")
    print(f"release_status={release_result.status.value}")
    print(f"release_handoff_note={release_result.handoff_note or '-'}")


if __name__ == "__main__":
    main()
