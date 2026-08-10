"""고정 Latency·Token·Cost 기준선을 외부 호출 없이 출력한다."""
from __future__ import annotations

from ai_platform.evaluation import (
    FIXED_RECORDED_USAGE,
    FIXED_TOKEN_PRICING,
    FIXED_USAGE_CASES,
    evaluate_usage,
)


def main() -> None:
    """고정 사용량 평가 결과를 사람이 읽을 수 있는 형식으로 출력한다."""
    metrics = evaluate_usage(FIXED_USAGE_CASES, FIXED_RECORDED_USAGE, FIXED_TOKEN_PRICING)
    print(f"Evaluation cases: {metrics.cases_evaluated}")
    print(f"Mean latency (ms): {metrics.mean_latency_ms:.6f}")
    print(f"P95 latency (ms): {metrics.p95_latency_ms}")
    print(f"Total tokens: {metrics.total_tokens}")
    print(f"Total cost (USD): {metrics.total_cost_micro_usd / 1_000_000:.6f}")


if __name__ == "__main__":
    main()
