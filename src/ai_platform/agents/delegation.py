"""Deterministic, approval-gated delegation primitives for Volume 07.

The module intentionally models planning separately from delegated execution. A plan may be
shown to a human while the workflow is paused, but no delegated worker is called until the
same run receives an explicit approval value.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from ai_platform.agents.workflow import (
    AgentProtocolError,
    WorkflowConfigurationError,
    validate_fixed_script,
)


class DelegationStatus(StrEnum):
    """Terminal or safely-paused states for a delegation run."""

    AWAITING_HUMAN_APPROVAL = "awaiting_human_approval"
    COMPLETED = "completed"
    HUMAN_REJECTED = "human_rejected"
    WORKER_RETRY_LIMIT_REACHED = "worker_retry_limit_reached"


class DelegationApproval(StrEnum):
    """Explicit human decision required before any delegated worker may run."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class DelegationTask:
    """One auditable, bounded assignment proposed by the coordinator."""

    task_id: str
    assignee: str
    instruction: str


@dataclass(frozen=True)
class DelegationPlan:
    """A finite manifest of delegated work proposed for human review."""

    summary: str
    tasks: tuple[DelegationTask, ...]


@dataclass(frozen=True)
class DelegationMessage:
    """An immutable audit record for planning or one worker attempt."""

    role: str
    content: str
    task_id: str | None = None
    attempt: int = 0


@dataclass(frozen=True)
class DelegationContext:
    """Read-only context supplied to a coordinator or delegated worker."""

    objective: str
    messages: tuple[DelegationMessage, ...]
    task: DelegationTask | None = None
    attempt: int = 0


@dataclass(frozen=True)
class WorkerResponse:
    """A fixed worker result; unsuccessful results consume a bounded retry attempt."""

    content: str
    succeeded: bool


class DelegationCoordinator(Protocol):
    """Boundary that proposes a delegation manifest without executing it."""

    def propose(self, context: DelegationContext) -> DelegationPlan:
        """Return one finite proposed plan for the supplied context."""


class DelegatedWorker(Protocol):
    """Boundary that performs one already-approved delegated attempt."""

    def act(self, context: DelegationContext) -> WorkerResponse:
        """Return one result for the supplied task and attempt number."""


class DeterministicMockCoordinator:
    """Offline coordinator that consumes a fixed plan script in call order."""

    def __init__(self, *, plans: tuple[DelegationPlan, ...]) -> None:
        self._validate_plan_script(plans)
        self._plans = plans
        self.calls: list[DelegationContext] = []

    @staticmethod
    def _validate_plan_script(plans: tuple[object, ...]) -> None:
        """Reject structurally malformed fixed manifests during mock configuration."""
        validate_fixed_script("plans", plans)
        for plan in plans:
            if not isinstance(plan, DelegationPlan):
                raise WorkflowConfigurationError("plans must contain only DelegationPlan values")
            if not isinstance(plan.summary, str) or not plan.summary.strip():
                raise WorkflowConfigurationError(
                    "DelegationPlan summary must be a non-empty string in a fixed script"
                )
            if not isinstance(plan.tasks, tuple) or not plan.tasks:
                raise WorkflowConfigurationError(
                    "DelegationPlan tasks must be a non-empty immutable tuple in a fixed script"
                )
            task_ids: set[str] = set()
            for task in plan.tasks:
                if not isinstance(task, DelegationTask):
                    raise WorkflowConfigurationError(
                        "DelegationPlan tasks must contain only DelegationTask values"
                    )
                if any(
                    not isinstance(value, str) or not value.strip()
                    for value in (task.task_id, task.assignee, task.instruction)
                ):
                    raise WorkflowConfigurationError(
                        "DelegationTask fields must be non-empty strings in a fixed script"
                    )
                if task.task_id in task_ids:
                    raise WorkflowConfigurationError(
                        "DelegationPlan task ids must be unique in a fixed script"
                    )
                task_ids.add(task.task_id)

    def propose(self, context: DelegationContext) -> DelegationPlan:
        """Record the local planning call and return the next fixed manifest."""
        plan_index = len(self.calls)
        if plan_index >= len(self._plans):
            raise AgentProtocolError(
                f"coordinator mock has no plan for call {plan_index + 1}"
            )
        self.calls.append(context)
        return self._plans[plan_index]


