"""고정 dataset으로 Keyword Router 결정을 외부 호출 없이 평가한다."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Final

from ai_platform.router.base import NoEligibleRouteError, RoutingConfigurationError, RoutingRequest
from ai_platform.router.keyword import KeywordRouter, NoConfidentKeywordRouteError

_ZERO: Final = Decimal("0")
_ONE: Final = Decimal("1")


class KeywordRoutingOutcome(StrEnum):
    """고정 평가 사례가 기대하는 안전한 Keyword Router 결과 유형이다."""

    ROUTE = "route"
    NO_CONFIDENT_KEYWORD_ROUTE = "no_confident_keyword_route"
    NO_ELIGIBLE_POLICY_ROUTE = "no_eligible_policy_route"


class RoutingQualityGateError(RuntimeError):
    """고정 평가 dataset의 accuracy가 명시한 품질 기준보다 낮을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class KeywordRoutingExpectation:
    """한 평가 사례가 기대하는 route 또는 안전 실패 결과를 선언한다."""

    outcome: KeywordRoutingOutcome
    intent: str | None = None
    target_name: str | None = None

    def __post_init__(self) -> None:
        """성공 route와 안전 실패의 기대값을 모호하지 않게 검증한다."""
        if self.outcome is KeywordRoutingOutcome.ROUTE:
            _validate_identifier(self.intent, "expected intent")
            _validate_identifier(self.target_name, "expected target name")
            return
        if self.intent is not None or self.target_name is not None:
            raise RoutingConfigurationError(
                "safe-failure expectations must not declare an intent or target name"
            )


@dataclass(frozen=True, slots=True)
class KeywordRoutingEvaluationCase:
    """원문을 실행에만 사용하고 보고서에는 ID만 남기는 고정 평가 사례다."""

    case_id: str
    request: RoutingRequest
    expected: KeywordRoutingExpectation

    def __post_init__(self) -> None:
        """추적 가능한 사례 ID를 요구한다."""
        _validate_identifier(self.case_id, "evaluation case_id")


@dataclass(frozen=True, slots=True)
class KeywordRoutingEvaluationReport:
    """결정 일치율과 불일치 사례 ID만 담는 JSON 직렬화 가능한 평가 결과다."""

    total_cases: int
    correct_cases: int
    accuracy: Decimal
    correct_safe_failures: int
    mismatched_case_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """dataset 크기와 accuracy 집계를 일관된 범위로 제한한다."""
        if (
            isinstance(self.total_cases, bool)
            or not isinstance(self.total_cases, int)
            or self.total_cases < 1
        ):
            raise RoutingConfigurationError("total_cases must be a positive integer")
        if (
            isinstance(self.correct_cases, bool)
            or not isinstance(self.correct_cases, int)
            or not 0 <= self.correct_cases <= self.total_cases
        ):
            raise RoutingConfigurationError("correct_cases must be between 0 and total_cases")
        if (
            isinstance(self.correct_safe_failures, bool)
            or not isinstance(self.correct_safe_failures, int)
            or not 0 <= self.correct_safe_failures <= self.correct_cases
        ):
            raise RoutingConfigurationError(
                "correct_safe_failures must be between 0 and correct_cases"
            )
        _validate_unit_decimal(self.accuracy, "accuracy")
        if self.accuracy != Decimal(self.correct_cases) / Decimal(self.total_cases):
            raise RoutingConfigurationError(
                "accuracy must equal correct_cases divided by total_cases"
            )
        if len(set(self.mismatched_case_ids)) != len(self.mismatched_case_ids):
            raise RoutingConfigurationError("mismatched_case_ids must be unique")
        if len(self.mismatched_case_ids) != self.total_cases - self.correct_cases:
            raise RoutingConfigurationError("mismatched_case_ids must match incorrect case count")
        for case_id in self.mismatched_case_ids:
            _validate_identifier(case_id, "mismatched case_id")

    def meets_accuracy(self, minimum_accuracy: Decimal) -> bool:
        """명시한 0~1 품질 기준을 이 보고서가 통과하는지 반환한다."""
        _validate_unit_decimal(minimum_accuracy, "minimum_accuracy")
        return self.accuracy >= minimum_accuracy

    def require_minimum_accuracy(self, minimum_accuracy: Decimal) -> None:
        """기준 미달을 안전하게 막고, 기준과 실제 accuracy를 오류에 남긴다."""
        if not self.meets_accuracy(minimum_accuracy):
            raise RoutingQualityGateError(
                "keyword routing accuracy "
                f"{self.accuracy} is below required minimum {minimum_accuracy}"
            )

    def as_log_record(self) -> dict[str, object]:
        """사용자 원문 없이 JSON 직렬화 가능한 평가 요약을 반환한다."""
        return {
            "total_cases": self.total_cases,
            "correct_cases": self.correct_cases,
            "accuracy": str(self.accuracy),
            "correct_safe_failures": self.correct_safe_failures,
            "mismatched_case_ids": list(self.mismatched_case_ids),
        }


