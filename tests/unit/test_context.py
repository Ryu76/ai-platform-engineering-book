import pytest

from ai_platform.llm import ContextBudget, ContextBudgetError


def test_context_budget_calculates_remaining_tokens_for_a_request_plan() -> None:
    budget = ContextBudget(context_window_tokens=2048, reserved_output_tokens=400)

    assessment = budget.assess(input_tokens=1500)

    assert assessment.total_planned_tokens == 1900
    assert assessment.remaining_tokens == 148
    assert assessment.fits is True
    assert budget.available_input_tokens == 1648


def test_context_budget_marks_overflow_without_hiding_the_negative_margin() -> None:
    budget = ContextBudget(context_window_tokens=2048, reserved_output_tokens=400)

    assessment = budget.assess(input_tokens=1800)

    assert assessment.total_planned_tokens == 2200
    assert assessment.remaining_tokens == -152
    assert assessment.fits is False


def test_context_budget_requires_a_plan_to_fit_before_a_live_request() -> None:
    budget = ContextBudget(context_window_tokens=100, reserved_output_tokens=20)

    with pytest.raises(ContextBudgetError, match="at most 80"):
        budget.require_fits(input_tokens=81)


@pytest.mark.parametrize(
    ("window", "reserved"),
    [
        (0, 0),
        (True, 0),
        (100, -1),
        (100, True),
        (100, 101),
    ],
)
def test_context_budget_rejects_invalid_window_or_reservation(window: int, reserved: int) -> None:
    with pytest.raises(ContextBudgetError):
        ContextBudget(context_window_tokens=window, reserved_output_tokens=reserved)


@pytest.mark.parametrize("input_tokens", [-1, True])
def test_context_budget_rejects_invalid_input_count(input_tokens: int) -> None:
    budget = ContextBudget(context_window_tokens=100, reserved_output_tokens=20)

    with pytest.raises(ContextBudgetError, match="input_tokens"):
        budget.assess(input_tokens)
