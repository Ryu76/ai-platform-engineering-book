"""외부 모델 호출 없이 라우팅 계약과 검증 규칙을 정의한다."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class RoutingConfigurationError(ValueError):
    """라우팅 대상 또는 정책 조건이 유효하지 않을 때 발생한다."""


class NoEligibleRouteError(RuntimeError):
    """요청 조건을 만족하는 정상 대상이 없을 때 발생한다."""


class RouteTargetKind(StrEnum):
    """Router가 선택할 수 있는 실행 대상의 유형이다."""

    AGENT = "agent"
    TOOL = "tool"
    MODEL = "model"


@dataclass(frozen=True, slots=True)
class RouteTarget:
    """비용·지연 시간·기능을 명시한 고정 라우팅 대상이다."""

    name: str
    kind: RouteTargetKind
    capabilities: frozenset[str]
    estimated_cost: Decimal
    estimated_latency_ms: int
    healthy: bool = True

    def __post_init__(self) -> None:
        """결정론적 정책이 비교할 수 있는 대상 속성을 검증한다."""
        _validate_identifier(self.name, "target name")
        if not self.capabilities:
            raise RoutingConfigurationError("target capabilities must not be empty")
        for capability in self.capabilities:
            _validate_identifier(capability, "capability")
        _validate_nonnegative_decimal(self.estimated_cost, "estimated_cost")
        _validate_nonnegative_int(self.estimated_latency_ms, "estimated_latency_ms")
        if not isinstance(self.healthy, bool):
            raise RoutingConfigurationError("healthy must be a boolean")


@dataclass(frozen=True, slots=True)
class RoutingRequirements:
    """한 요청이 필요로 하는 기능·비용·지연 시간 제한이다."""

    required_capabilities: frozenset[str] = field(default_factory=frozenset)
    maximum_cost: Decimal | None = None
    maximum_latency_ms: int | None = None
    permitted_target_names: frozenset[str] | None = None

    def __post_init__(self) -> None:
        """정책 평가 전에 제한 조건의 형식과 범위를 검증한다."""
        for capability in self.required_capabilities:
            _validate_identifier(capability, "required capability")
        if self.maximum_cost is not None:
            _validate_nonnegative_decimal(self.maximum_cost, "maximum_cost")
        if self.maximum_latency_ms is not None:
            _validate_nonnegative_int(self.maximum_latency_ms, "maximum_latency_ms")
        if self.permitted_target_names is not None:
            if not self.permitted_target_names:
                raise RoutingConfigurationError("permitted_target_names must not be empty when set")
            for name in self.permitted_target_names:
                _validate_identifier(name, "permitted target name")


@dataclass(frozen=True, slots=True)
class RoutingRequest:
    """원문과 정책 조건을 함께 보관하되, 원문은 결정 로그에 기록하지 않는다."""

    request_id: str
    text: str
    requirements: RoutingRequirements = field(default_factory=RoutingRequirements)

    def __post_init__(self) -> None:
        """추적 가능한 요청 ID와 비어 있지 않은 사용자 입력을 요구한다."""
        _validate_identifier(self.request_id, "request_id")
        if not isinstance(self.text, str) or not self.text.strip():
            raise RoutingConfigurationError("request text must not be empty")


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """선택 결과와 감사 가능한 최소 메타데이터를 나타낸다."""

    request_id: str
    policy_name: str
    target: RouteTarget
    reason: str
    confidence: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        """정책명이 비어 있거나 신뢰도가 범위를 벗어난 결정을 막는다."""
        _validate_identifier(self.request_id, "request_id")
        _validate_identifier(self.policy_name, "policy_name")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise RoutingConfigurationError("decision reason must not be empty")
        _validate_nonnegative_decimal(self.confidence, "confidence")
        if self.confidence > Decimal("1"):
            raise RoutingConfigurationError("confidence must be between 0 and 1")

    def as_log_record(self) -> dict[str, str]:
        """사용자 원문·비밀값 없이 JSON 직렬화 가능한 결정 로그를 만든다."""
        return {
            "request_id": self.request_id,
            "policy_name": self.policy_name,
            "target_name": self.target.name,
            "target_kind": self.target.kind.value,
            "reason": self.reason,
            "confidence": str(self.confidence),
            "estimated_cost": str(self.target.estimated_cost),
            "estimated_latency_ms": str(self.target.estimated_latency_ms),
        }


def _validate_identifier(value: object, name: str) -> None:
    """빈 문자열, 공백 전용 문자열, 문자열이 아닌 식별자를 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise RoutingConfigurationError(f"{name} must be a nonempty string")


def _validate_nonnegative_decimal(value: object, name: str) -> None:
    """비용 비교에서 부동소수점·NaN·Infinity를 허용하지 않는다."""
    if not isinstance(value, Decimal):
        raise RoutingConfigurationError(f"{name} must be a Decimal")
    try:
        valid = value.is_finite() and value >= Decimal("0")
    except InvalidOperation as error:
        raise RoutingConfigurationError(f"{name} must be a finite nonnegative Decimal") from error
    if not valid:
        raise RoutingConfigurationError(f"{name} must be a finite nonnegative Decimal")


def _validate_nonnegative_int(value: object, name: str) -> None:
    """밀리초 제한은 부울을 제외한 0 이상의 정수로 한정한다."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RoutingConfigurationError(f"{name} must be a nonnegative integer")
