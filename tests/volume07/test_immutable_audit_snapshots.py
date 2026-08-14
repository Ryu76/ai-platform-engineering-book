"""Offline contracts for immutable per-call audit snapshots in Volume 07."""

from __future__ import annotations

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


def mock_agent(role: str, *responses: AgentResponse) -> DeterministicMockAgent:
    """Create a local role with an immutable fixed response script."""
    return DeterministicMockAgent(role=role, responses=responses)


def test_review_contexts_are_immutable_snapshots_of_prior_roles() -> None:
    """Later QA output must not appear in earlier review-role contexts."""
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

    result = workflow.run(
        task="Verify local audit snapshots.", human_approval=HumanApproval.APPROVED
    )

    assert planner.calls[0].messages == ()
    assert [message.role for message in researcher.calls[0].messages] == ["planner"]
    assert [message.role for message in developer.calls[0].messages] == ["planner", "researcher"]
    assert [message.role for message in reviewer.calls[0].messages] == [
        "planner",
        "researcher",
        "developer",
    ]
    assert [message.role for message in qa.calls[0].messages] == [
        "planner",
        "researcher",
        "developer",
        "reviewer",
    ]
    assert [message.role for message in result.messages] == [
        "planner",
        "researcher",
        "developer",
        "reviewer",
        "qa",
    ]
    assert isinstance(reviewer.calls[0].messages, tuple)
    assert len(reviewer.calls[0].messages) == 3


def test_delegation_worker_contexts_snapshot_only_completed_prior_work() -> None:
    """A worker sees the manifest and prior attempts, never later assigned work."""
    coordinator = DeterministicMockCoordinator(
        plans=(
            DelegationPlan(
                "Use bounded local work.",
                (
                    DelegationTask("draft", "writer", "Write an offline draft."),
                    DelegationTask("verify", "checker", "Check the offline draft."),
                ),
            ),
        )
    )
    writer = DeterministicMockWorker(
        role="writer", responses=(WorkerResponse("draft complete", True),)
    )
    checker = DeterministicMockWorker(
        role="checker", responses=(WorkerResponse("checks complete", True),)
    )
    workflow = ApprovalGatedDelegationWorkflow(
        coordinator=coordinator,
        workers={"writer": writer, "checker": checker},
        allowed_assignees=frozenset({"writer", "checker"}),
        max_tasks=2,
        max_worker_attempts=1,
    )

    result = workflow.run(
        objective="Prepare bounded local work.", human_approval=DelegationApproval.APPROVED
    )

    assert coordinator.calls[0].messages == ()
    assert writer.calls[0].task is not None
    assert writer.calls[0].task.task_id == "draft"
    assert [message.role for message in writer.calls[0].messages] == ["coordinator"]
    assert checker.calls[0].task is not None
    assert checker.calls[0].task.task_id == "verify"
    assert [message.role for message in checker.calls[0].messages] == ["coordinator", "writer"]
    assert [message.role for message in result.messages] == ["coordinator", "writer", "checker"]
    assert isinstance(checker.calls[0].messages, tuple)
    assert len(writer.calls[0].messages) == 1


def test_conflict_peer_snapshot_excludes_later_consensus_policy() -> None:
    """Exact consensus is recorded only after both peers supplied their fixed proposals."""
    planner = DeterministicMockConflictAgent(
        role="planner", proposals=(ConflictProposal("offline", "Planner rationale."),)
    )
    reviewer = DeterministicMockConflictAgent(
        role="reviewer", proposals=(ConflictProposal("offline", "Reviewer rationale."),)
    )
    workflow = BoundedConflictResolutionWorkflow(
        agents={"planner": planner, "reviewer": reviewer}, max_agents=2, max_rounds=1
    )

    result = workflow.run(
        objective="Select a local option.", human_approval=ConflictApproval.APPROVED
    )

    assert planner.calls[0].messages == ()
    assert [message.role for message in reviewer.calls[0].messages] == ["planner"]
    assert [message.role for message in result.messages] == ["planner", "reviewer", "policy"]
    assert isinstance(reviewer.calls[0].messages, tuple)
    assert len(reviewer.calls[0].messages) == 1


def test_release_devops_snapshot_includes_qa_but_no_future_message() -> None:
    """DevOps receives only the approved local audit before it emits its handoff note."""
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

    result = workflow.run(task="Prepare a local handoff.", human_approval=HumanApproval.APPROVED)

    assert planner.calls[0].messages == ()
    assert [message.role for message in reviewer.calls[0].messages] == ["planner", "developer"]
    assert [message.role for message in qa.calls[0].messages] == [
        "planner",
        "developer",
        "reviewer",
    ]
    assert [message.role for message in devops.calls[0].messages] == [
        "planner",
        "developer",
        "reviewer",
        "qa",
    ]
    assert [message.role for message in result.messages] == [
        "planner",
        "developer",
        "reviewer",
        "qa",
        "devops",
    ]
    assert isinstance(devops.calls[0].messages, tuple)
    assert len(devops.calls[0].messages) == 4
