"""고정 평가 스냅샷을 동일한 계약에서 결정론적으로 비교한다."""
from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from typing import Literal


class RegressionEvaluationError(ValueError):
    """회귀 비교 입력이 데이터셋·지표 계약을 위반할 때 발생한다."""


MetricDirection = Literal["higher_is_better", "lower_is_better"]
ComparisonStatus = Literal["improved", "within_tolerance", "regression"]


@dataclass(frozen=True, slots=True)
class MetricValue:
    """한 이름과 유한한 수치로 표현한 결정론적 평가 결과다."""

    metric_id: str
    value: float

    def __post_init__(self) -> None:
        _require_non_empty("metric_id", self.metric_id)
        _require_finite("value", self.value)


@dataclass(frozen=True, slots=True)
class EvaluationSnapshot:
    """동일한 골든 사례 집합에서 얻은 이름 있는 지표의 고정 스냅샷이다."""

    dataset_id: str
    dataset_version: str
    case_ids: tuple[str, ...]
    metrics: tuple[MetricValue, ...]

    def __post_init__(self) -> None:
        _require_non_empty("dataset_id", self.dataset_id)
        _require_non_empty("dataset_version", self.dataset_version)
        _validate_identifiers("case_ids", self.case_ids)
        if not self.metrics:
            raise RegressionEvaluationError("metrics must not be empty")
        metric_ids = tuple(metric.metric_id for metric in self.metrics)
        if len(set(metric_ids)) != len(metric_ids):
            raise RegressionEvaluationError("metric ids must be unique")


@dataclass(frozen=True, slots=True)
class RegressionPolicy:
    """한 지표의 바람직한 방향과 허용 가능한 절대 저하량이다."""

    metric_id: str
    direction: MetricDirection
    allowed_degradation: float = 0.0

    def __post_init__(self) -> None:
        _require_non_empty("metric_id", self.metric_id)
        if self.direction not in {"higher_is_better", "lower_is_better"}:
            raise RegressionEvaluationError(
                "direction must be 'higher_is_better' or 'lower_is_better'"
            )
        _require_finite("allowed_degradation", self.allowed_degradation)
        if self.allowed_degradation < 0:
            raise RegressionEvaluationError("allowed_degradation must be non-negative")


@dataclass(frozen=True, slots=True)
class RegressionMetricResult:
    """한 정책 지표의 기준선·후보 차이와 승인 상태다."""

    metric_id: str
    baseline_value: float
    candidate_value: float
    delta: float
    allowed_degradation: float
    status: ComparisonStatus


@dataclass(frozen=True, slots=True)
class RegressionReport:
    """동일 데이터셋 비교의 사례 계약, 지표 결과, 최종 승인 결정을 보관한다."""

    dataset_id: str
    dataset_version: str
    cases_evaluated: int
    is_approved: bool
    metric_results: tuple[RegressionMetricResult, ...]


def compare_snapshots(
    baseline: EvaluationSnapshot,
    candidate: EvaluationSnapshot,
    policies: tuple[RegressionPolicy, ...],
) -> RegressionReport:
    """같은 데이터셋·버전·사례·지표 계약에서 후보 회귀를 판정한다.

    ``allowed_degradation``은 지표의 원래 단위로 표현한 절대 허용치다. 예를 들어
    recall 0.75에서 0.01을 허용하려면 ``0.01``을 사용하고, 비용 micro USD에는 그
    정수 단위를 그대로 사용한다. 모든 정책 지표가 허용 범위 안에 있어야 승인된다.
    """
    _validate_comparable_snapshots(baseline, candidate)
    _validate_policies(policies, baseline.metrics)
    baseline_values = {metric.metric_id: metric.value for metric in baseline.metrics}
    candidate_values = {metric.metric_id: metric.value for metric in candidate.metrics}

    results = tuple(
        _compare_metric(
            policy,
            baseline_values[policy.metric_id],
            candidate_values[policy.metric_id],
        )
        for policy in policies
    )
    return RegressionReport(
        dataset_id=baseline.dataset_id,
        dataset_version=baseline.dataset_version,
        cases_evaluated=len(baseline.case_ids),
        is_approved=all(result.status != "regression" for result in results),
        metric_results=results,
    )


