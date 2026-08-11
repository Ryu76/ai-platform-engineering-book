"""Offline runtime tests for untrusted AgentResponse review decisions in Volume 07."""

from __future__ import annotations

import pytest

from ai_platform.agents import (
    AgentContext,
    AgentProtocolError,
    AgentResponse,
    ApprovalGatedReleaseHandoffWorkflow,
    BoundedReviewWorkflow,
    DeterministicMockAgent,
    HumanApproval,
    ReviewDecision,
)


class InvalidReviewAgent:
    """A local untrusted boundary that bypasses deterministic mock setup validation."""

    def __init__(self, response: AgentResponse) -> None:
        self._response = response
        self.calls: list[AgentContext] = []

    def act(self, context: AgentContext) -> AgentResponse:
        self.calls.append(context)
        return self._response


def mock(role: str, response: AgentResponse) -> DeterministicMockAgent:
    """Build one valid, fixed, offline role response."""
    return DeterministicMockAgent(role=role, responses=(response,))


def test_invalid_runtime_review_stops_review_workflow_before_researcher() -> None:
    planner = InvalidReviewAgent(AgentResponse("plan", "approve"))  # type: ignore[arg-type]
    researcher = mock("researcher", AgentResponse("evidence"))
    developer = mock("developer", AgentResponse("draft"))
    reviewer = mock("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = mock("qa", AgentResponse("qa passed"))
    workflow = BoundedReviewWorkflow(
        planner=planner,
        researcher=researcher,
        developer=developer,
        reviewer=reviewer,
        qa=qa,
    )

    with pytest.raises(AgentProtocolError, match="review must be a ReviewDecision or None"):
        workflow.run(task="keep the workflow offline", human_approval=HumanApproval.APPROVED)

    assert len(planner.calls) == 1
    assert researcher.calls == developer.calls == reviewer.calls == qa.calls == []


def test_invalid_runtime_review_stops_release_handoff_before_qa_and_devops() -> None:
    planner = mock("planner", AgentResponse("plan"))
    developer = mock("developer", AgentResponse("draft"))
    reviewer = InvalidReviewAgent(AgentResponse("approved", "approve"))  # type: ignore[arg-type]
    qa = mock("qa", AgentResponse("qa passed"))
    devops = mock("devops", AgentResponse("local handoff only"))
    workflow = ApprovalGatedReleaseHandoffWorkflow(
        planner=planner,
        developer=developer,
        reviewer=reviewer,
        qa=qa,
        devops=devops,
    )

    with pytest.raises(AgentProtocolError, match="review must be a ReviewDecision or None"):
        workflow.run(task="prepare a local handoff", human_approval=HumanApproval.APPROVED)

    assert len(planner.calls) == len(developer.calls) == len(reviewer.calls) == 1
    assert qa.calls == devops.calls == []


def test_non_reviewer_cannot_claim_review_authority_before_next_review_workflow_role() -> None:
    planner = InvalidReviewAgent(AgentResponse("plan", ReviewDecision.APPROVE))
    researcher = mock("researcher", AgentResponse("evidence"))
    developer = mock("developer", AgentResponse("draft"))
    reviewer = mock("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = mock("qa", AgentResponse("qa passed"))
    workflow = BoundedReviewWorkflow(
        planner=planner,
        researcher=researcher,
        developer=developer,
        reviewer=reviewer,
        qa=qa,
    )

    with pytest.raises(AgentProtocolError, match="planner response must not include"):
        workflow.run(
            task="keep review authority role-scoped",
            human_approval=HumanApproval.APPROVED,
        )

    assert len(planner.calls) == 1
    assert researcher.calls == developer.calls == reviewer.calls == qa.calls == []


def test_qa_cannot_claim_review_authority_before_release_devops_handoff() -> None:
    planner = mock("planner", AgentResponse("plan"))
    developer = mock("developer", AgentResponse("draft"))
    reviewer = mock("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = InvalidReviewAgent(AgentResponse("qa passed", ReviewDecision.APPROVE))
    devops = mock("devops", AgentResponse("local handoff only"))
    workflow = ApprovalGatedReleaseHandoffWorkflow(
        planner=planner,
        developer=developer,
        reviewer=reviewer,
        qa=qa,
        devops=devops,
    )

    with pytest.raises(AgentProtocolError, match="qa response must not include"):
        workflow.run(task="prepare a local handoff", human_approval=HumanApproval.APPROVED)

    assert len(planner.calls) == len(developer.calls) == len(reviewer.calls) == len(qa.calls) == 1
    assert devops.calls == []


def test_devops_cannot_claim_review_authority_or_create_a_handoff_note() -> None:
    planner = mock("planner", AgentResponse("plan"))
    developer = mock("developer", AgentResponse("draft"))
    reviewer = mock("reviewer", AgentResponse("approved", ReviewDecision.APPROVE))
    qa = mock("qa", AgentResponse("qa passed"))
    devops = InvalidReviewAgent(AgentResponse("local handoff only", ReviewDecision.APPROVE))
    workflow = ApprovalGatedReleaseHandoffWorkflow(
        planner=planner,
        developer=developer,
        reviewer=reviewer,
        qa=qa,
        devops=devops,
    )

    with pytest.raises(AgentProtocolError, match="devops response must not include"):
        workflow.run(task="prepare a local handoff", human_approval=HumanApproval.APPROVED)

    assert len(devops.calls) == 1
