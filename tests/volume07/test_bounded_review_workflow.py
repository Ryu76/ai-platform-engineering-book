"""Offline contract tests for Volume 07's bounded multi-agent review slice."""

from __future__ import annotations

import pytest

from ai_platform.agents import (
    AgentContext,
    AgentProtocolError,
    AgentResponse,
    BoundedReviewWorkflow,
    DeterministicMockAgent,
    HumanApproval,
    ReviewDecision,
    WorkflowConfigurationError,
    WorkflowStatus,
)


def mock(role: str, *responses: AgentResponse) -> DeterministicMockAgent:
    """Create an auditable mock with only the supplied local responses."""
    return DeterministicMockAgent(role=role, responses=responses)


def workflow(
    *, review_responses: tuple[AgentResponse, ...], limit: int = 2
) -> tuple[
    BoundedReviewWorkflow,
    DeterministicMockAgent,
    DeterministicMockAgent,
    DeterministicMockAgent,
    DeterministicMockAgent,
    DeterministicMockAgent,
]:
    """Create five deterministic roles and return them for call-boundary assertions."""
    planner = mock("planner", AgentResponse("plan"))
    researcher = mock("researcher", AgentResponse("evidence"))
    developer = mock(
        "developer", *(AgentResponse(f"draft-{index}") for index in range(1, limit + 1))
    )
    reviewer = mock("reviewer", *review_responses)
    qa = mock("qa", AgentResponse("qa passed"))
    return (
        BoundedReviewWorkflow(
            planner=planner,
            researcher=researcher,
            developer=developer,
            reviewer=reviewer,
            qa=qa,
            max_review_cycles=limit,
        ),
        planner,
        researcher,
        developer,
        reviewer,
        qa,
    )


def test_approved_review_pauses_for_human_approval_without_running_qa() -> None:
    flow, planner, researcher, developer, reviewer, qa = workflow(
        review_responses=(AgentResponse("approved", ReviewDecision.APPROVE),)
    )

    result = flow.run(task="write an offline example")

    assert result.status is WorkflowStatus.AWAITING_HUMAN_APPROVAL
    assert result.review_cycles == 1
    assert [message.role for message in result.messages] == [
        "planner",
        "researcher",
        "developer",
        "reviewer",
    ]
    assert [len(agent.calls) for agent in (planner, researcher, developer, reviewer, qa)] == [
        1,
        1,
        1,
        1,
        0,
    ]


def test_explicit_human_approval_is_required_before_qa_and_completion() -> None:
    flow, _, _, _, _, qa = workflow(
        review_responses=(AgentResponse("approved", ReviewDecision.APPROVE),)
    )

    result = flow.run(task="write an offline example", human_approval=HumanApproval.APPROVED)

    assert result.status is WorkflowStatus.COMPLETED
    assert [message.role for message in result.messages] == [
        "planner",
        "researcher",
        "developer",
        "reviewer",
        "qa",
    ]
    assert len(qa.calls) == 1


def test_revisions_stop_at_the_configured_bound_without_qa() -> None:
    flow, _, _, developer, reviewer, qa = workflow(
        review_responses=(
            AgentResponse("revise first", ReviewDecision.REVISE),
            AgentResponse("revise second", ReviewDecision.REVISE),
        ),
        limit=2,
    )

    result = flow.run(task="write an offline example", human_approval=HumanApproval.APPROVED)

    assert result.status is WorkflowStatus.REVIEW_LIMIT_REACHED
    assert result.review_cycles == 2
    assert [message.role for message in result.messages] == [
        "planner",
        "researcher",
        "developer",
        "reviewer",
        "developer",
        "reviewer",
    ]
    assert len(developer.calls) == len(reviewer.calls) == 2
    assert qa.calls == []


def test_human_rejection_fails_closed_before_agents_are_called() -> None:
    flow, planner, researcher, developer, reviewer, qa = workflow(
        review_responses=(AgentResponse("approved", ReviewDecision.APPROVE),)
    )

    result = flow.run(task="write an offline example", human_approval=HumanApproval.REJECTED)

    assert result.status is WorkflowStatus.HUMAN_REJECTED
    assert result.messages == ()
    assert [agent.calls for agent in (planner, researcher, developer, reviewer, qa)] == [
        [],
        [],
        [],
        [],
        [],
    ]


def test_invalid_configuration_and_missing_reviewer_decision_fail_closed() -> None:
    planner = mock("planner", AgentResponse("plan"))
    with pytest.raises(WorkflowConfigurationError, match="positive integer"):
        BoundedReviewWorkflow(
            planner=planner,
            researcher=planner,
            developer=planner,
            reviewer=planner,
            qa=planner,
            max_review_cycles=0,
        )

    flow, _, _, _, _, _ = workflow(review_responses=(AgentResponse("ambiguous"),))
    with pytest.raises(AgentProtocolError, match="explicit review decision"):
        flow.run(task="write an offline example")


def test_invalid_task_and_early_agent_output_stop_before_later_roles() -> None:
    flow, planner, researcher, developer, reviewer, qa = workflow(
        review_responses=(AgentResponse("approved", ReviewDecision.APPROVE),)
    )

    with pytest.raises(WorkflowConfigurationError, match="non-empty string"):
        flow.run(task=object())  # type: ignore[arg-type]
    assert [agent.calls for agent in (planner, researcher, developer, reviewer, qa)] == [
        [],
        [],
        [],
        [],
        [],
    ]

    with pytest.raises(WorkflowConfigurationError, match="non-empty string in a fixed script"):
        mock("planner", AgentResponse("   "))


def test_mock_script_exhaustion_prevents_unbounded_fallback_work() -> None:
    agent = mock("developer", AgentResponse("one draft"))
    context = AgentContext(task="offline", iteration=1, messages=())

    assert agent.act(context).content == "one draft"
    with pytest.raises(AgentProtocolError, match="no response for call 2"):
        agent.act(context)