class DeterministicMockWorker:
    """Offline worker that consumes fixed outcomes and fails closed on exhaustion."""

    def __init__(self, *, role: str, responses: tuple[WorkerResponse, ...]) -> None:
        if not isinstance(role, str) or not role.strip():
            raise WorkflowConfigurationError("role must not be empty")
        self._validate_response_script(responses)
        self.role = role
        self._responses = responses
        self.calls: list[DelegationContext] = []

    @staticmethod
    def _validate_response_script(responses: tuple[object, ...]) -> None:
        """Reject malformed fixed worker outcomes during mock configuration."""
        validate_fixed_script("responses", responses)
        for response in responses:
            if not isinstance(response, WorkerResponse):
                raise WorkflowConfigurationError(
                    "responses must contain only WorkerResponse values"
                )
            if not isinstance(response.content, str) or not response.content.strip():
                raise WorkflowConfigurationError(
                    "WorkerResponse content must be a non-empty string in a fixed script"
                )
            if not isinstance(response.succeeded, bool):
                raise WorkflowConfigurationError(
                    "WorkerResponse succeeded must be a boolean in a fixed script"
                )

    def act(self, context: DelegationContext) -> WorkerResponse:
        """Record a local worker call and return the next preconfigured outcome."""
        response_index = len(self.calls)
        if response_index >= len(self._responses):
            raise AgentProtocolError(
                f"{self.role} mock has no response for call {response_index + 1}"
            )
        self.calls.append(context)
        return self._responses[response_index]


@dataclass(frozen=True)
class DelegationResult:
    """The state and complete audit trail for one delegation request."""

    status: DelegationStatus
    messages: tuple[DelegationMessage, ...]
    completed_task_ids: tuple[str, ...]


