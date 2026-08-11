"""Offline tests for deterministic Mock role labels at workflow configuration time."""

from __future__ import annotations

import pytest

from ai_platform.agents import (
    AgentResponse,
    ApprovalGatedDelegationWorkflow,
    ApprovalGatedReleaseHandoffWorkflow,
    BoundedConflictResolutionWorkflow,
    BoundedReviewWorkflow,
    ConflictProposal,
    DelegationPlan,
    DelegationTask,
    DeterministicMockAgent,
    DeterministicMockConflictAgent,
    DeterministicMockCoordinator,
    DeterministicMockWorker,
    ReviewDecision,
    WorkerResponse,
    WorkflowConfigurationError,
)


def mock_agent(role: str, response: AgentResponse | None = None) -> DeterministicMockAgent:
    """Create one valid fixed local role boundary."""
    return DeterministicMockAgent(role=role, responses=(response or AgentResponse(role),))


def test_review_workflow_rejects_mislabeled_mock_before_any_agent_call() -> None:
    """A developer Mock cannot silently occupy the planner boundary."""
    mislabeled_planner = mock_agent("developer")
    researcher = mock_agent("researcher")
    developer = mock_agent("developer")
    reviewer = mock_agent("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = mock_agent("qa")

    with pytest.raises(
        WorkflowConfigurationError, match="planner declared role must match 'planner'"
    ):
        BoundedReviewWorkflow(
            planner=mislabeled_planner,
            researcher=researcher,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
        )

    assert all(
        agent.calls == []
        for agent in (mislabeled_planner, researcher, developer, reviewer, qa)
    )


def test_release_handoff_rejects_mislabeled_mock_before_any_agent_call() -> None:
    """A QA Mock cannot silently occupy the DevOps handoff boundary."""
    planner = mock_agent("planner")
    developer = mock_agent("developer")
    reviewer = mock_agent("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = mock_agent("qa")
    mislabeled_devops = mock_agent("qa")

    with pytest.raises(
        WorkflowConfigurationError, match="devops declared role must match 'devops'"
    ):
        ApprovalGatedReleaseHandoffWorkflow(
            planner=planner,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
            devops=mislabeled_devops,
        )

    assert all(
        agent.calls == []
        for agent in (planner, developer, reviewer, qa, mislabeled_devops)
    )


def test_delegation_rejects_mislabeled_worker_before_coordinator_call() -> None:
    """A fixed worker label must match the immutable assignee allow-list key."""
    coordinator = DeterministicMockCoordinator(
        plans=(DelegationPlan("Local plan.", (DelegationTask("draft", "writer", "Write."),)),)
    )
    mislabeled_worker = DeterministicMockWorker(
        role="reviewer", responses=(WorkerResponse("done", True),)
    )

    with pytest.raises(
        WorkflowConfigurationError, match="worker for writer declared role must match 'writer'"
    ):
        ApprovalGatedDelegationWorkflow(
            coordinator=coordinator,
            workers={"writer": mislabeled_worker},
            allowed_assignees=frozenset({"writer"}),
        )

    assert coordinator.calls == mislabeled_worker.calls == []


def test_conflict_workflow_rejects_mislabeled_mock_before_peer_call() -> None:
    """A fixed proposal Mock must match its role-to-agent mapping key."""
    mislabeled_planner = DeterministicMockConflictAgent(
        role="reviewer", proposals=(ConflictProposal("local", "rationale"),)
    )
    reviewer = DeterministicMockConflictAgent(
        role="reviewer", proposals=(ConflictProposal("local", "rationale"),)
    )

    with pytest.raises(
        WorkflowConfigurationError, match="agent for planner declared role must match 'planner'"
    ):
        BoundedConflictResolutionWorkflow(
            agents={"planner": mislabeled_planner, "reviewer": reviewer}, max_agents=2
        )

    assert mislabeled_planner.calls == reviewer.calls == []