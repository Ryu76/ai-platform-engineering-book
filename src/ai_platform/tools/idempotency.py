"""Tool 실행 전후 idempotency·approval·audit 바인딩을 memory-only fixture로 모델링한다.

이 module은 durable store, clock, Tool handler, network, process 또는 destructive action을 직접
호출하지 않는다. 이미 검증된 allowlisted Tool 요청의 immutable digest binding을 받아, injected
clock/audit sink 경계에서 한 번의 execution reservation과 결과 reconciliation signal만 결정한다.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from typing import Protocol


class McpToolExecutionLedgerError(ValueError):
    """idempotency, approval, audit 계약이 Tool 실행 전에 안전하게 중단됨을 나타낸다."""

    def __init__(self, message: str, *, reconciliation_required: bool = False) -> None:
        super().__init__(message)
        self.reconciliation_required = reconciliation_required


class McpToolExecutionState(StrEnum):
    """한 idempotency key가 다시 execution될 수 있는지 표현하는 작은 상태다."""

    RESERVED = "reserved"
    COMPLETED = "completed"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class McpToolExecutionOutcome(StrEnum):
    """caller가 Tool result를 확정했는지, delivery/side effect가 모호한지 나타낸다."""

    SUCCEEDED = "succeeded"
    AMBIGUOUS = "ambiguous"


class McpToolExecutionAuditPhase(StrEnum):
    """원문 인자·Tool 결과 없이 기록하는 pre/post execution audit 단계다."""

    AUTHORIZED = "authorized"
    SUCCEEDED = "succeeded"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class McpToolExecutionBinding:
    """idempotency key를 exact request의 non-reversible JSON digest에 묶는다."""

    idempotency_key: str
    request_id: str
    tool_name: str
    arguments_digest: str

    @classmethod
    def for_request(
        cls,
        *,
        idempotency_key: str,
        request_id: str,
        tool_name: str,
        arguments: Mapping[str, object],
    ) -> McpToolExecutionBinding:
        """같은 JSON 요청만 같은 immutable binding으로 만들고 raw argument를 보관하지 않는다."""
        _validate_identifier(idempotency_key, field_name="idempotency_key")
        _validate_identifier(request_id, field_name="request_id")
        _validate_identifier(tool_name, field_name="tool_name")
        return cls(
            idempotency_key=idempotency_key,
            request_id=request_id,
            tool_name=tool_name,
            arguments_digest=_arguments_digest(arguments),
        )

    def __post_init__(self) -> None:
        """직접 생성한 binding도 identifier와 SHA-256 hex snapshot을 강제한다."""
        _validate_identifier(self.idempotency_key, field_name="idempotency_key")
        _validate_identifier(self.request_id, field_name="request_id")
        _validate_identifier(self.tool_name, field_name="tool_name")
        if (
            not isinstance(self.arguments_digest, str)
            or len(self.arguments_digest) != 64
            or any(character not in "0123456789abcdef" for character in self.arguments_digest)
        ):
            raise McpToolExecutionLedgerError("MCP Tool arguments digest is invalid")


@dataclass(frozen=True, slots=True)
class McpTimedToolApproval:
    """trusted approval workflow가 발급했다고 가정하는 one-time exact binding grant다."""

    approval_id: str
    binding: McpToolExecutionBinding
    expires_at: float

    def __post_init__(self) -> None:
        """expiry 없는/replayable approval이 execution boundary에 들어오지 않게 한다."""
        _validate_identifier(self.approval_id, field_name="approval_id")
        if not isinstance(self.binding, McpToolExecutionBinding):
            raise McpToolExecutionLedgerError("MCP Tool approval binding is invalid")
        _validate_timestamp(self.expires_at)


@dataclass(frozen=True, slots=True)
class McpToolExecutionAuditEvent:
    """exact binding과 approval을 raw arguments/result 없이 immutable하게 남기는 event다."""

    binding: McpToolExecutionBinding
    approval_id: str
    phase: McpToolExecutionAuditPhase


class McpToolExecutionAuditSink(Protocol):
    """production durable append adapter가 구현할 one-event audit seam이다."""

    def record(self, event: McpToolExecutionAuditEvent) -> None:
        """정확히 한 immutable 최소 event를 append한다."""


@dataclass(slots=True)
class InMemoryMcpToolExecutionAuditSink:
    """offline fixture용 append-only audit sink; filesystem이나 external store를 열지 않는다."""

    _events: list[McpToolExecutionAuditEvent] = field(default_factory=list, init=False, repr=False)

    @property
    def events(self) -> tuple[McpToolExecutionAuditEvent, ...]:
        """기존 audit record를 caller가 수정하지 못하도록 tuple snapshot을 반환한다."""
        return tuple(self._events)

    def record(self, event: McpToolExecutionAuditEvent) -> None:
        """validated event 하나를 memory에 append한다."""
        if not isinstance(event, McpToolExecutionAuditEvent):
            raise McpToolExecutionLedgerError("MCP Tool audit event is invalid")
        self._events.append(event)


@dataclass(frozen=True, slots=True)
class McpToolExecutionClaim:
    """pre-execution audit append까지 끝난 one-time execution ownership snapshot이다."""

    binding: McpToolExecutionBinding
    approval_id: str


@dataclass(frozen=True, slots=True)
class McpToolExecutionResolution:
    """Tool result 이후 final state와 caller-owned reconciliation requirement를 반환한다."""

    state: McpToolExecutionState
    reconciliation_required: bool


@dataclass(slots=True)
class _LedgerEntry:
    """public API 밖 memory-only mutable reservation state다."""

    binding: McpToolExecutionBinding
    approval_id: str
    state: McpToolExecutionState


class InMemoryMcpToolExecutionLedger:
    """한 process 안에서 duplicate/replay를 멈추는 non-concurrent teaching fixture다.

    ``reserve`` 성공 뒤에만 caller가 allowlisted Tool을 한 번 실행할 수 있다. Completion audit
    append가 실패하거나 Tool outcome이 ambiguous면 key는 reconciliation-required로 latch되어 blind
    retry를 막는다. This is not a durable, transactional, or concurrent production store.
    """

    def __init__(self, audit_sink: McpToolExecutionAuditSink) -> None:
        if not callable(getattr(audit_sink, "record", None)):
            raise McpToolExecutionLedgerError("MCP Tool audit sink is invalid")
        self._audit_sink = audit_sink
        self._entries: dict[str, _LedgerEntry] = {}
        self._used_approval_ids: set[str] = set()

    def reserve(self, approval: McpTimedToolApproval, *, now: float) -> McpToolExecutionClaim:
        """unexpired unused approval의 pre-execution audit을 먼저 append하고 한 번만 claim한다."""
        if not isinstance(approval, McpTimedToolApproval):
            raise McpToolExecutionLedgerError("MCP Tool approval is invalid")
        now = _validate_timestamp(now)
        binding = approval.binding
        existing = self._entries.get(binding.idempotency_key)
        if existing is not None:
            if existing.binding == binding:
                raise McpToolExecutionLedgerError("MCP Tool idempotency key is already reserved")
            raise McpToolExecutionLedgerError(
                "MCP Tool idempotency key conflicts with another request"
            )
        if now >= approval.expires_at:
            raise McpToolExecutionLedgerError("MCP Tool approval has expired")
        if approval.approval_id in self._used_approval_ids:
            raise McpToolExecutionLedgerError("MCP Tool approval has already been used")
        self._append_audit(binding, approval.approval_id, McpToolExecutionAuditPhase.AUTHORIZED)
        self._entries[binding.idempotency_key] = _LedgerEntry(
            binding=binding,
            approval_id=approval.approval_id,
            state=McpToolExecutionState.RESERVED,
        )
        self._used_approval_ids.add(approval.approval_id)
        return McpToolExecutionClaim(binding=binding, approval_id=approval.approval_id)

    def resolve(
        self, claim: McpToolExecutionClaim, *, outcome: McpToolExecutionOutcome
    ) -> McpToolExecutionResolution:
        """Caller가 제공한 result의 success/ambiguity audit·retry signal만 결정한다."""
        if not isinstance(claim, McpToolExecutionClaim):
            raise McpToolExecutionLedgerError("MCP Tool execution claim is invalid")
        if not isinstance(outcome, McpToolExecutionOutcome):
            raise McpToolExecutionLedgerError("MCP Tool execution outcome is invalid")
        entry = self._entries.get(claim.binding.idempotency_key)
        if (
            entry is None
            or entry.binding != claim.binding
            or entry.approval_id != claim.approval_id
            or entry.state is not McpToolExecutionState.RESERVED
        ):
            raise McpToolExecutionLedgerError("MCP Tool execution claim cannot be resolved")
        if outcome is McpToolExecutionOutcome.AMBIGUOUS:
            return self._require_reconciliation(entry, McpToolExecutionAuditPhase.AMBIGUOUS)
        try:
            self._append_audit(
                entry.binding, entry.approval_id, McpToolExecutionAuditPhase.SUCCEEDED
            )
        except McpToolExecutionLedgerError:
            entry.state = McpToolExecutionState.RECONCILIATION_REQUIRED
            raise McpToolExecutionLedgerError(
                "MCP Tool completion audit failed; reconciliation is required",
                reconciliation_required=True,
            ) from None
        entry.state = McpToolExecutionState.COMPLETED
        return McpToolExecutionResolution(
            state=McpToolExecutionState.COMPLETED,
            reconciliation_required=False,
        )

    def state_for(self, idempotency_key: str) -> McpToolExecutionState | None:
        """caller가 retry 대신 durable reconciliation을 선택할 수 있는 read-only state query다."""
        _validate_identifier(idempotency_key, field_name="idempotency_key")
        entry = self._entries.get(idempotency_key)
        return None if entry is None else entry.state

    def _require_reconciliation(
        self, entry: _LedgerEntry, phase: McpToolExecutionAuditPhase
    ) -> McpToolExecutionResolution:
        try:
            self._append_audit(entry.binding, entry.approval_id, phase)
        except McpToolExecutionLedgerError:
            pass
        entry.state = McpToolExecutionState.RECONCILIATION_REQUIRED
        return McpToolExecutionResolution(
            state=McpToolExecutionState.RECONCILIATION_REQUIRED,
            reconciliation_required=True,
        )

    def _append_audit(
        self,
        binding: McpToolExecutionBinding,
        approval_id: str,
        phase: McpToolExecutionAuditPhase,
    ) -> None:
        try:
            self._audit_sink.record(
                McpToolExecutionAuditEvent(
                    binding=binding,
                    approval_id=approval_id,
                    phase=phase,
                )
            )
        except Exception:
            raise McpToolExecutionLedgerError("MCP Tool audit append failed") from None


def _validate_identifier(value: object, *, field_name: str) -> None:
    """log/store key injection을 피하는 small printable identifier contract다."""
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or any(character in "\x00\n\r" for character in value)
    ):
        raise McpToolExecutionLedgerError(
            f"MCP Tool {field_name} must be a non-empty single-line string"
        )


def _validate_timestamp(value: object) -> float:
    """injected time fixture의 NaN/infinity/bool을 expiry decision 전에 거부한다."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise McpToolExecutionLedgerError("MCP Tool approval timestamp is invalid")
    return float(value)


def _arguments_digest(arguments: Mapping[str, object]) -> str:
    """finite canonical JSON만 exact binding digest로 만들고 raw argument snapshot은 버린다."""
    if not isinstance(arguments, Mapping):
        raise McpToolExecutionLedgerError("MCP Tool arguments must be a JSON object")
    try:
        canonical_arguments = json.dumps(
            dict(arguments),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError):
        raise McpToolExecutionLedgerError("MCP Tool arguments must be finite JSON values") from None
    return hashlib.sha256(canonical_arguments.encode("utf-8")).hexdigest()
