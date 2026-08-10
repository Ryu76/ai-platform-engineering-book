"""Volume 10의 고정 Latency·Token·Cost 평가 계약을 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.evaluation import (
    FIXED_GOLDEN_DATASET,
    FIXED_RECORDED_USAGE,
    FIXED_TOKEN_PRICING,
    FIXED_USAGE_CASES,
    RecordedUsage,
    TokenPricing,
    UsageCase,
    UsageEvaluationError,
    evaluate_usage,
    evaluate_usage_cases,
)


def test_fixed_usage_has_reproducible_latency_token_and_cost_metrics() -> None:
    """동일한 고정 기록과 단가는 항상 동일한 기준선을 만든다."""
    metrics = evaluate_usage(FIXED_USAGE_CASES, FIXED_RECORDED_USAGE, FIXED_TOKEN_PRICING)

    assert metrics.cases_evaluated == 5
    assert metrics.total_latency_ms == 920
    assert metrics.mean_latency_ms == pytest.approx(184.0)
    assert metrics.p95_latency_ms == 340
    assert metrics.total_input_tokens == 780
    assert metrics.total_output_tokens == 460
    assert metrics.total_tokens == 1240
    assert metrics.total_cost_micro_usd == 5240


def test_usage_cases_share_the_versioned_golden_case_ids() -> None:
    """사용량 기준선이 다른 사례 집합으로 바뀌는 것을 막는다."""
    assert tuple(case.case_id for case in FIXED_USAGE_CASES) == tuple(
        case.case_id for case in FIXED_GOLDEN_DATASET.cases
    )


def test_case_metrics_apply_fixed_pricing_in_stable_case_order() -> None:
    """비용은 환경 가격표가 아니라 고정 마이크로 USD 단가로 계산한다."""
    case_metrics = evaluate_usage_cases(
        FIXED_USAGE_CASES, FIXED_RECORDED_USAGE, FIXED_TOKEN_PRICING
    )

    assert tuple(metric.case_id for metric in case_metrics) == (
        "access-reset",
        "expense-receipt",
        "incident-response",
        "benefits-enrollment",
        "office-parking",
    )
    assert case_metrics[0].total_tokens == 230
    assert case_metrics[0].cost_micro_usd == 1000
    assert case_metrics[4].cost_micro_usd == 400


def test_usage_metrics_use_nearest_rank_p95_without_wall_clock_measurement() -> None:
    """P95는 기록된 다섯 latency를 정렬한 nearest-rank 위치로 고정한다."""
    metrics = evaluate_usage(FIXED_USAGE_CASES, FIXED_RECORDED_USAGE, FIXED_TOKEN_PRICING)

    assert metrics.p95_latency_ms == 340


def test_usage_metrics_reject_missing_or_unexpected_records() -> None:
    """좋은 일부 사례만 골라 평균 시간·비용을 계산하지 못하게 한다."""
    incomplete = {"access-reset": FIXED_RECORDED_USAGE["access-reset"]}

    with pytest.raises(UsageEvaluationError, match="missing="):
        evaluate_usage(FIXED_USAGE_CASES, incomplete, FIXED_TOKEN_PRICING)


def test_usage_metrics_reject_record_key_and_payload_case_id_mismatch() -> None:
    """사전 키와 기록 내부 ID가 다르면 다른 사례의 비용을 합산하지 않는다."""
    usage = dict(FIXED_RECORDED_USAGE)
    usage["access-reset"] = RecordedUsage("expense-receipt", 120, 140, 90)

    with pytest.raises(UsageEvaluationError, match="key and case_id"):
        evaluate_usage(FIXED_USAGE_CASES, usage, FIXED_TOKEN_PRICING)


@pytest.mark.parametrize(
    ("latency_ms", "input_tokens", "output_tokens", "message"),
    [
        (0, 1, 1, "positive"),
        (-1, 1, 1, "positive"),
        (1, -1, 1, "non-negative"),
        (1, 1, -1, "non-negative"),
        (True, 1, 1, "positive"),
    ],
)
def test_recorded_usage_rejects_invalid_measurements(
    latency_ms: int, input_tokens: int, output_tokens: int, message: str
) -> None:
    """실제 시계·SDK 형식에 기대지 않고 입력 단위를 엄격히 검증한다."""
    with pytest.raises(UsageEvaluationError, match=message):
        RecordedUsage("case-a", latency_ms, input_tokens, output_tokens)


@pytest.mark.parametrize("input_price", [-1, 1.5, True])
def test_token_pricing_rejects_invalid_micro_usd_rates(input_price: int) -> None:
    """부동 소수 가격이나 음수 단가는 비용 기준선을 흔들 수 없다."""
    with pytest.raises(UsageEvaluationError, match="non-negative"):
        TokenPricing(input_price, 8)  # type: ignore[arg-type]


def test_usage_cases_reject_duplicate_case_ids() -> None:
    """동일 사례를 두 번 넣어 평균을 왜곡하지 않는다."""
    with pytest.raises(UsageEvaluationError, match="unique"):
        evaluate_usage(
            (UsageCase("case-a"), UsageCase("case-a")),
            {"case-a": RecordedUsage("case-a", 1, 0, 0)},
            TokenPricing(0, 0),
        )
