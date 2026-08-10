"""고정 기록에서 Latency·Token·Cost를 결정론적으로 집계한다."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


class UsageEvaluationError(ValueError):
    """고정 사용량 평가 입력이 계약을 위반할 때 발생한다."""


@dataclass(frozen=True, slots=True)
class UsageCase:
    """골든 사례 ID에 연결할 지연 시간·토큰·비용 측정 계약이다."""

    case_id: str

    def __post_init__(self) -> None:
        _require_non_empty("case_id", self.case_id)


@dataclass(frozen=True, slots=True)
class RecordedUsage:
    """라이브 호출 없이 검토할 수 있는 한 사례의 고정 사용량 기록이다."""

    case_id: str
    latency_ms: int
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        _require_non_empty("case_id", self.case_id)
        _require_positive_int("latency_ms", self.latency_ms)
        _require_non_negative_int("input_tokens", self.input_tokens)
        _require_non_negative_int("output_tokens", self.output_tokens)


@dataclass(frozen=True, slots=True)
class TokenPricing:
    """토큰당 마이크로 USD 단가를 고정해 비용 계산을 재현한다."""

    input_micro_usd_per_token: int
    output_micro_usd_per_token: int

    def __post_init__(self) -> None:
        _require_non_negative_int(
            "input_micro_usd_per_token", self.input_micro_usd_per_token
        )
        _require_non_negative_int(
            "output_micro_usd_per_token", self.output_micro_usd_per_token
        )


@dataclass(frozen=True, slots=True)
class UsageCaseMetrics:
    """사례별 기록 토큰과 고정 단가로 계산한 비용을 보관한다."""

    case_id: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_micro_usd: int


@dataclass(frozen=True, slots=True)
class UsageMetrics:
    """전체 고정 사례의 지연 시간·토큰·비용 기준선이다."""

    cases_evaluated: int
    total_latency_ms: int
    mean_latency_ms: float
    p95_latency_ms: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_micro_usd: int


def evaluate_usage_cases(
    cases: Sequence[UsageCase],
    recorded_usage_by_case: Mapping[str, RecordedUsage],
    pricing: TokenPricing,
) -> tuple[UsageCaseMetrics, ...]:
    """완전한 고정 사례 집합을 사례 순서대로 비용까지 계산한다."""
    _validate_cases(cases)
    _validate_recorded_usage_keys(cases, recorded_usage_by_case)

    metrics: list[UsageCaseMetrics] = []
    for case in cases:
        usage = recorded_usage_by_case[case.case_id]
        if usage.case_id != case.case_id:
            raise UsageEvaluationError(
                f"recorded usage key and case_id must match for {case.case_id}"
            )
        total_tokens = usage.input_tokens + usage.output_tokens
        cost_micro_usd = (
            usage.input_tokens * pricing.input_micro_usd_per_token
            + usage.output_tokens * pricing.output_micro_usd_per_token
        )
        metrics.append(
            UsageCaseMetrics(
                case_id=case.case_id,
                latency_ms=usage.latency_ms,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=total_tokens,
                cost_micro_usd=cost_micro_usd,
            )
        )
    return tuple(metrics)


def evaluate_usage(
    cases: Sequence[UsageCase],
    recorded_usage_by_case: Mapping[str, RecordedUsage],
    pricing: TokenPricing,
) -> UsageMetrics:
    """고정 기록을 평균·nearest-rank P95·합계 기준선으로 집계한다."""
    case_metrics = evaluate_usage_cases(cases, recorded_usage_by_case, pricing)
    latencies = sorted(metric.latency_ms for metric in case_metrics)
    count = len(case_metrics)
    p95_index = (95 * count + 99) // 100 - 1
    total_latency_ms = sum(latencies)
    total_input_tokens = sum(metric.input_tokens for metric in case_metrics)
    total_output_tokens = sum(metric.output_tokens for metric in case_metrics)
    total_tokens = total_input_tokens + total_output_tokens
    total_cost_micro_usd = sum(metric.cost_micro_usd for metric in case_metrics)
    return UsageMetrics(
        cases_evaluated=count,
        total_latency_ms=total_latency_ms,
        mean_latency_ms=total_latency_ms / count,
        p95_latency_ms=latencies[p95_index],
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_tokens=total_tokens,
        total_cost_micro_usd=total_cost_micro_usd,
    )


def _validate_cases(cases: Sequence[UsageCase]) -> None:
    """빈 평가와 중복 사례 ID를 차단한다."""
    if not cases:
        raise UsageEvaluationError("at least one usage case is required")
    case_ids = tuple(case.case_id for case in cases)
    if len(set(case_ids)) != len(case_ids):
        raise UsageEvaluationError("usage case ids must be unique")


def _validate_recorded_usage_keys(
    cases: Sequence[UsageCase], recorded_usage_by_case: Mapping[str, RecordedUsage]
) -> None:
    """일부 사례만 제출해 시간·비용 기준선을 좋게 보이는 것을 막는다."""
    case_ids = {case.case_id for case in cases}
    recorded_case_ids = set(recorded_usage_by_case)
    if case_ids != recorded_case_ids:
        missing = sorted(case_ids - recorded_case_ids)
        unexpected = sorted(recorded_case_ids - case_ids)
        raise UsageEvaluationError(
            "recorded usage must match case ids; "
            f"missing={missing}, unexpected={unexpected}"
        )


def _require_non_empty(field_name: str, value: str) -> None:
    """문자열 식별자의 빈 값과 비문자열 값을 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise UsageEvaluationError(f"{field_name} must be a non-empty string")


def _require_positive_int(field_name: str, value: int) -> None:
    """밀리초는 0보다 큰 정수 기록만 허용한다."""
    if type(value) is not int or value <= 0:
        raise UsageEvaluationError(f"{field_name} must be a positive integer")


def _require_non_negative_int(field_name: str, value: int) -> None:
    """토큰과 마이크로 USD는 음수·실수·불리언을 허용하지 않는다."""
    if type(value) is not int or value < 0:
        raise UsageEvaluationError(f"{field_name} must be a non-negative integer")