class ApprovalGatedDelegationWorkflow:
    """Plan a finite manifest, pause for approval, then run bounded worker retries."""

    def __init__(
        self,
        *,
        coordinator: DelegationCoordinator,
        workers: Mapping[str, DelegatedWorker],
        allowed_assignees: frozenset[str],
        max_tasks: int = 3,
        max_worker_attempts: int = 2,
    ) -> None:
        self._validate_positive_integer("max_tasks", max_tasks)
        self._validate_positive_integer("max_worker_attempts", max_worker_attempts)
        if not isinstance(workers, Mapping):
            raise WorkflowConfigurationError("workers must be a mapping of assignees to workers")
        if not isinstance(allowed_assignees, frozenset) or not allowed_assignees:
            raise WorkflowConfigurationError(
                "allowed_assignees must be a non-empty immutable frozenset"
            )
        if any(not isinstance(role, str) or not role.strip() for role in allowed_assignees):
            raise WorkflowConfigurationError("allowed_assignees must contain non-empty roles")
        if set(workers) != set(allowed_assignees):
            raise WorkflowConfigurationError(
                "workers must contain exactly one worker for each allowed assignee"
            )
        if not callable(getattr(coordinator, "propose", None)):
            raise WorkflowConfigurationError(
                "coordinator must provide a callable propose(context) method"
            )
        for assignee, worker in workers.items():
            if not callable(getattr(worker, "act", None)):
                raise WorkflowConfigurationError(
                    f"worker for {assignee} must provide a callable act(context) method"
                )
        self._coordinator = coordinator
        self._workers = dict(workers)
        self._allowed_assignees = frozenset(allowed_assignees)
        self._max_tasks = max_tasks
        self._max_worker_attempts = max_worker_attempts

    def run(
        self,
        *,
        objective: str,
        human_approval: DelegationApproval = DelegationApproval.PENDING,
    ) -> DelegationResult:
        """Produce an approved finite plan and execute only its bounded worker attempts."""
        if not isinstance(objective, str) or not objective.strip():
            raise WorkflowConfigurationError("objective must be a non-empty string")
        if not isinstance(human_approval, DelegationApproval):
            raise WorkflowConfigurationError(
                "human_approval must be a DelegationApproval value"
            )
        if human_approval is DelegationApproval.REJECTED:
            return DelegationResult(DelegationStatus.HUMAN_REJECTED, (), ())

        messages: list[DelegationMessage] = []
        plan = self._coordinator.propose(DelegationContext(objective, tuple(messages)))
        self._validate_plan(plan)
        messages.append(DelegationMessage("coordinator", self._render_plan(plan)))

        if human_approval is DelegationApproval.PENDING:
            return DelegationResult(
                DelegationStatus.AWAITING_HUMAN_APPROVAL, tuple(messages), ()
            )

        completed_task_ids: list[str] = []
        for task in plan.tasks:
            worker = self._workers[task.assignee]
            for attempt in range(1, self._max_worker_attempts + 1):
                response = worker.act(
                    DelegationContext(objective, tuple(messages), task, attempt)
                )
                self._validate_worker_response(response)
                messages.append(
                    DelegationMessage(task.assignee, response.content, task.task_id, attempt)
                )
                if response.succeeded:
                    completed_task_ids.append(task.task_id)
                    break
            else:
                return DelegationResult(
                    DelegationStatus.WORKER_RETRY_LIMIT_REACHED,
                    tuple(messages),
                    tuple(completed_task_ids),
                )

        return DelegationResult(
            DelegationStatus.COMPLETED, tuple(messages), tuple(completed_task_ids)
        )

    @staticmethod
    def _validate_positive_integer(name: str, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise WorkflowConfigurationError(f"{name} must be a positive integer")

    def _validate_plan(self, plan: DelegationPlan) -> None:
        if not isinstance(plan, DelegationPlan):
            raise AgentProtocolError("coordinator response must be a DelegationPlan")
        if not isinstance(plan.summary, str) or not plan.summary.strip():
            raise AgentProtocolError("delegation plan summary must not be empty")
        if not isinstance(plan.tasks, tuple):
            raise AgentProtocolError("delegation plan tasks must be an immutable tuple")
        if not plan.tasks or len(plan.tasks) > self._max_tasks:
            raise AgentProtocolError("delegation plan task count is outside the configured bound")

        task_ids: set[str] = set()
        for task in plan.tasks:
            if not isinstance(task, DelegationTask):
                raise AgentProtocolError("delegation plan contains an invalid task")
            if not isinstance(task.task_id, str) or not isinstance(task.instruction, str):
                raise AgentProtocolError("delegation task id and instruction must be strings")
            if not task.task_id.strip() or not task.instruction.strip():
                raise AgentProtocolError("delegation task id and instruction must not be empty")
            if not isinstance(task.assignee, str):
                raise AgentProtocolError("delegation task assignee must be a string")
            if task.task_id in task_ids:
                raise AgentProtocolError("delegation plan task ids must be unique")
            if task.assignee not in self._allowed_assignees:
                raise AgentProtocolError("delegation task assignee is not allowed")
            task_ids.add(task.task_id)

    @staticmethod
    def _validate_worker_response(response: object) -> None:
        """Reject malformed worker output before it is added to the audit trail."""
        if not isinstance(response, WorkerResponse):
            raise AgentProtocolError("worker response must be a WorkerResponse")
        if not isinstance(response.content, str) or not response.content.strip():
            raise AgentProtocolError("worker response content must be a non-empty string")
        if not isinstance(response.succeeded, bool):
            raise AgentProtocolError("worker response succeeded must be a boolean")

    @staticmethod
    def _render_plan(plan: DelegationPlan) -> str:
        assignments = ", ".join(
            f"{task.task_id}->{task.assignee}" for task in plan.tasks
        )
        return f"{plan.summary} Assignments: {assignments}."
