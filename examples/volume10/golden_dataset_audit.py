"""고정 골든 데이터셋의 구성과 버전을 외부 호출 없이 감사한다."""
from __future__ import annotations

from ai_platform.evaluation import FIXED_GOLDEN_DATASET, summarize_golden_dataset


def main() -> None:
    """사례·기대 동작·카테고리 수를 안정된 순서로 출력한다."""
    summary = summarize_golden_dataset(FIXED_GOLDEN_DATASET)
    category_summary = ", ".join(
        f"{category}={count}" for category, count in summary.categories
    )
    print(f"Dataset: {summary.dataset_id}")
    print(f"Version: {summary.version}")
    print(f"Cases: {summary.cases_total}")
    print(f"Answer cases: {summary.answer_cases}")
    print(f"Abstain cases: {summary.abstain_cases}")
    print(f"Categories: {category_summary}")


if __name__ == "__main__":
    main()
