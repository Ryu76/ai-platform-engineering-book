"""Offline configuration tests for inaccessible Volume 07 agent protocol properties."""

from __future__ import annotations

import pytest

from ai_platform.agents import (
    AgentResponse,
    ApprovalGatedDelegationWorkflow,
    ApprovalGatedReleaseHandoffWorkflow,
    BoundedConflictResolutionWorkflow,
    BoundedReviewWorkflow,
    ConflictProposal,
    DeterministicMockAgent,
    DeterministicMockConflictAgent,
    DeterministicMockWorker,
    ReviewDecision,
    WorkerResponse,
    WorkflowConfigurationError,
)


class UnreadableActBoundary:
    """A local test double whose protocol accessor fails before an invocation exists."""

    @property
    def act(self) -> object:
        raise RuntimeError("local test boundary accessor failed")


class UnreadableProposeBoundary:
    """A local test double whose proposal accessor fails during configuration."""

    @property
    def propose(self) -> object:
        raise RuntimeError("local test boundary accessor failed")


def mock_agent(role: str, response: AgentResponse | None = None) -> DeterministicMockAgent:
    """Create one valid fixed local role boundary."""
    return DeterministicMockAgent(role=role, responses=(response or AgentResponse(role),))


def test_review_workflow_converts_unreadable_act_accessor_before_any_call() -> None:
    """An inaccessible Planner protocol property is not allowed to leak an accessor error."""
    researcher = mock_agent("researcher")
    developer = mock_agent("developer")
    reviewer = mock_agent("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = mock_agent("qa")

    with pytest.raises(
        WorkflowConfigurationError, match="planner act boundary could not be read"
    ):
        BoundedReviewWorkflow(
            planner=UnreadableActBoundary(),  # type: ignore[arg-type]
            researcher=researcher,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
        )

    assert researcher.calls == developer.calls == reviewer.calls == qa.calls == []


def test_release_handoff_converts_unreadable_act_accessor_before_any_call() -> None:
    """An inaccessible DevOps protocol property fails during setup, not after QA approval."""
    planner = mock_agent("planner")
    developer = mock_agent("developer")
    reviewer = mock_agent("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = mock_agent("qa")

    with pytest.raises(
        WorkflowConfigurationError, match="devops act boundary could not be read"
    ):
        ApprovalGatedReleaseHandoffWorkflow(
            planner=planner,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
            devops=UnreadableActBoundary(),  # type: ignore[arg-type]
        )

    assert planner.calls == developer.calls == reviewer.calls == qa.calls == []


def test_delegation_converts_unreadable_propose_accessor_before_worker_call() -> None:
    """An inaccessible Coordinator property fails before its plan or a Worker can run."""
    writer = DeterministicMockWorker(
        role="writer", responses=(WorkerResponse("done", True),)
    )

    with pytest.raises(
        WorkflowConfigurationError, match="coordinator propose boundary could not be read"
    ):
        ApprovalGatedDelegationWorkflow(
            coordinator=UnreadableProposeBoundary(),  # type: ignore[arg-type]
            workers={"writer": writer},
            allowed_assignees=frozenset({"writer"}),
        )

    assert writer.calls == []


def test_conflict_workflow_converts_unreadable_propose_accessor_before_peer_call() -> None:
    """An inaccessible proposal boundary stops setup before any conflict round begins."""
    reviewer = DeterministicMockConflictAgent(
        role="reviewer", proposals=(ConflictProposal("local", "rationale"),)
    )

    with pytest.raises(
        WorkflowConfigurationError, match="agent for planner propose boundary could not be read"
    ):
        BoundedConflictResolutionWorkflow(
            agents={
                "planner": UnreadableProposeBoundary(),  # type: ignore[dict-item]
                "reviewer": reviewer,
            },
            max_agents=2,
        )

    assert reviewer.calls == []
