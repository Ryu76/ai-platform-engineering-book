"""Offline contract tests for Volume 07's approval-gated delegation slice."""

from __future__ import annotations

import pytest

from ai_platform.agents import (
    AgentProtocolError,
    ApprovalGatedDelegationWorkflow,
    DelegationApproval,
    DelegationPlan,
    DelegationStatus,
    DelegationTask,
    DeterministicMockCoordinator,
    DeterministicMockWorker,
    WorkerResponse,
    WorkflowConfigurationError,
)


def plan(*tasks: DelegationTask) -> DelegationPlan:
    """Create one finite, reviewable delegation manifest."""
    return DelegationPlan("Split the offline work by specialty.", tasks)


def task(task_id: str, assignee: str) -> DelegationTask:
    """Create a local assignment with stable content for audit assertions."""
    return DelegationTask(task_id, assignee, f"Complete {task_id} without network access.")


def workflow(
    *,
    coordinator_plan: DelegationPlan,
    writer_responses: tuple[WorkerResponse, ...] = (WorkerResponse("draft complete", True),),
    checker_responses: tuple[WorkerResponse, ...] = (WorkerResponse("checks complete", True),),
    attempts: int = 2,
) -> tuple[
    ApprovalGatedDelegationWorkflow,
    DeterministicMockCoordinator,
    DeterministicMockWorker,
    DeterministicMockWorker,
]:
    """Build a finite coordinator and exactly two local worker boundaries."""
    coordinator = DeterministicMockCoordinator(plans=(coordinator_plan,))
    writer = DeterministicMockWorker(role="writer", responses=writer_responses)
    checker = DeterministicMockWorker(role="checker", responses=checker_responses)
    return (
        ApprovalGatedDelegationWorkflow(
            coordinator=coordinator,
            workers={"writer": writer, "checker": checker},
            allowed_assignees=frozenset({"writer", "checker"}),
            max_tasks=2,
            max_worker_attempts=attempts,
        ),
        coordinator,
        writer,
        checker,
    )


def test_pending_approval_records_a_manifest_but_never_calls_workers() -> None:
    flow, coordinator, writer, checker = workflow(
        coordinator_plan=plan(task("draft", "writer"), task("verify", "checker"))
    )

    result = flow.run(objective="Prepare a local tutorial.")

    assert result.status is DelegationStatus.AWAITING_HUMAN_APPROVAL
    assert result.completed_task_ids == ()
    assert [(message.role, message.content) for message in result.messages] == [
        (
            "coordinator",
            "Split the offline work by specialty. Assignments: draft->writer, verify->checker.",
        )
    ]
    assert len(coordinator.calls) == 1
    assert writer.calls == []
    assert checker.calls == []


def test_explicit_approval_runs_only_manifest_tasks_and_records_retry_context() -> None:
    flow, _, writer, checker = workflow(
        coordinator_plan=plan(task("draft", "writer"), task("verify", "checker")),
        writer_responses=(
            WorkerResponse("draft needs a local correction", False),
            WorkerResponse("draft complete", True),
        ),
    )

    result = flow.run(
        objective="Prepare a local tutorial.", human_approval=DelegationApproval.APPROVED
    )

    assert result.status is DelegationStatus.COMPLETED
    assert result.completed_task_ids == ("draft", "verify")
    assert [(message.role, message.task_id, message.attempt) for message in result.messages] == [
        ("coordinator", None, 0),
        ("writer", "draft", 1),
        ("writer", "draft", 2),
        ("checker", "verify", 1),
    ]
    assert [call.attempt for call in writer.calls] == [1, 2]
    assert writer.calls[0].task == task("draft", "writer")
    assert writer.calls[0].messages[0].role == "coordinator"
    assert checker.calls[0].messages[-1].content == "draft complete"


