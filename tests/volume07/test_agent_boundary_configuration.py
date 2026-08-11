"""Offline configuration-boundary tests for Volume 07 multi-agent workflows."""

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
    WorkflowStatus,
)


def mock_agent(role: str) -> DeterministicMockAgent:
    """Create one fixed local role that records any unexpected invocation."""
    return DeterministicMockAgent(role=role, responses=(AgentResponse(f"{role} result"),))


def test_review_and_release_workflows_reject_non_callable_role_boundaries() -> None:
    """Role objects without ``act`` are rejected before either workflow can run."""
    planner = mock_agent("planner")
    researcher = mock_agent("researcher")
    developer = mock_agent("developer")
    reviewer = mock_agent("reviewer")
    qa = mock_agent("qa")

    with pytest.raises(WorkflowConfigurationError, match="planner must provide a callable"):
        BoundedReviewWorkflow(
            planner=object(),
            researcher=researcher,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
        )

    with pytest.raises(WorkflowConfigurationError, match="devops must provide a callable"):
        ApprovalGatedReleaseHandoffWorkflow(
            planner=planner,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
            devops=object(),
        )

    assert planner.calls == researcher.calls == developer.calls == reviewer.calls == qa.calls == []


def test_delegation_rejects_non_callable_coordinator_and_worker_boundaries() -> None:
    """Planning and worker boundaries fail during setup, before an approved run."""
    plan = DelegationPlan("Local plan.", (DelegationTask("draft", "writer", "Write locally."),))
    writer = DeterministicMockWorker(role="writer", responses=(WorkerResponse("done", True),))

    with pytest.raises(WorkflowConfigurationError, match="coordinator must provide a callable"):
        ApprovalGatedDelegationWorkflow(
            coordinator=object(),
            workers={"writer": writer},
            allowed_assignees=frozenset({"writer"}),
        )

    with pytest.raises(
        WorkflowConfigurationError, match="worker for writer must provide a callable"
    ):
        ApprovalGatedDelegationWorkflow(
            coordinator=DeterministicMockCoordinator(plans=(plan,)),
            workers={"writer": object()},
            allowed_assignees=frozenset({"writer"}),
        )

    assert writer.calls == []


def test_delegation_requires_an_immutable_assignee_allow_list() -> None:
    """A mutable allow-list cannot change the configured execution boundary later."""
    coordinator = DeterministicMockCoordinator(
        plans=(
            DelegationPlan(
                "Local plan.", (DelegationTask("draft", "writer", "Write locally."),)
            ),
        )
    )
    writer = DeterministicMockWorker(role="writer", responses=(WorkerResponse("done", True),))

    with pytest.raises(WorkflowConfigurationError, match="immutable frozenset"):
        ApprovalGatedDelegationWorkflow(
            coordinator=coordinator,
            workers={"writer": writer},
            allowed_assignees={"writer"},  # type: ignore[arg-type]
        )

    assert coordinator.calls == []
    assert writer.calls == []


def test_conflict_workflow_rejects_non_callable_agent_boundaries() -> None:
    """A malformed conflict role cannot trigger its peer or a later round."""
    reviewer = DeterministicMockConflictAgent(
        role="reviewer", proposals=(ConflictProposal("local option", "Local rationale."),)
    )

    with pytest.raises(
        WorkflowConfigurationError, match="agent for planner must provide a callable"
    ):
        BoundedConflictResolutionWorkflow(
            agents={"planner": object(), "reviewer": reviewer}, max_agents=2
        )

    assert reviewer.calls == []


def test_callable_role_boundaries_still_allow_review_configuration() -> None:
    """The setup check is structural and preserves deterministic mock workflows."""
    planner = mock_agent("planner")
    researcher = mock_agent("researcher")
    developer = mock_agent("developer")
    reviewer = DeterministicMockAgent(
        role="reviewer", responses=(AgentResponse("approved", ReviewDecision.APPROVE),)
    )
    qa = mock_agent("qa")

    workflow = BoundedReviewWorkflow(
        planner=planner,
        researcher=researcher,
        developer=developer,
        reviewer=reviewer,
        qa=qa,
    )

    result = workflow.run(task="Prepare a local example.")

    assert result.status is WorkflowStatus.AWAITING_HUMAN_APPROVAL
    assert qa.calls == []
