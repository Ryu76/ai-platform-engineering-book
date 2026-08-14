"""Volume 03의 Tool idempotency·approval·audit fixture가 blind retry를 막는지 검증한다."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from ai_platform.tools.idempotency import (
    InMemoryMcpToolExecutionAuditSink,
    InMemoryMcpToolExecutionLedger,
    McpTimedToolApproval,
    McpToolExecutionAuditPhase,
    McpToolExecutionBinding,
    McpToolExecutionClaim,
    McpToolExecutionLedgerError,
    McpToolExecutionOutcome,
    McpToolExecutionState,
)


def _binding(
    *,
    key: str = "idem-001",
    request_id: str = "mcp-stdio:string:request-001",
    arguments: dict[str, object] | None = None,
) -> McpToolExecutionBinding:
    return McpToolExecutionBinding.for_request(
        idempotency_key=key,
        request_id=request_id,
        tool_name="safe_calculator",
        arguments=arguments or {"left": 2, "right": 3, "operation": "add"},
    )


def _approval(
    *,
    binding: McpToolExecutionBinding | None = None,
    approval_id: str = "approval-001",
    expires_at: float = 101.0,
) -> McpTimedToolApproval:
    return McpTimedToolApproval(
        approval_id=approval_id,
        binding=binding or _binding(),
        expires_at=expires_at,
    )


def test_reservation_appends_exact_digest_binding_before_allowlisted_execution() -> None:
    sink = InMemoryMcpToolExecutionAuditSink()
    ledger = InMemoryMcpToolExecutionLedger(sink)
    secret_like_argument = "do-not-store-this-tool-argument"
    approval = _approval(binding=_binding(arguments={"text": secret_like_argument}))

    claim = ledger.reserve(approval, now=100.0)

    assert claim.binding == approval.binding
    assert claim.approval_id == "approval-001"
    assert sink.events[0].phase is McpToolExecutionAuditPhase.AUTHORIZED
    assert sink.events[0].binding == approval.binding
    assert secret_like_argument not in str(asdict(sink.events[0]))
    assert ledger.state_for("idem-001") is McpToolExecutionState.RESERVED


def test_same_idempotency_key_cannot_execute_twice_after_reservation() -> None:
    ledger = InMemoryMcpToolExecutionLedger(InMemoryMcpToolExecutionAuditSink())
    approval = _approval()
    ledger.reserve(approval, now=100.0)

    with pytest.raises(McpToolExecutionLedgerError, match="already reserved"):
        ledger.reserve(approval, now=100.0)

    assert ledger.state_for("idem-001") is McpToolExecutionState.RESERVED


def test_same_key_with_a_different_exact_request_is_a_pre_execution_conflict() -> None:
    sink = InMemoryMcpToolExecutionAuditSink()
    ledger = InMemoryMcpToolExecutionLedger(sink)
    ledger.reserve(_approval(), now=100.0)
    conflicting = _approval(
        binding=_binding(arguments={"left": 2, "right": 4, "operation": "add"}),
        approval_id="approval-002",
    )

    with pytest.raises(McpToolExecutionLedgerError, match="conflicts"):
        ledger.reserve(conflicting, now=100.0)

    assert len(sink.events) == 1


def test_expired_approval_is_rejected_before_audit_or_reservation() -> None:
    sink = InMemoryMcpToolExecutionAuditSink()
    ledger = InMemoryMcpToolExecutionLedger(sink)

    with pytest.raises(McpToolExecutionLedgerError, match="has expired"):
        ledger.reserve(_approval(expires_at=100.0), now=100.0)

    assert sink.events == ()
    assert ledger.state_for("idem-001") is None


def test_replayed_approval_id_is_rejected_even_for_a_new_idempotency_key() -> None:
    sink = InMemoryMcpToolExecutionAuditSink()
    ledger = InMemoryMcpToolExecutionLedger(sink)
    ledger.reserve(_approval(), now=100.0)
    replay = _approval(
        binding=_binding(key="idem-002", request_id="mcp-stdio:string:request-002"),
    )

    with pytest.raises(McpToolExecutionLedgerError, match="already been used"):
        ledger.reserve(replay, now=100.0)

    assert len(sink.events) == 1
    assert ledger.state_for("idem-002") is None


class _FailingAuditSink:
    def __init__(self, *, fail_calls: set[int]) -> None:
        self.fail_calls = fail_calls
        self.calls = 0

    def record(self, _: object) -> None:
        self.calls += 1
        if self.calls in self.fail_calls:
            raise RuntimeError("private durable audit adapter detail")


def test_pre_execution_audit_failure_does_not_consume_key_or_approval() -> None:
    sink = _FailingAuditSink(fail_calls={1})
    ledger = InMemoryMcpToolExecutionLedger(sink)
    approval = _approval()

    with pytest.raises(McpToolExecutionLedgerError, match="audit append failed") as error:
        ledger.reserve(approval, now=100.0)

    assert "private durable audit adapter detail" not in str(error.value)
    assert error.value.reconciliation_required is False
    assert ledger.state_for("idem-001") is None
    assert sink.calls == 1


def test_successful_result_appends_completion_and_closes_the_key() -> None:
    sink = InMemoryMcpToolExecutionAuditSink()
    ledger = InMemoryMcpToolExecutionLedger(sink)
    claim = ledger.reserve(_approval(), now=100.0)

    resolution = ledger.resolve(claim, outcome=McpToolExecutionOutcome.SUCCEEDED)

    assert resolution.state is McpToolExecutionState.COMPLETED
    assert resolution.reconciliation_required is False
    assert [event.phase for event in sink.events] == [
        McpToolExecutionAuditPhase.AUTHORIZED,
        McpToolExecutionAuditPhase.SUCCEEDED,
    ]


def test_ambiguous_tool_result_latches_key_for_caller_owned_reconciliation() -> None:
    ledger = InMemoryMcpToolExecutionLedger(InMemoryMcpToolExecutionAuditSink())
    approval = _approval()
    claim = ledger.reserve(approval, now=100.0)

    resolution = ledger.resolve(claim, outcome=McpToolExecutionOutcome.AMBIGUOUS)

    assert resolution.state is McpToolExecutionState.RECONCILIATION_REQUIRED
    assert resolution.reconciliation_required is True
    with pytest.raises(McpToolExecutionLedgerError, match="already reserved"):
        ledger.reserve(approval, now=100.0)


def test_completion_audit_failure_latches_key_and_requires_reconciliation() -> None:
    sink = _FailingAuditSink(fail_calls={2})
    ledger = InMemoryMcpToolExecutionLedger(sink)
    claim = ledger.reserve(_approval(), now=100.0)

    with pytest.raises(McpToolExecutionLedgerError, match="reconciliation is required") as error:
        ledger.resolve(claim, outcome=McpToolExecutionOutcome.SUCCEEDED)

    assert error.value.reconciliation_required is True
    assert ledger.state_for("idem-001") is McpToolExecutionState.RECONCILIATION_REQUIRED
    assert sink.calls == 2


def test_forged_or_stale_claim_never_appends_a_completion_event() -> None:
    sink = InMemoryMcpToolExecutionAuditSink()
    ledger = InMemoryMcpToolExecutionLedger(sink)
    claim = ledger.reserve(_approval(), now=100.0)
    forged = McpToolExecutionClaim(binding=_binding(key="idem-002"), approval_id=claim.approval_id)

    with pytest.raises(McpToolExecutionLedgerError, match="cannot be resolved"):
        ledger.resolve(forged, outcome=McpToolExecutionOutcome.SUCCEEDED)

    assert len(sink.events) == 1


@pytest.mark.parametrize("now", (True, float("nan"), "100"))
def test_invalid_clock_value_is_rejected_before_audit(now: object) -> None:
    sink = InMemoryMcpToolExecutionAuditSink()
    ledger = InMemoryMcpToolExecutionLedger(sink)

    with pytest.raises(McpToolExecutionLedgerError, match="timestamp is invalid"):
        ledger.reserve(_approval(), now=now)  # type: ignore[arg-type]

    assert sink.events == ()
