"""고정 검색 결과의 사례별 성공·실패를 외부 호출 없이 설명한다."""
from __future__ import annotations

from ai_platform.evaluation import (
    FIXED_RETRIEVAL_CASES,
    FIXED_RETRIEVAL_RESULTS_AT_3,
    evaluate_retrieval_cases,
)

CUTOFF = 3


def main() -> None:
    """고정 Top-3 결과를 사례 입력 순서대로 사람이 읽을 수 있게 출력한다."""
    case_metrics = evaluate_retrieval_cases(
        FIXED_RETRIEVAL_CASES,
        FIXED_RETRIEVAL_RESULTS_AT_3,
        k=CUTOFF,
    )
    print(f"Cutoff: {CUTOFF}")
    for metrics in case_metrics:
        retrieved = ", ".join(metrics.relevant_document_ids_retrieved) or "none"
        first_rank = str(metrics.first_relevant_rank) if metrics.first_relevant_rank else "none"
        print(
            f"{metrics.case_id}: retrieved={retrieved}; first_rank={first_rank}; "
            f"Recall@{CUTOFF}={metrics.recall_at_k:.6f}; "
            f"Precision@{CUTOFF}={metrics.precision_at_k:.6f}; "
            f"MRR={metrics.reciprocal_rank:.6f}; NDCG@{CUTOFF}={metrics.ndcg_at_k:.6f}"
        )


if __name__ == "__main__":
    main()
