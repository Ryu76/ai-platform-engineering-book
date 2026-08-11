"""Deterministic, approval-gated conflict resolution for Volume 07.

This module deliberately resolves only an exact option consensus. It does not let an
orchestrator silently pick a winner from conflicting agent suggestions; a consensus is
presented for explicit human approval before it is marked completed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from ai_platform.agents.workflow import (
    AgentProtocolError,
    WorkflowConfigurationError,
    validate_declared_role,
    validate_fixed_script,
)


class ConflictApproval(StrEnum):
    """Explicit human decision required before a consensus becomes a completed result."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ConflictResolutionStatus(StrEnum):
    """Terminal or safely-paused states for a bounded conflict-resolution run."""

    AWAITING_HUMAN_APPROVAL = "awaiting_human_approval"
    COMPLETED = "completed"
    CONFLICT_LIMIT_REACHED = "conflict_limit_reached"
    HUMAN_REJECTED = "human_rejected"


@dataclass(frozen=True)
class ConflictProposal:
    """One agent's auditable option and its local rationale for a resolution round."""

    option: str
    rationale: str


@dataclass(frozen=True)
class ConflictMessage:
    """An immutable record of a proposal or deterministic policy observation."""

    role: str
    content: str
    round: int


@dataclass(frozen=True)
class ConflictContext:
    """Read-only context supplied to one conflict-resolution agent invocation."""

    objective: str
    round: int
    messages: tuple[ConflictMessage, ...]


class ConflictAgent(Protocol):
    """Boundary that proposes exactly one local option for a bounded round."""

    def propose(self, context: ConflictContext) -> ConflictProposal:
        """Return a proposal without network, tool, or side-effect assumptions."""


class DeterministicMockConflictAgent:
    """Offline proposal agent that consumes a fixed local script in call order."""

    def __init__(self, *, role: str, proposals: tuple[ConflictProposal, ...]) -> None:
        if not isinstance(role, str) or not role.strip():
            raise WorkflowConfigurationError("role must not be empty")
        self._validate_proposal_script(proposals)
        self.role = role
        self._proposals = proposals
        self.calls: list[ConflictContext] = []

    @staticmethod
    def _validate_proposal_script(proposals: tuple[object, ...]) -> None:
        """Reject malformed fixed proposals during mock configuration."""
        validate_fixed_script("proposals", proposals)
        for proposal in proposals:
            if not isinstance(proposal, ConflictProposal):
                raise WorkflowConfigurationError(
                    "proposals must contain only ConflictProposal values"
                )
            if not isinstance(proposal.option, str) or not isinstance(proposal.rationale, str):
                raise WorkflowConfigurationError(
                    "ConflictProposal option and rationale must be strings in a fixed script"
                )
            if not proposal.option.strip() or not proposal.rationale.strip():
                raise WorkflowConfigurationError(
                    "ConflictProposal option and rationale must not be empty in a fixed script"
                )

    def propose(self, context: ConflictContext) -> ConflictProposal:
        """Record one local call and fail closed when the script is exhausted."""
        proposal_index = len(self.calls)
        if proposal_index >= len(self._proposals):
            raise AgentProtocolError(
                f"{self.role} mock has no proposal for call {proposal_index + 1}"
            )
        self.calls.append(context)
        return self._proposals[proposal_index]


@dataclass(frozen=True)
class ConflictResolutionResult:
    """The bounded audit trail and optional exact-consensus option for one objective."""

    status: ConflictResolutionStatus
    messages: tuple[ConflictMessage, ...]
    rounds: int
    consensus_option: str | None


class BoundedConflictResolutionWorkflow:
    """Collect finite proposals, require exact consensus, then require human approval."""

    def __init__(
        self,
        *,
        agents: Mapping[str, ConflictAgent],
        max_agents: int = 3,
        max_rounds: int = 2,
    ) -> None:
        self._validate_positive_integer("max_agents", max_agents)
        self._validate_positive_integer("max_rounds", max_rounds)
        if not isinstance(agents, Mapping):
            raise WorkflowConfigurationError("agents must be a mapping of roles to agents")
        if len(agents) < 2 or len(agents) > max_agents:
            raise WorkflowConfigurationError(
                "agents must contain at least two roles and not exceed max_agents"
            )
        if any(not isinstance(role, str) or not role.strip() for role in agents):
            raise WorkflowConfigurationError("agent roles must not be empty")
        for role, agent in agents.items():
            if not callable(getattr(agent, "propose", None)):
                raise WorkflowConfigurationError(
                    f"agent for {role} must provide a callable propose(context) method"
                )
            validate_declared_role(role, f"agent for {role}", agent)
        self._agents = dict(agents)
        self._max_rounds = max_rounds

    def run(
        self,
        *,
        objective: str,
        human_approval: ConflictApproval = ConflictApproval.PENDING,
    ) -> ConflictResolutionResult:
        """Run no more than ``max_rounds * max_agents`` local proposal calls.

        Rejection occurs before any agent invocation. Conflicting options are never selected
        by the workflow: the run stops at its round bound. An exact consensus is an auditable
        recommendation only until the caller supplies ``ConflictApproval.APPROVED``.
        """
        if not isinstance(objective, str) or not objective.strip():
            raise WorkflowConfigurationError("objective must be a non-empty string")
        if not isinstance(human_approval, ConflictApproval):
            raise WorkflowConfigurationError(
                "human_approval must be a ConflictApproval value"
            )
        if human_approval is ConflictApproval.REJECTED:
            return ConflictResolutionResult(
                ConflictResolutionStatus.HUMAN_REJECTED, (), 0, None
            )

        messages: list[ConflictMessage] = []
        for round_number in range(1, self._max_rounds + 1):
            proposals: list[ConflictProposal] = []
            for role, agent in self._agents.items():
                proposal = agent.propose(
                    ConflictContext(objective, round_number, tuple(messages))
                )
                self._validate_proposal(proposal)
                proposals.append(proposal)
                messages.append(ConflictMessage(role, proposal.rationale, round_number))

            options = {proposal.option for proposal in proposals}
            if len(options) != 1:
                continue

            consensus_option = proposals[0].option
            messages.append(
                ConflictMessage(
                    "policy",
                    f"Exact consensus proposed: {consensus_option}",
                    round_number,
                )
            )
            if human_approval is ConflictApproval.PENDING:
                return ConflictResolutionResult(
                    ConflictResolutionStatus.AWAITING_HUMAN_APPROVAL,
                    tuple(messages),
                    round_number,
                    consensus_option,
                )
            return ConflictResolutionResult(
                ConflictResolutionStatus.COMPLETED,
                tuple(messages),
                round_number,
                consensus_option,
            )

        return ConflictResolutionResult(
            ConflictResolutionStatus.CONFLICT_LIMIT_REACHED,
            tuple(messages),
            self._max_rounds,
            None,
        )

    @staticmethod
    def _validate_positive_integer(name: str, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise WorkflowConfigurationError(f"{name} must be a positive integer")

    @staticmethod
    def _validate_proposal(proposal: object) -> None:
        if not isinstance(proposal, ConflictProposal):
            raise AgentProtocolError("agent response must be a ConflictProposal")
        if not isinstance(proposal.option, str) or not isinstance(proposal.rationale, str):
            raise AgentProtocolError("conflict proposal option and rationale must be strings")
        if not proposal.option.strip() or not proposal.rationale.strip():
            raise AgentProtocolError("conflict proposal option and rationale must not be empty")
