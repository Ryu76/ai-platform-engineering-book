"""LLM 토큰 사용량을 외부 호출 없이 비용으로 추정하는 도구."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from ai_platform.llm.client import TokenUsage

_TOKENS_PER_MILLION = Decimal("1000000")


class UsageConfigurationError(ValueError):
    """가격 또는 예산 설정이 유효하지 않을 때 발생한다."""


class CostBudgetExceeded(RuntimeError):
    """추정 비용 검사에서 예산 상한을 넘었을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """모델의 입력·출력 100만 토큰당 가격을 나타낸다."""

    input_per_million_tokens: Decimal
    output_per_million_tokens: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        """음수·비유한 가격과 모호한 통화 코드를 차단한다."""
        _validate_nonnegative_decimal(
            self.input_per_million_tokens, "input_per_million_tokens"
        )
        _validate_nonnegative_decimal(
            self.output_per_million_tokens, "output_per_million_tokens"
        )
        _validate_currency(self.currency)


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """입력·출력 토큰별 비용과 합계를 분리해 보관한다."""

    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal
    currency: str

    def __post_init__(self) -> None:
        """수동 생성한 추정값도 유한한 금액·통화·합계 계약을 지키게 한다."""
        _validate_nonnegative_decimal(self.input_cost, "input_cost")
        _validate_nonnegative_decimal(self.output_cost, "output_cost")
        _validate_nonnegative_decimal(self.total_cost, "total_cost")
        _validate_currency(self.currency)
        if self.input_cost + self.output_cost != self.total_cost:
            raise UsageConfigurationError("total_cost must equal input_cost plus output_cost")


@dataclass(frozen=True, slots=True)
class CostBudget:
    """한 번의 요청 또는 작업에 적용할 명시적인 추정 비용 상한이다."""

    maximum_cost: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        """음수 예산과 모호한 통화 코드를 차단한다."""
        _validate_nonnegative_decimal(self.maximum_cost, "maximum_cost")
        _validate_currency(self.currency)

    def require_within(self, estimate: CostEstimate) -> None:
        """추정 비용이 상한 또는 통화 계약을 벗어나면 검사에 실패시킨다."""
        if estimate.currency != self.currency:
            raise UsageConfigurationError("estimate currency must match budget currency")
        if estimate.total_cost > self.maximum_cost:
            raise CostBudgetExceeded(
                f"estimated cost {estimate.total_cost} {estimate.currency} exceeds "
                f"budget {self.maximum_cost} {self.currency}"
            )


def estimate_cost(usage: TokenUsage, pricing: ModelPricing) -> CostEstimate:
    """제공자 사용량과 고정 가격표로 비용을 결정론적으로 계산한다.

    가격표는 제공자 웹사이트에서 확인한 값을 사람이 명시적으로 입력한다.
    이 함수는 네트워크 요청, 환율 변환, 반올림을 수행하지 않는다.
    """
    _validate_usage(usage)
    input_cost = (
        Decimal(usage.input_tokens) * pricing.input_per_million_tokens / _TOKENS_PER_MILLION
    )
    output_cost = (
        Decimal(usage.output_tokens) * pricing.output_per_million_tokens / _TOKENS_PER_MILLION
    )
    return CostEstimate(
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
        currency=pricing.currency,
    )


def _validate_usage(usage: TokenUsage) -> None:
    """수동으로 생성한 사용량도 정수·0 이상 계약을 만족하게 한다."""
    for name, value in (
        ("input_tokens", usage.input_tokens),
        ("output_tokens", usage.output_tokens),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise UsageConfigurationError(f"{name} must be a nonnegative integer")


def _validate_nonnegative_decimal(value: Decimal, name: str) -> None:
    """금액 계산에서 부동소수점과 NaN·Infinity를 허용하지 않는다."""
    if not isinstance(value, Decimal):
        raise UsageConfigurationError(f"{name} must be a Decimal")
    try:
        is_valid = value.is_finite() and value >= Decimal("0")
    except InvalidOperation as error:
        raise UsageConfigurationError(f"{name} must be a finite nonnegative Decimal") from error
    if not is_valid:
        raise UsageConfigurationError(f"{name} must be a finite nonnegative Decimal")


def _validate_currency(currency: str) -> None:
    """비교 가능한 세 글자 대문자 통화 코드만 허용한다."""
    if (
        not isinstance(currency, str)
        or len(currency) != 3
        or not currency.isalpha()
        or not currency.isupper()
    ):
        raise UsageConfigurationError("currency must be a three-letter uppercase code")
