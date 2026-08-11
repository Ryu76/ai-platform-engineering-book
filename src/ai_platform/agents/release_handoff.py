"""Bounded, approval-gated release handoff for Volume 07.

This module produces an auditable local handoff only.  The DevOps role prepares a
release note after QA, but it has no deployment, network, secret, or tool-execution
capability.  An explicit human approval is required before QA and DevOps are called.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_platform.agents.workflow import (
    Agent,
    AgentContext,
    AgentMessage,
    AgentProtocolError,
    AgentResponse,
    HumanApproval,
    ReviewDecision,
    WorkflowConfigurationError,
    validate_agent_boundary,
)


class ReleaseHandoffStatus(StrEnum):
    """Terminal or safely-paused states of an offline release-handoff run."""

    AWAITING_HUMAN_APPROVAL = "awaiting_human_approval"
    COMPLETED = "completed"
    HUMAN_REJECTED = "human_rejected"
    REVIEW_LIMIT_REACHED = "review_limit_reached"


@dataclass(frozen=True)
class ReleaseHandoffResult:
    """Immutable audit trail and optional local handoff note for one release candidate."""

    status: ReleaseHandoffStatus
    messages: tuple[AgentMessage, ...]
    review_cycles: int
    handoff_note: str | None


class ApprovalGatedReleaseHandoffWorkflow:
    """Coordinate bounded review, then make QA and DevOps contingent on human approval.

    A completed result means only that deterministic local QA and the DevOps handoff
    note were produced.  It never means that a deployment, tool call, or external
    change occurred.
    """

    def __init__(
        self,
        *,
        planner: Agent,
        developer: Agent,
        reviewer: Agent,
        qa: Agent,
        devops: Agent,
        max_review_cycles: int = 2,
    ) -> None:
        self._validate_positive_integer("max_review_cycles", max_review_cycles)
        for role, agent in (
            ("planner", planner),
            ("developer", developer),
            ("reviewer", reviewer),
            ("qa", qa),
            ("devops", devops),
        ):
            validate_agent_boundary(role, agent)
        self._planner = planner
        self._developer = developer
        self._reviewer = reviewer
        self._qa = qa
        self._devops = devops
        self._max_review_cycles = max_review_cycles

    def run(
        self, *, task: str, human_approval: HumanApproval = HumanApproval.PENDING
    ) -> ReleaseHandoffResult:
        """Prepare at most one plan plus ``max_review_cycles`` draft/review pairs.

        ``REJECTED`` exits before all roles.  ``PENDING`` returns the approved review
        audit trail but does not call QA or DevOps.  Only an ``APPROVED`` decision can
        produce the final local handoff note.
        """
        if not isinstance(task, str) or not task.strip():
            raise WorkflowConfigurationError("task must be a non-empty string")
        if not isinstance(human_approval, HumanApproval):
            raise WorkflowConfigurationError("human_approval must be a HumanApproval value")
        if human_approval is HumanApproval.REJECTED:
            return ReleaseHandoffResult(ReleaseHandoffStatus.HUMAN_REJECTED, (), 0, None)

        messages: list[AgentMessage] = []
        self._append(messages, "planner", self._planner, task, 0)

        for cycle in range(1, self._max_review_cycles + 1):
            self._append(messages, "developer", self._developer, task, cycle)
            reviewer_response = self._call(self._reviewer, task, cycle, messages)
            self._validate_role_response(reviewer_response, "reviewer")
            messages.append(AgentMessage("reviewer", reviewer_response.content, cycle))

            if reviewer_response.review is ReviewDecision.REVISE:
                continue
            if human_approval is HumanApproval.PENDING:
                return ReleaseHandoffResult(
                    ReleaseHandoffStatus.AWAITING_HUMAN_APPROVAL,
                    tuple(messages),
                    cycle,
                    None,
                )

            self._append(messages, "qa", self._qa, task, cycle)
            handoff = self._call(self._devops, task, cycle, messages)
            self._validate_role_response(handoff, "devops")
            messages.append(AgentMessage("devops", handoff.content, cycle))
            return ReleaseHandoffResult(
                ReleaseHandoffStatus.COMPLETED,
                tuple(messages),
                cycle,
                handoff.content,
            )

        return ReleaseHandoffResult(
            ReleaseHandoffStatus.REVIEW_LIMIT_REACHED,
            tuple(messages),
            self._max_review_cycles,
            None,
        )

    @staticmethod
    def _validate_positive_integer(name: str, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise WorkflowConfigurationError(f"{name} must be a positive integer")

    @staticmethod
    def _call(
        agent: Agent, task: str, iteration: int, messages: list[AgentMessage]
    ) -> AgentResponse:
        return agent.act(AgentContext(task, iteration, tuple(messages)))

    def _append(
        self, messages: list[AgentMessage], role: str, agent: Agent, task: str, iteration: int
    ) -> None:
        response = self._call(agent, task, iteration, messages)
        self._validate_role_response(response, role)
        messages.append(AgentMessage(role, response.content, iteration))

    @staticmethod
    def _validate_response(response: object) -> AgentResponse:
        if not isinstance(response, AgentResponse):
            raise AgentProtocolError("agent response must be an AgentResponse")
        if not isinstance(response.content, str) or not response.content.strip():
            raise AgentProtocolError("agent response content must be a non-empty string")
        if response.review is not None and not isinstance(response.review, ReviewDecision):
            raise AgentProtocolError(
                "agent response review must be a ReviewDecision or None"
            )
        return response

    @classmethod
    def _validate_role_response(cls, response: object, role: str) -> None:
        """Limit review authority to Reviewer before an output enters the audit trail."""
        validated_response = cls._validate_response(response)
        if role != "reviewer" and validated_response.review is not None:
            raise AgentProtocolError(f"{role} response must not include a review decision")
        if role == "reviewer" and validated_response.review not in (
            ReviewDecision.APPROVE,
            ReviewDecision.REVISE,
        ):
            raise AgentProtocolError("reviewer response must include an explicit review decision")
