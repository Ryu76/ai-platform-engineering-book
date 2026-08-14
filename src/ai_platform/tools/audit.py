"""승인된 Tool 실행의 최소·구조화 감사 기록을 남기는 교육용 경계."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from ai_platform.tools.authorization import (
    ApprovalGrant,
    ToolAuthorizationPolicy,
    ToolRisk,
    execute_authorized,
    execute_authorized_with_policy,
)
from ai_platform.tools.execution import (
    ToolExecutionPolicy,
    ToolExecutionTimeoutError,
    ToolRetryExhaustedError,
)
from ai_platform.tools.registry import ToolRegistry, ToolRegistryError, ToolResult


class ToolAuditOutcome(StrEnum):
    """Tool 요청의 감사 가능한 최종 상태; handler 오류도 성공으로 기록하지 않는다."""

    SUCCEEDED = "succeeded"
    DENIED = "denied"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ToolAuditEvent:
    """원문 인자·결과·예외 없이 실행 경계를 추적할 최소 이벤트다."""

    request_id: str
    tool_name: str
    risk: ToolRisk | None
    approval_id: str | None
    outcome: ToolAuditOutcome


@dataclass(slots=True)
class InMemoryToolAuditSink:
    """오프라인 실습용 append-only 감사 sink; 외부 저장소에는 연결하지 않는다."""

    _events: list[ToolAuditEvent] = field(default_factory=list, init=False, repr=False)

    @property
    def events(self) -> tuple[ToolAuditEvent, ...]:
        """호출자가 기존 기록을 바꾸지 못하도록 불변 스냅샷을 반환한다."""
        return tuple(self._events)

    def record(self, event: ToolAuditEvent) -> None:
        """이미 최소화한 이벤트 하나만 기록한다."""
        self._events.append(event)


def execute_audited(
    registry: ToolRegistry,
    *,
    request_id: str,
    tool_name: str,
    arguments: Mapping[str, object],
    policy: ToolAuthorizationPolicy,
    audit_sink: InMemoryToolAuditSink,
    approval: ApprovalGrant | None = None,
) -> ToolResult:
    """기존 승인 경계를 실행하고 성공·거부·실패를 원문 없이 한 번 기록한다."""
    try:
        result = execute_authorized(
            registry,
            request_id=request_id,
            tool_name=tool_name,
            arguments=arguments,
            policy=policy,
            approval=approval,
        )
    except ToolRegistryError:
        audit_sink.record(
            _event_for_request(
                request_id=request_id,
                tool_name=tool_name,
                policy=policy,
                approval=approval,
                outcome=ToolAuditOutcome.DENIED,
            )
        )
        raise
    except Exception:
        audit_sink.record(
            _event_for_request(
                request_id=request_id,
                tool_name=tool_name,
                policy=policy,
                approval=approval,
                outcome=ToolAuditOutcome.FAILED,
            )
        )
        raise
    audit_sink.record(
        _event_for_request(
            request_id=request_id,
            tool_name=tool_name,
            policy=policy,
            approval=approval,
            outcome=ToolAuditOutcome.SUCCEEDED,
        )
    )
    return result


def execute_audited_with_policy(
    registry: ToolRegistry,
    *,
    request_id: str,
    tool_name: str,
    arguments: Mapping[str, object],
    authorization_policy: ToolAuthorizationPolicy,
    execution_policy: ToolExecutionPolicy,
    audit_sink: InMemoryToolAuditSink,
    approval: ApprovalGrant | None = None,
) -> ToolResult:
    """승인 뒤 제한된 timeout/retry 실행을 하고 원문 없이 최종 결과를 감사한다."""
    try:
        result = execute_authorized_with_policy(
            registry,
            request_id=request_id,
            tool_name=tool_name,
            arguments=arguments,
            authorization_policy=authorization_policy,
            execution_policy=execution_policy,
            approval=approval,
        )
    except (ToolExecutionTimeoutError, ToolRetryExhaustedError):
        audit_sink.record(
            _event_for_request(
                request_id=request_id,
                tool_name=tool_name,
                policy=authorization_policy,
                approval=approval,
                outcome=ToolAuditOutcome.FAILED,
            )
        )
        raise
    except ToolRegistryError:
        audit_sink.record(
            _event_for_request(
                request_id=request_id,
                tool_name=tool_name,
                policy=authorization_policy,
                approval=approval,
                outcome=ToolAuditOutcome.DENIED,
            )
        )
        raise
    except Exception:
        audit_sink.record(
            _event_for_request(
                request_id=request_id,
                tool_name=tool_name,
                policy=authorization_policy,
                approval=approval,
                outcome=ToolAuditOutcome.FAILED,
            )
        )
        raise
    audit_sink.record(
        _event_for_request(
            request_id=request_id,
            tool_name=tool_name,
            policy=authorization_policy,
            approval=approval,
            outcome=ToolAuditOutcome.SUCCEEDED,
        )
    )
    return result


def _event_for_request(
    *,
    request_id: str,
    tool_name: str,
    policy: ToolAuthorizationPolicy,
    approval: ApprovalGrant | None,
    outcome: ToolAuditOutcome,
) -> ToolAuditEvent:
    """모든 경로에서 같은 최소 필드만 사용해 감사 이벤트를 만든다."""
    return ToolAuditEvent(
        request_id=request_id,
        tool_name=tool_name,
        risk=policy.tool_risks.get(tool_name),
        approval_id=approval.approval_id if approval is not None else None,
        outcome=outcome,
    )