def evaluate_keyword_router(
    router: KeywordRouter,
    cases: tuple[KeywordRoutingEvaluationCase, ...],
) -> KeywordRoutingEvaluationReport:
    """동일한 고정 사례마다 route·안전 실패 결과를 평가해 accuracy를 계산한다."""
    if not cases:
        raise RoutingConfigurationError("keyword routing evaluation dataset must not be empty")
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise RoutingConfigurationError("keyword routing evaluation case_ids must be unique")

    correct_cases = 0
    correct_safe_failures = 0
    mismatched_case_ids: list[str] = []
    for case in cases:
        actual_outcome, actual_intent, actual_target_name = _route_case(router, case.request)
        if (
            actual_outcome is case.expected.outcome
            and actual_intent == case.expected.intent
            and actual_target_name == case.expected.target_name
        ):
            correct_cases += 1
            if actual_outcome is not KeywordRoutingOutcome.ROUTE:
                correct_safe_failures += 1
        else:
            mismatched_case_ids.append(case.case_id)

    total_cases = len(cases)
    return KeywordRoutingEvaluationReport(
        total_cases=total_cases,
        correct_cases=correct_cases,
        accuracy=Decimal(correct_cases) / Decimal(total_cases),
        correct_safe_failures=correct_safe_failures,
        mismatched_case_ids=tuple(mismatched_case_ids),
    )


def _route_case(
    router: KeywordRouter, request: RoutingRequest
) -> tuple[KeywordRoutingOutcome, str | None, str | None]:
    """정상 route와 이미 계약된 두 안전 실패를 평가 결과 유형으로 변환한다."""
    try:
        decision = router.route(request)
    except NoConfidentKeywordRouteError:
        return (KeywordRoutingOutcome.NO_CONFIDENT_KEYWORD_ROUTE, None, None)
    except NoEligibleRouteError:
        return (KeywordRoutingOutcome.NO_ELIGIBLE_POLICY_ROUTE, None, None)
    return (KeywordRoutingOutcome.ROUTE, decision.intent, decision.target.name)


def _validate_identifier(value: object, name: str) -> None:
    """비어 있거나 문자열이 아닌 식별자를 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise RoutingConfigurationError(f"{name} must be a nonempty string")


def _validate_unit_decimal(value: object, name: str) -> None:
    """threshold와 accuracy를 유한한 Decimal 0 이상 1 이하로 제한한다."""
    if not isinstance(value, Decimal):
        raise RoutingConfigurationError(f"{name} must be a Decimal")
    try:
        valid = value.is_finite() and _ZERO <= value <= _ONE
    except InvalidOperation as error:
        raise RoutingConfigurationError(
            f"{name} must be a finite Decimal between 0 and 1"
        ) from error
    if not valid:
        raise RoutingConfigurationError(f"{name} must be a finite Decimal between 0 and 1")
