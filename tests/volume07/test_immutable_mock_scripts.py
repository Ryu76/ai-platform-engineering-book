"""Offline configuration tests for fixed deterministic Volume 07 mock scripts."""

from __future__ import annotations

import pytest

from ai_platform.agents import (
    AgentContext,
    AgentProtocolError,
    AgentResponse,
    ConflictProposal,
    DelegationPlan,
    DelegationTask,
    DeterministicMockAgent,
    DeterministicMockConflictAgent,
    DeterministicMockCoordinator,
    DeterministicMockWorker,
    WorkerResponse,
    WorkflowConfigurationError,
)


def test_deterministic_mocks_reject_mutable_scripts_during_configuration() -> None:
    """A mutable script cannot extend or reorder the configured local call budget."""
    with pytest.raises(
        WorkflowConfigurationError, match="responses must be a non-empty immutable tuple"
    ):
        DeterministicMockAgent(
            role="planner", responses=[AgentResponse("plan")]  # type: ignore[arg-type]
        )
    with pytest.raises(
        WorkflowConfigurationError, match="plans must be a non-empty immutable tuple"
    ):
        DeterministicMockCoordinator(
            plans=[
                DelegationPlan(
                    "plan", (DelegationTask("task", "writer", "write"),)
                )
            ]  # type: ignore[arg-type]
        )
    with pytest.raises(
        WorkflowConfigurationError, match="responses must be a non-empty immutable tuple"
    ):
        DeterministicMockWorker(
            role="writer", responses=[WorkerResponse("done", True)]  # type: ignore[arg-type]
        )
    with pytest.raises(
        WorkflowConfigurationError, match="proposals must be a non-empty immutable tuple"
    ):
        DeterministicMockConflictAgent(
            role="reviewer",
            proposals=[ConflictProposal("local", "rationale")],  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "factory",
    (
        lambda: DeterministicMockAgent(
            role=None, responses=(AgentResponse("plan"),)  # type: ignore[arg-type]
        ),
        lambda: DeterministicMockWorker(
            role=None, responses=(WorkerResponse("done", True),)  # type: ignore[arg-type]
        ),
        lambda: DeterministicMockConflictAgent(
            role=None,
            proposals=(ConflictProposal("local", "rationale"),),  # type: ignore[arg-type]
        ),
    ),
)
def test_role_mocks_reject_non_string_role_names(factory: object) -> None:
    """Invalid role metadata is a configuration error, not an incidental attribute error."""
    with pytest.raises(WorkflowConfigurationError, match="role must not be empty"):
        factory()  # type: ignore[operator]


def test_deterministic_mocks_reject_malformed_fixed_entries_during_configuration() -> None:
    """A local script is valid only when every fixed entry satisfies its base contract."""
    with pytest.raises(WorkflowConfigurationError, match="AgentResponse content"):
        DeterministicMockAgent(
            role="planner", responses=(AgentResponse(object()),)  # type: ignore[arg-type]
        )
    with pytest.raises(WorkflowConfigurationError, match="DelegationPlan summary"):
        DeterministicMockCoordinator(
            plans=(DelegationPlan(" ", (DelegationTask("task", "writer", "write"),)),)
        )
    with pytest.raises(WorkflowConfigurationError, match="WorkerResponse succeeded"):
        DeterministicMockWorker(
            role="writer", responses=(WorkerResponse("done", 1),)  # type: ignore[arg-type]
        )
    with pytest.raises(WorkflowConfigurationError, match="ConflictProposal option and rationale"):
        DeterministicMockConflictAgent(
            role="reviewer", proposals=(ConflictProposal("option", " "),)
        )


def test_tuple_script_stays_bounded_and_exhaustion_has_no_fallback() -> None:
    """The accepted immutable script exposes every unexpected extra local invocation."""
    mock = DeterministicMockAgent(role="planner", responses=(AgentResponse("plan"),))
    context = AgentContext(task="offline", iteration=0, messages=())

    assert mock.act(context).content == "plan"
    with pytest.raises(AgentProtocolError, match="no response for call 2"):
        mock.act(context)
