from decimal import Decimal

import pytest

from ai_platform.llm import (
    CostBudget,
    CostBudgetExceeded,
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
