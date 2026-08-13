"""Offline configuration tests for context-compatible Volume 07 Agent boundaries."""

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


class NoContextActBoundary:
    """Callable test double that is unsafe because ``act`` takes no context."""

    def act(self) -> AgentResponse:
        return AgentResponse("This must never run.")


class NoContextProposeBoundary:
    """Callable test double that is unsafe because ``propose`` takes no context."""

    def propose(self) -> object:
        return object()


class ExtraRequiredContextBoundary:
    """Callable test double that needs more than the workflow can provide."""

    def act(self, context: object, required: object) -> AgentResponse:
        return AgentResponse(f"This must never run: {context!r} {required!r}")


def agent(role: str, response: AgentResponse | None = None) -> DeterministicMockAgent:
    """Build one valid local Agent whose call history exposes unexpected execution."""
    return DeterministicMockAgent(role=role, responses=(response or AgentResponse(role),))


def test_review_and_release_reject_callable_act_boundaries_without_context() -> None:
    """A callable with the wrong arity cannot defer failure until a workflow run."""
    researcher = agent("researcher")
    developer = agent("developer")
    reviewer = agent("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = agent("qa")

    with pytest.raises(WorkflowConfigurationError, match="must accept one positional context"):
        BoundedReviewWorkflow(
            planner=NoContextActBoundary(),
            researcher=researcher,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
        )

    with pytest.raises(WorkflowConfigurationError, match="must accept one positional context"):
        ApprovalGatedReleaseHandoffWorkflow(
            planner=agent("planner"),
            developer=developer,
            reviewer=reviewer,
            qa=qa,
            devops=NoContextActBoundary(),
        )

    assert researcher.calls == developer.calls == reviewer.calls == qa.calls == []


def test_review_rejects_an_act_boundary_with_an_extra_required_argument() -> None:
    """A one-context workflow must not rely on a later call-time arity error."""
    researcher = agent("researcher")
    developer = agent("developer")
    reviewer = agent("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = agent("qa")

    with pytest.raises(WorkflowConfigurationError, match="must accept one positional context"):
        BoundedReviewWorkflow(
            planner=ExtraRequiredContextBoundary(),
            researcher=researcher,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
        )

    assert researcher.calls == developer.calls == reviewer.calls == qa.calls == []


def test_delegation_rejects_callable_boundaries_without_context() -> None:
    """Coordinator and Worker arity are both checked before plan or dispatch work."""
    plan = DelegationPlan("Local plan.", (DelegationTask("draft", "writer", "Write locally."),))
    writer = DeterministicMockWorker(role="writer", responses=(WorkerResponse("done", True),))

    with pytest.raises(WorkflowConfigurationError, match="must accept one positional context"):
        ApprovalGatedDelegationWorkflow(
            coordinator=NoContextProposeBoundary(),
            workers={"writer": writer},
            allowed_assignees=frozenset({"writer"}),
        )

    coordinator = DeterministicMockCoordinator(plans=(plan,))
    with pytest.raises(WorkflowConfigurationError, match="must accept one positional context"):
        ApprovalGatedDelegationWorkflow(
            coordinator=coordinator,
            workers={"writer": NoContextActBoundary()},
            allowed_assignees=frozenset({"writer"}),
        )

    assert coordinator.calls == []
    assert writer.calls == []


def test_conflict_rejects_callable_proposal_boundary_without_context() -> None:
    """A malformed peer cannot begin a bounded conflict round or call a valid peer."""
    reviewer = DeterministicMockConflictAgent(
        role="reviewer", proposals=(ConflictProposal("local option", "Local rationale."),)
    )

    with pytest.raises(WorkflowConfigurationError, match="must accept one positional context"):
        BoundedConflictResolutionWorkflow(
            agents={"planner": NoContextProposeBoundary(), "reviewer": reviewer},
            max_agents=2,
        )

    assert reviewer.calls == []