def _compare_metric(
    policy: RegressionPolicy, baseline_value: float, candidate_value: float
) -> RegressionMetricResult:
    """정책 방향을 적용해 한 후보 값의 악화량과 상태를 계산한다."""
    delta = candidate_value - baseline_value
    deterioration = -delta if policy.direction == "higher_is_better" else delta
    exceeds_tolerance = deterioration > policy.allowed_degradation and not isclose(
        deterioration, policy.allowed_degradation, rel_tol=1e-12, abs_tol=1e-12
    )
    if exceeds_tolerance:
        status: ComparisonStatus = "regression"
    elif deterioration < 0:
        status = "improved"
    else:
        status = "within_tolerance"
    return RegressionMetricResult(
        metric_id=policy.metric_id,
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        delta=delta,
        allowed_degradation=policy.allowed_degradation,
        status=status,
    )


def _validate_comparable_snapshots(
    baseline: EvaluationSnapshot, candidate: EvaluationSnapshot
) -> None:
    """기준선과 후보가 같은 재현 가능한 평가 계약을 사용하는지 검사한다."""
    if baseline.dataset_id != candidate.dataset_id:
        raise RegressionEvaluationError("dataset ids must match")
    if baseline.dataset_version != candidate.dataset_version:
        raise RegressionEvaluationError("dataset versions must match")
    if baseline.case_ids != candidate.case_ids:
        raise RegressionEvaluationError("case ids and order must match")
    baseline_metric_ids = {metric.metric_id for metric in baseline.metrics}
    candidate_metric_ids = {metric.metric_id for metric in candidate.metrics}
    if baseline_metric_ids != candidate_metric_ids:
        missing = sorted(baseline_metric_ids - candidate_metric_ids)
        unexpected = sorted(candidate_metric_ids - baseline_metric_ids)
        raise RegressionEvaluationError(
            f"snapshot metric ids must match; missing={missing}, unexpected={unexpected}"
        )


def _validate_policies(
    policies: tuple[RegressionPolicy, ...], metrics: tuple[MetricValue, ...]
) -> None:
    """정확히 한 정책으로 모든 비교 지표의 방향과 허용치를 고정한다."""
    if not policies:
        raise RegressionEvaluationError("at least one regression policy is required")
    policy_ids = tuple(policy.metric_id for policy in policies)
    if len(set(policy_ids)) != len(policy_ids):
        raise RegressionEvaluationError("regression policy metric ids must be unique")
    metric_ids = {metric.metric_id for metric in metrics}
    if set(policy_ids) != metric_ids:
        missing = sorted(metric_ids - set(policy_ids))
        unexpected = sorted(set(policy_ids) - metric_ids)
        raise RegressionEvaluationError(
            f"regression policies must match snapshot metrics; missing={missing}, "
            f"unexpected={unexpected}"
        )


def _require_non_empty(field_name: str, value: str) -> None:
    """식별자·버전의 빈 값과 비문자열 값을 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise RegressionEvaluationError(f"{field_name} must be a non-empty string")


def _validate_identifiers(field_name: str, identifiers: tuple[str, ...]) -> None:
    """사례 식별자의 빈 값과 중복을 차단해 선택 편향을 막는다."""
    if not identifiers:
        raise RegressionEvaluationError(f"{field_name} must not be empty")
    if any(not isinstance(identifier, str) or not identifier.strip() for identifier in identifiers):
        raise RegressionEvaluationError(f"{field_name} must contain non-empty strings")
    if len(set(identifiers)) != len(identifiers):
        raise RegressionEvaluationError(f"{field_name} must be unique")


def _require_finite(field_name: str, value: float) -> None:
    """NaN·무한대·불리언이 비교 결과를 우회하지 못하게 한다."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise RegressionEvaluationError(f"{field_name} must be a finite number")
