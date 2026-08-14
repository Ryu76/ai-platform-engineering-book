"""Volume 08 Keyword Router 평가의 외부 호출 없는 결정론적 계약 테스트."""

import json
from decimal import Decimal

import pytest

from ai_platform.router import (
    KeywordRoute,
    KeywordRouter,
    KeywordRoutingEvaluationCase,
    KeywordRoutingExpectation,
    KeywordRoutingOutcome,
    PolicyRouter,
    RouteTarget,
    RouteTargetKind,
    RoutingConfigurationError,
    RoutingQualityGateError,
    RoutingRequest,
    RoutingRequirements,
    evaluate_keyword_router,
)


def _target(name: str, capabilities: frozenset[str]) -> RouteTarget:
    return RouteTarget(
        name=name,
        kind=RouteTargetKind.AGENT,
        capabilities=capabilities,
        estimated_cost=Decimal("0.001"),
        estimated_latency_ms=50,
    )


def _router() -> KeywordRouter:
    return KeywordRouter(
        name="evaluation-keyword-router",
        policy_router=PolicyRouter(
            name="evaluation-policy",
            targets=(
                _target("general-agent", frozenset({"respond"})),
                _target("order-agent", frozenset({"lookup_order", "respond"})),
                _target("refund-agent", frozenset({"issue_refund", "respond"})),
            ),
        ),
        routes=(
            KeywordRoute(
                intent="order_tracking",
                keywords=frozenset({"order", "tracking"}),
                required_capabilities=frozenset({"lookup_order", "respond"}),
                confidence=Decimal("0.90"),
            ),
            KeywordRoute(
                intent="refund_request",
                keywords=frozenset({"refund"}),
                required_capabilities=frozenset({"issue_refund", "respond"}),
                confidence=Decimal("0.85"),
            ),
        ),
        minimum_confidence=Decimal("0.80"),
    )


def _case(
    case_id: str,
    text: str,
    expected: KeywordRoutingExpectation,
    *,
    permitted_target_names: frozenset[str] | None = None,
) -> KeywordRoutingEvaluationCase:
    return KeywordRoutingEvaluationCase(
        case_id=case_id,
        request=RoutingRequest(
            request_id=f"request-{case_id}",
            text=text,
            requirements=RoutingRequirements(permitted_target_names=permitted_target_names),
        ),
        expected=expected,
    )


def test_evaluation_measures_routes_and_two_safe_failure_modes() -> None:
    report = evaluate_keyword_router(
        _router(),
        (
            _case(
                "order-route",
                "ORDER tracking please",
                KeywordRoutingExpectation(
                    outcome=KeywordRoutingOutcome.ROUTE,
                    intent="order_tracking",
                    target_name="order-agent",
                ),
            ),
            _case(
                "refund-route",
                "refund please",
                KeywordRoutingExpectation(
                    outcome=KeywordRoutingOutcome.ROUTE,
                    intent="refund_request",
                    target_name="refund-agent",
                ),
            ),
            _case(
                "unknown-safe-failure",
                "hello there",
                KeywordRoutingExpectation(outcome=KeywordRoutingOutcome.NO_CONFIDENT_KEYWORD_ROUTE),
            ),
            _case(
                "permission-safe-failure",
                "refund please",
                KeywordRoutingExpectation(outcome=KeywordRoutingOutcome.NO_ELIGIBLE_POLICY_ROUTE),
                permitted_target_names=frozenset({"general-agent"}),
            ),
        ),
    )

    assert report.total_cases == 4
    assert report.correct_cases == 4
    assert report.accuracy == Decimal("1")
    assert report.correct_safe_failures == 2
    assert report.mismatched_case_ids == ()
    assert report.meets_accuracy(Decimal("1"))
    report.require_minimum_accuracy(Decimal("1"))


def test_evaluation_reports_mismatches_and_enforces_an_explicit_accuracy_gate() -> None:
    report = evaluate_keyword_router(
        _router(),
        (
            _case(
                "wrong-expected-target",
                "order tracking please",
                KeywordRoutingExpectation(
                    outcome=KeywordRoutingOutcome.ROUTE,
                    intent="order_tracking",
                    target_name="refund-agent",
                ),
            ),
            _case(
                "correct-safe-failure",
                "unrelated request",
                KeywordRoutingExpectation(outcome=KeywordRoutingOutcome.NO_CONFIDENT_KEYWORD_ROUTE),
            ),
        ),
    )

    assert report.correct_cases == 1
    assert report.accuracy == Decimal("0.5")
    assert report.mismatched_case_ids == ("wrong-expected-target",)
    with pytest.raises(RoutingQualityGateError, match="below required minimum 0.75"):
        report.require_minimum_accuracy(Decimal("0.75"))


def test_evaluation_report_log_is_json_serializable_and_omits_user_text() -> None:
    secret_text = "do not log this user secret"
    report = evaluate_keyword_router(
        _router(),
        (
            _case(
                "private-case",
                secret_text,
                KeywordRoutingExpectation(outcome=KeywordRoutingOutcome.NO_CONFIDENT_KEYWORD_ROUTE),
            ),
        ),
    )

    record = report.as_log_record()

    assert record == {
        "total_cases": 1,
        "correct_cases": 1,
        "accuracy": "1",
        "correct_safe_failures": 1,
        "mismatched_case_ids": [],
    }
    assert secret_text not in json.dumps(record)
    json.dumps(record)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: KeywordRoutingExpectation(
            outcome=KeywordRoutingOutcome.ROUTE,
            intent="order_tracking",
        ),
        lambda: KeywordRoutingExpectation(
            outcome=KeywordRoutingOutcome.NO_CONFIDENT_KEYWORD_ROUTE,
            intent="must-not-be-set",
        ),
        lambda: evaluate_keyword_router(_router(), ()),
        lambda: evaluate_keyword_router(
            _router(),
            (
                _case(
                    "duplicate-case",
                    "hello",
                    KeywordRoutingExpectation(
                        outcome=KeywordRoutingOutcome.NO_CONFIDENT_KEYWORD_ROUTE
                    ),
                ),
                _case(
                    "duplicate-case",
                    "still hello",
                    KeywordRoutingExpectation(
                        outcome=KeywordRoutingOutcome.NO_CONFIDENT_KEYWORD_ROUTE
                    ),
                ),
            ),
        ),
    ],
)
def test_evaluation_rejects_ambiguous_expectations_and_invalid_datasets(factory: object) -> None:
    with pytest.raises(RoutingConfigurationError):
        factory()  # type: ignore[operator]


@pytest.mark.parametrize("minimum_accuracy", [Decimal("-0.01"), Decimal("1.01"), Decimal("NaN")])
def test_evaluation_rejects_invalid_accuracy_thresholds(minimum_accuracy: Decimal) -> None:
    report = evaluate_keyword_router(
        _router(),
        (
            _case(
                "threshold-case",
                "hello",
                KeywordRoutingExpectation(outcome=KeywordRoutingOutcome.NO_CONFIDENT_KEYWORD_ROUTE),
            ),
        ),
    )

    with pytest.raises(RoutingConfigurationError):
        report.meets_accuracy(minimum_accuracy)
