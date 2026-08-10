"""Offline contract tests for Volume 07's bounded conflict-resolution slice."""

from __future__ import annotations

import pytest

from ai_platform.agents import (
    AgentProtocolError,
    BoundedConflictResolutionWorkflow,
    ConflictApproval,
    ConflictProposal,
    ConflictResolutionStatus,
    DeterministicMockConflictAgent,
    WorkflowConfigurationError,
)


def proposal(option: str, rationale: str = "Local rationale.") -> ConflictProposal:
    """Create one stable local proposal for a test script."""
    return ConflictProposal(option, rationale)


def workflow(
    *,
    planner_proposals: tuple[ConflictProposal, ...],
    reviewer_proposals: tuple[ConflictProposal, ...],
    rounds: int = 2,
) -> tuple[
    BoundedConflictResolutionWorkflow,
    DeterministicMockConflictAgent,
    DeterministicMockConflictAgent,
]:
    """Build two fixed agents with an explicit two-agent, finite boundary."""
    planner = DeterministicMockConflictAgent(
        role="planner", proposals=planner_proposals
    )
    reviewer = DeterministicMockConflictAgent(
        role="reviewer", proposals=reviewer_proposals
    )
    return (
        BoundedConflictResolutionWorkflow(
            agents={"planner": planner, "reviewer": reviewer},
            max_agents=2,
            max_rounds=rounds,
        ),
        planner,
        reviewer,
    )


def test_consensus_pauses_for_human_approval_without_implicit_completion() -> None:
    flow, planner, reviewer = workflow(
        planner_proposals=(proposal("offline tutorial", "Use the local tutorial."),),
        reviewer_proposals=(proposal("offline tutorial", "The local tutorial is reviewable."),),
    )

    result = flow.run(objective="Choose a tutorial plan.")

    assert result.status is ConflictResolutionStatus.AWAITING_HUMAN_APPROVAL
    assert result.rounds == 1
    assert result.consensus_option == "offline tutorial"
    assert [(message.role, message.round) for message in result.messages] == [
        ("planner", 1),
        ("reviewer", 1),
        ("policy", 1),
    ]
    assert len(planner.calls) == len(reviewer.calls) == 1


def test_explicit_approval_completes_only_after_bounded_agents_converge() -> None:
    flow, planner, reviewer = workflow(
        planner_proposals=(
            proposal("option-a", "Planner initially prefers option A."),
            proposal("offline tutorial", "Planner accepts the local plan."),
        ),
        reviewer_proposals=(
            proposal("option-b", "Reviewer initially prefers option B."),
            proposal("offline tutorial", "Reviewer accepts the local plan."),
        ),
    )

    result = flow.run(
        objective="Choose a tutorial plan.", human_approval=ConflictApproval.APPROVED
    )

    assert result.status is ConflictResolutionStatus.COMPLETED
    assert result.rounds == 2
    assert result.consensus_option == "offline tutorial"
    assert [message.role for message in result.messages] == [
        "planner",
        "reviewer",
        "planner",
        "reviewer",
        "policy",
    ]
    assert [call.round for call in planner.calls] == [1, 2]
    assert [call.round for call in reviewer.calls] == [1, 2]
    assert reviewer.calls[1].messages[-1].role == "planner"


def test_conflict_stops_at_configured_round_bound_without_selecting_a_winner() -> None:
    flow, planner, reviewer = workflow(
        planner_proposals=(proposal("option-a"), proposal("option-a")),
        reviewer_proposals=(proposal("option-b"), proposal("option-b")),
    )

    result = flow.run(
        objective="Choose a tutorial plan.", human_approval=ConflictApproval.APPROVED
    )

    assert result.status is ConflictResolutionStatus.CONFLICT_LIMIT_REACHED
    assert result.rounds == 2
    assert result.consensus_option is None
    assert [message.role for message in result.messages] == [
        "planner",
        "reviewer",
        "planner",
        "reviewer",
    ]
    assert len(planner.calls) == len(reviewer.calls) == 2


def test_human_rejection_fails_closed_before_any_agent_is_called() -> None:
    flow, planner, reviewer = workflow(
        planner_proposals=(proposal("offline tutorial"),),
        reviewer_proposals=(proposal("offline tutorial"),),
    )

    result = flow.run(
        objective="Choose a tutorial plan.", human_approval=ConflictApproval.REJECTED
    )

    assert result.status is ConflictResolutionStatus.HUMAN_REJECTED
    assert result.messages == ()
    assert planner.calls == []
    assert reviewer.calls == []


def test_unsafe_configuration_and_invalid_proposal_fail_before_later_calls() -> None:
    planner = DeterministicMockConflictAgent(
        role="planner", proposals=(proposal("offline tutorial"),)
    )
    with pytest.raises(WorkflowConfigurationError, match="at least two roles"):
        BoundedConflictResolutionWorkflow(agents={"planner": planner})
    with pytest.raises(WorkflowConfigurationError, match="positive integer"):
        BoundedConflictResolutionWorkflow(
            agents={"planner": planner, "reviewer": planner}, max_rounds=0
        )

    invalid_flow, _, reviewer = workflow(
        planner_proposals=(ConflictProposal("", "No option supplied."),),
        reviewer_proposals=(proposal("offline tutorial"),),
    )
    with pytest.raises(AgentProtocolError, match="option and rationale must not be empty"):
        invalid_flow.run(objective="Choose a tutorial plan.")
    assert reviewer.calls == []


def test_malformed_objective_and_proposal_types_fail_closed_before_later_calls() -> None:
    flow, planner, reviewer = workflow(
        planner_proposals=(proposal("offline tutorial"),),
        reviewer_proposals=(proposal("offline tutorial"),),
    )

    with pytest.raises(WorkflowConfigurationError, match="non-empty string"):
        flow.run(objective=object())  # type: ignore[arg-type]
    assert planner.calls == []
    assert reviewer.calls == []

    malformed_flow, malformed_planner, malformed_reviewer = workflow(
        planner_proposals=(object(),),  # type: ignore[arg-type]
        reviewer_proposals=(proposal("offline tutorial"),),
    )
    with pytest.raises(AgentProtocolError, match="must be a ConflictProposal"):
        malformed_flow.run(objective="Choose a tutorial plan.")
    assert len(malformed_planner.calls) == 1
    assert malformed_reviewer.calls == []

    malformed_field_flow, _, malformed_field_reviewer = workflow(
        planner_proposals=(
            ConflictProposal(object(), "A rationale."),  # type: ignore[arg-type]
        ),
        reviewer_proposals=(proposal("offline tutorial"),),
    )
    with pytest.raises(AgentProtocolError, match="option and rationale must be strings"):
        malformed_field_flow.run(objective="Choose a tutorial plan.")
    assert malformed_field_reviewer.calls == []


def test_mock_script_exhaustion_has_no_fallback_round() -> None:
    flow, planner, reviewer = workflow(
        planner_proposals=(proposal("option-a"),),
        reviewer_proposals=(proposal("option-b"),),
        rounds=2,
    )

    with pytest.raises(AgentProtocolError, match="no proposal for call 2"):
        flow.run(objective="Choose a tutorial plan.")
    assert len(planner.calls) == len(reviewer.calls) == 1
