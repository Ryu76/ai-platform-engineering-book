"""고정 골든 데이터셋의 RAG 검색 품질을 외부 호출 없이 측정한다."""
from __future__ import annotations

from ai_platform.evaluation import (
    FIXED_RETRIEVAL_CASES,
    FIXED_RETRIEVAL_RESULTS_AT_3,
    evaluate_retrieval,
)


def main() -> None:
    """고정 Top-3 순위의 검색 평가 보고서를 출력한다."""
    metrics = evaluate_retrieval(
        FIXED_RETRIEVAL_CASES,
        FIXED_RETRIEVAL_RESULTS_AT_3,
        k=3,
    )
    print(f"평가 사례: {metrics.cases_evaluated}")
    print(f"Recall@3: {metrics.recall_at_k:.6f}")
    print(f"Precision@3: {metrics.precision_at_k:.6f}")
    print(f"Hit Rate@3: {metrics.hit_rate_at_k:.6f}")
    print(f"MRR: {metrics.mean_reciprocal_rank:.6f}")
    print(f"NDCG@3: {metrics.ndcg_at_k:.6f}")


if __name__ == "__main__":
    main()