def test_unsuccessful_worker_stops_at_limit_and_does_not_dispatch_later_tasks() -> None:
    flow, _, writer, checker = workflow(
        coordinator_plan=plan(task("draft", "writer"), task("verify", "checker")),
        writer_responses=(
            WorkerResponse("retry one", False),
            WorkerResponse("retry two", False),
        ),
    )

    result = flow.run(
        objective="Prepare a local tutorial.", human_approval=DelegationApproval.APPROVED
    )

    assert result.status is DelegationStatus.WORKER_RETRY_LIMIT_REACHED
    assert result.completed_task_ids == ()
    assert [(message.task_id, message.attempt) for message in result.messages] == [
        (None, 0),
        ("draft", 1),
        ("draft", 2),
    ]
    assert len(writer.calls) == 2
    assert checker.calls == []


def test_human_rejection_fails_closed_before_coordinator_or_workers_are_called() -> None:
    flow, coordinator, writer, checker = workflow(
        coordinator_plan=plan(task("draft", "writer"))
    )

    result = flow.run(
        objective="Prepare a local tutorial.", human_approval=DelegationApproval.REJECTED
    )

    assert result.status is DelegationStatus.HUMAN_REJECTED
    assert result.messages == ()
    assert coordinator.calls == []
    assert writer.calls == []
    assert checker.calls == []


def test_unsafe_manifest_and_configuration_fail_closed_before_worker_execution() -> None:
    unsafe_flow, _, writer, _ = workflow(
        coordinator_plan=plan(task("draft", "writer"), task("draft", "checker"))
    )

    with pytest.raises(AgentProtocolError, match="task ids must be unique"):
        unsafe_flow.run(objective="Prepare a local tutorial.")
    assert writer.calls == []

    coordinator = DeterministicMockCoordinator(plans=(plan(task("draft", "writer")),))
    writer_worker = DeterministicMockWorker(
        role="writer", responses=(WorkerResponse("done", True),)
    )
    with pytest.raises(WorkflowConfigurationError, match="exactly one worker"):
        ApprovalGatedDelegationWorkflow(
            coordinator=coordinator,
            workers={"writer": writer_worker},
            allowed_assignees=frozenset({"writer", "checker"}),
        )


def test_malformed_objective_and_agent_outputs_fail_closed() -> None:
    flow, coordinator, writer, checker = workflow(
        coordinator_plan=plan(task("draft", "writer"))
    )

    with pytest.raises(WorkflowConfigurationError, match="non-empty string"):
        flow.run(objective=object())  # type: ignore[arg-type]
    assert coordinator.calls == []
    assert writer.calls == []
    assert checker.calls == []

    malformed_plan_flow, _, malformed_plan_writer, _ = workflow(
        coordinator_plan=object()  # type: ignore[arg-type]
    )
    with pytest.raises(AgentProtocolError, match="must be a DelegationPlan"):
        malformed_plan_flow.run(objective="Prepare a local tutorial.")
    assert malformed_plan_writer.calls == []

    malformed_response_flow, _, malformed_response_writer, malformed_response_checker = workflow(
        coordinator_plan=plan(task("draft", "writer")),
        writer_responses=(object(),),  # type: ignore[arg-type]
    )
    with pytest.raises(AgentProtocolError, match="must be a WorkerResponse"):
        malformed_response_flow.run(
            objective="Prepare a local tutorial.", human_approval=DelegationApproval.APPROVED
        )
    assert len(malformed_response_writer.calls) == 1
    assert malformed_response_checker.calls == []


def test_worker_script_exhaustion_has_no_fallback_attempt() -> None:
    flow, _, writer, _ = workflow(
        coordinator_plan=plan(task("draft", "writer")),
        writer_responses=(WorkerResponse("retry", False),),
        attempts=2,
    )

    with pytest.raises(AgentProtocolError, match="no response for call 2"):
        flow.run(
            objective="Prepare a local tutorial.", human_approval=DelegationApproval.APPROVED
        )
    assert len(writer.calls) == 1
