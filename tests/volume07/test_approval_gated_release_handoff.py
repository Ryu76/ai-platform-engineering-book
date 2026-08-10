"""Offline contract tests for Volume 07's approval-gated release-handoff slice."""

from __future__ import annotations

import pytest

from ai_platform.agents import (
    AgentProtocolError,
    AgentResponse,
    ApprovalGatedReleaseHandoffWorkflow,
    DeterministicMockAgent,
    HumanApproval,
    ReleaseHandoffStatus,
    ReviewDecision,
    WorkflowConfigurationError,
)


def response(content: str, review: ReviewDecision | None = None) -> AgentResponse:
    """Create one fixed response without any live model or tool dependency."""
    return AgentResponse(content, review)


def build_workflow(
    *,
    developer_responses: tuple[AgentResponse, ...] = (response("Draft: local candidate."),),
    reviewer_responses: tuple[AgentResponse, ...] = (
        response("Review: candidate is acceptable.", ReviewDecision.APPROVE),
    ),
    cycles: int = 2,
) -> tuple[
    ApprovalGatedReleaseHandoffWorkflow,
    DeterministicMockAgent,
    DeterministicMockAgent,
    DeterministicMockAgent,
    DeterministicMockAgent,
    DeterministicMockAgent,
]:
    """Create five local roles and expose each call history for safety assertions."""
    planner = DeterministicMockAgent(role="planner", responses=(response("Plan: local only."),))
    developer = DeterministicMockAgent(role="developer", responses=developer_responses)
    reviewer = DeterministicMockAgent(role="reviewer", responses=reviewer_responses)
    qa = DeterministicMockAgent(role="qa", responses=(response("QA: passed."),))
    devops = DeterministicMockAgent(
        role="devops", responses=(response("Handoff: no deployment was run."),)
    )
    return (
        ApprovalGatedReleaseHandoffWorkflow(
            planner=planner,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
            devops=devops,
            max_review_cycles=cycles,
        ),
        planner,
        developer,
        reviewer,
        qa,
        devops,
    )


def test_review_approval_pauses_before_qa_and_devops() -> None:
    flow, planner, developer, reviewer, qa, devops = build_workflow()

    result = flow.run(task="Prepare a local handoff.")

    assert result.status is ReleaseHandoffStatus.AWAITING_HUMAN_APPROVAL
    assert result.review_cycles == 1
    assert result.handoff_note is None
    assert [message.role for message in result.messages] == ["planner", "developer", "reviewer"]
    assert len(planner.calls) == len(developer.calls) == len(reviewer.calls) == 1
    assert qa.calls == []
    assert devops.calls == []


def test_explicit_approval_runs_qa_then_devops_and_shares_audit_context() -> None:
    flow, _, developer, reviewer, qa, devops = build_workflow()

    result = flow.run(task="Prepare a local handoff.", human_approval=HumanApproval.APPROVED)

    assert result.status is ReleaseHandoffStatus.COMPLETED
    assert result.handoff_note == "Handoff: no deployment was run."
    assert [message.role for message in result.messages] == [
        "planner",
        "developer",
        "reviewer",
        "qa",
        "devops",
    ]
    assert reviewer.calls[0].messages[-1].role == "developer"
    assert qa.calls[0].messages[-1].role == "reviewer"
    assert devops.calls[0].messages[-1].role == "qa"
    assert len(developer.calls) == len(reviewer.calls) == len(qa.calls) == len(devops.calls) == 1


def test_revisions_stop_at_the_configured_bound_without_qa_or_devops() -> None:
    flow, _, developer, reviewer, qa, devops = build_workflow(
        developer_responses=(response("Draft one."), response("Draft two.")),
        reviewer_responses=(
            response("Revise the local notes.", ReviewDecision.REVISE),
            response("Revise again.", ReviewDecision.REVISE),
        ),
    )

    result = flow.run(task="Prepare a local handoff.", human_approval=HumanApproval.APPROVED)

    assert result.status is ReleaseHandoffStatus.REVIEW_LIMIT_REACHED
    assert result.review_cycles == 2
    assert result.handoff_note is None
    assert [message.role for message in result.messages] == [
        "planner",
        "developer",
        "reviewer",
        "developer",
        "reviewer",
    ]
    assert len(developer.calls) == len(reviewer.calls) == 2
    assert qa.calls == []
    assert devops.calls == []


def test_rejection_fails_closed_before_every_role() -> None:
    flow, planner, developer, reviewer, qa, devops = build_workflow()

    result = flow.run(task="Prepare a local handoff.", human_approval=HumanApproval.REJECTED)

    assert result.status is ReleaseHandoffStatus.HUMAN_REJECTED
    assert result.messages == ()
    assert result.handoff_note is None
    assert planner.calls == developer.calls == reviewer.calls == qa.calls == devops.calls == []


def test_invalid_review_response_stops_before_qa_and_devops() -> None:
    flow, _, developer, reviewer, qa, devops = build_workflow(
        reviewer_responses=(response("Review did not make a decision."),)
    )

    with pytest.raises(AgentProtocolError, match="explicit review decision"):
        flow.run(task="Prepare a local handoff.")

    assert len(developer.calls) == len(reviewer.calls) == 1
    assert qa.calls == []
    assert devops.calls == []


def test_script_exhaustion_does_not_fallback_to_qa_or_devops() -> None:
    flow, _, developer, reviewer, qa, devops = build_workflow(
        developer_responses=(response("Draft one."),),
        reviewer_responses=(
            response("Revise the local notes.", ReviewDecision.REVISE),
            response("Review after a second draft.", ReviewDecision.APPROVE),
        ),
    )

    with pytest.raises(AgentProtocolError, match="developer mock has no response for call 2"):
        flow.run(task="Prepare a local handoff.", human_approval=HumanApproval.APPROVED)

    assert len(developer.calls) == len(reviewer.calls) == 1
    assert qa.calls == []
    assert devops.calls == []


def test_configuration_and_agent_response_contracts_fail_closed() -> None:
    with pytest.raises(WorkflowConfigurationError, match="positive integer"):
        ApprovalGatedReleaseHandoffWorkflow(
            planner=DeterministicMockAgent(role="planner", responses=(response("Plan."),)),
            developer=DeterministicMockAgent(role="developer", responses=(response("Draft."),)),
            reviewer=DeterministicMockAgent(role="reviewer", responses=(response("Review."),)),
            qa=DeterministicMockAgent(role="qa", responses=(response("QA."),)),
            devops=DeterministicMockAgent(role="devops", responses=(response("Handoff."),)),
            max_review_cycles=True,
        )

    flow, _, _, reviewer, qa, devops = build_workflow(
        reviewer_responses=(response("   ", ReviewDecision.APPROVE),)
    )
    with pytest.raises(AgentProtocolError, match="content must be a non-empty string"):
        flow.run(task="Prepare a local handoff.")
    assert len(reviewer.calls) == 1
    assert qa.calls == []
    assert devops.calls == []
