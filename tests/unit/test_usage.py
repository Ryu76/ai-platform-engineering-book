from decimal import Decimal

import pytest

from ai_platform.llm import (
    CostBudget,
    CostBudgetExceeded,
    CostEstimate,
    ModelPricing,
    TokenUsage,
    UsageConfigurationError,
    estimate_cost,
)


def test_estimate_cost_separates_input_output_and_total_with_decimal() -> None:
    pricing = ModelPricing(
        input_per_million_tokens=Decimal("2.50"),
        output_per_million_tokens=Decimal("10.00"),
    )

    estimate = estimate_cost(TokenUsage(input_tokens=1200, output_tokens=300), pricing)

    assert estimate.input_cost == Decimal("0.00300")
    assert estimate.output_cost == Decimal("0.00300")
    assert estimate.total_cost == Decimal("0.00600")
    assert estimate.currency == "USD"


def test_budget_allows_estimate_equal_to_its_cap() -> None:
    pricing = ModelPricing(
        input_per_million_tokens=Decimal("1"),
        output_per_million_tokens=Decimal("1"),
    )
    estimate = estimate_cost(TokenUsage(input_tokens=500000, output_tokens=500000), pricing)
    budget = CostBudget(maximum_cost=Decimal("1.0"))

    budget.require_within(estimate)


def test_budget_rejects_estimate_above_cap_during_local_estimate_check() -> None:
    pricing = ModelPricing(
        input_per_million_tokens=Decimal("4"),
        output_per_million_tokens=Decimal("12"),
    )
    estimate = estimate_cost(TokenUsage(input_tokens=100000, output_tokens=100000), pricing)
    budget = CostBudget(maximum_cost=Decimal("1.50"))

    with pytest.raises(CostBudgetExceeded, match="exceeds budget"):
        budget.require_within(estimate)


def test_budget_rejects_an_estimate_with_a_different_currency() -> None:
    pricing = ModelPricing(
        input_per_million_tokens=Decimal("1"),
        output_per_million_tokens=Decimal("1"),
        currency="KRW",
    )
    estimate = estimate_cost(TokenUsage(input_tokens=1, output_tokens=1), pricing)

    with pytest.raises(UsageConfigurationError, match="currency"):
        CostBudget(maximum_cost=Decimal("1"), currency="USD").require_within(estimate)


@pytest.mark.parametrize(
    ("input_cost", "output_cost", "total_cost", "currency", "expected_message"),
    [
        (Decimal("-0.01"), Decimal("0"), Decimal("0"), "USD", "input_cost"),
        (Decimal("0"), Decimal("NaN"), Decimal("0"), "USD", "output_cost"),
        (Decimal("0"), Decimal("0"), Decimal("Infinity"), "USD", "total_cost"),
        (Decimal("0.001"), Decimal("0.002"), Decimal("0.002"), "USD", "total_cost"),
        (Decimal("0"), Decimal("0"), Decimal("0"), "usd", "currency"),
    ],
)
def test_cost_estimate_rejects_invalid_or_non_additive_manual_values(
    input_cost: Decimal,
    output_cost: Decimal,
    total_cost: Decimal,
    currency: str,
    expected_message: str,
) -> None:
    """예산 검사를 우회할 수 있는 잘못된 수동 추정값을 만들 수 없어야 한다."""
    with pytest.raises(UsageConfigurationError, match=expected_message):
        CostEstimate(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            currency=currency,
        )


@pytest.mark.parametrize(
    "arguments",
    [
        {
            "input_per_million_tokens": Decimal("-0.01"),
            "output_per_million_tokens": Decimal("1"),
        },
        {
            "input_per_million_tokens": Decimal("NaN"),
            "output_per_million_tokens": Decimal("1"),
        },
        {
            "input_per_million_tokens": Decimal("1"),
            "output_per_million_tokens": Decimal("Infinity"),
        },
        {
            "input_per_million_tokens": Decimal("1"),
            "output_per_million_tokens": Decimal("1"),
            "currency": "usd",
        },
    ],
)
def test_pricing_rejects_invalid_values(arguments: dict[str, Decimal | str]) -> None:
    with pytest.raises(UsageConfigurationError):
        ModelPricing(**arguments)


@pytest.mark.parametrize(
    "usage",
    [
        TokenUsage(input_tokens=-1, output_tokens=0),
        TokenUsage(input_tokens=0, output_tokens=-1),
        TokenUsage(input_tokens=True, output_tokens=0),
    ],
)
def test_estimate_rejects_invalid_manually_created_usage(usage: TokenUsage) -> None:
    pricing = ModelPricing(
        input_per_million_tokens=Decimal("1"),
        output_per_million_tokens=Decimal("1"),
    )

    with pytest.raises(UsageConfigurationError, match="tokens"):
        estimate_cost(usage, pricing)


@pytest.mark.parametrize("maximum_cost", [Decimal("-0.01"), Decimal("NaN")])
def test_budget_rejects_invalid_cap(maximum_cost: Decimal) -> None:
    with pytest.raises(UsageConfigurationError):
        CostBudget(maximum_cost=maximum_cost)
