"""외부 API 없이 기록된 토큰 사용량의 비용 상한을 점검하는 예제."""
from decimal import Decimal

from ai_platform.llm import CostBudget, ModelPricing, TokenUsage, estimate_cost


def main() -> None:
    """고정된 예시 사용량으로 비용 계산과 예산 확인을 재현한다."""
    pricing = ModelPricing(
        input_per_million_tokens=Decimal("2.50"),
        output_per_million_tokens=Decimal("10.00"),
        currency="USD",
    )
    usage = TokenUsage(input_tokens=1200, output_tokens=300)
    estimate = estimate_cost(usage, pricing)
    CostBudget(maximum_cost=Decimal("0.01"), currency="USD").require_within(estimate)

    print(f"입력 토큰: {usage.input_tokens}")
    print(f"출력 토큰: {usage.output_tokens}")
    print(f"입력 비용: {estimate.input_cost} {estimate.currency}")
    print(f"출력 비용: {estimate.output_cost} {estimate.currency}")
    print(f"총 추정 비용: {estimate.total_cost} {estimate.currency}")


if __name__ == "__main__":
    main()
