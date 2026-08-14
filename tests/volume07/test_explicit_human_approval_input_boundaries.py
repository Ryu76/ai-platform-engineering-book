"""Offline contracts for strict, explicit human-approval input boundaries in Volume 07."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

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
    WorkflowConfigurationError,
)


@dataclass(frozen=True)
class ApprovalCase:
    """One local workflow invocation and all boundaries that must remain uncalled."""

    run: Callable[[object], object]
    call_histories: tuple[list[object], ...]


def mock_agent(role: str, response: AgentResponse) -> DeterministicMockAgent:
    """Create one deterministic local role with one immutable response."""
    return DeterministicMockAgent(role=role, responses=(response,))


def build_review_case() -> ApprovalCase:
    """Build an approval-gated review flow without invoking its roles."""
    planner = mock_agent("planner", AgentResponse("plan"))
    researcher = mock_agent("researcher", AgentResponse("evidence"))
    developer = mock_agent("developer", AgentResponse("draft"))
    reviewer = mock_agent("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = mock_agent("qa", AgentResponse("qa passed"))
    workflow = BoundedReviewWorkflow(
        planner=planner,
        researcher=researcher,
        developer=developer,
        reviewer=reviewer,
        qa=qa,
        max_review_cycles=1,
    )
    return ApprovalCase(
        run=lambda approval: workflow.run(task="Review local work.", human_approval=approval),
        call_histories=(planner.calls, researcher.calls, developer.calls, reviewer.calls, qa.calls),
    )


def build_delegation_case() -> ApprovalCase:
    """Build an approval-gated delegation flow without invoking its boundaries."""
    coordinator = DeterministicMockCoordinator(
        plans=(
            DelegationPlan(
                "Prepare local assets.",
                (DelegationTask("draft", "writer", "Write a local draft."),),
            ),
        )
    )
    writer = DeterministicMockWorker(
        role="writer", responses=(WorkerResponse("draft complete", True),)
    )
    workflow = ApprovalGatedDelegationWorkflow(
        coordinator=coordinator,
        workers={"writer": writer},
        allowed_assignees=frozenset({"writer"}),
        max_tasks=1,
        max_worker_attempts=1,
    )
    return ApprovalCase(
        run=lambda approval: workflow.run(
            objective="Delegate local work.", human_approval=approval
        ),
        call_histories=(coordinator.calls, writer.calls),
    )


def build_conflict_case() -> ApprovalCase:
    """Build an approval-gated exact-consensus flow without invoking either peer."""
    planner = DeterministicMockConflictAgent(
        role="planner", proposals=(ConflictProposal("local", "Use local work."),)
    )
    reviewer = DeterministicMockConflictAgent(
        role="reviewer", proposals=(ConflictProposal("local", "Keep it auditable."),)
    )
    workflow = BoundedConflictResolutionWorkflow(
        agents={"planner": planner, "reviewer": reviewer}, max_agents=2, max_rounds=1
    )
    return ApprovalCase(
        run=lambda approval: workflow.run(
            objective="Choose a local option.", human_approval=approval
        ),
        call_histories=(planner.calls, reviewer.calls),
    )


def build_release_case() -> ApprovalCase:
    """Build an approval-gated local handoff flow without invoking its roles."""
    planner = mock_agent("planner", AgentResponse("plan"))
    developer = mock_agent("developer", AgentResponse("draft"))
    reviewer = mock_agent("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = mock_agent("qa", AgentResponse("qa passed"))
    devops = mock_agent("devops", AgentResponse("local handoff only"))
    workflow = ApprovalGatedReleaseHandoffWorkflow(
        planner=planner,
        developer=developer,
        reviewer=reviewer,
        qa=qa,
        devops=devops,
        max_review_cycles=1,
    )
    return ApprovalCase(
        run=lambda approval: workflow.run(task="Prepare a local handoff.", human_approval=approval),
        call_histories=(planner.calls, developer.calls, reviewer.calls, qa.calls, devops.calls),
    )


@pytest.mark.parametrize(
    ("build_case", "invalid_approval"),
    [
        (build_review_case, "approved"),
        (build_delegation_case, HumanApproval.APPROVED),
        (build_conflict_case, DelegationApproval.APPROVED),
        (build_release_case, ConflictApproval.APPROVED),
    ],
    ids=(
        "review-raw-string",
        "delegation-foreign-enum",
        "conflict-foreign-enum",
        "release-foreign-enum",
    ),
)
def test_only_the_workflow_specific_approval_enum_can_open_a_local_gate(
    build_case: Callable[[], ApprovalCase], invalid_approval: object
) -> None:
    """Raw strings and a different workflow's enum fail before every local Agent call."""
    case = build_case()

    with pytest.raises(WorkflowConfigurationError, match="human_approval must be"):
        case.run(invalid_approval)

    assert all(history == [] for history in case.call_histories)
