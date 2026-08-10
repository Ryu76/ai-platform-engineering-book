"""고정 후보로 1차 검색 순위와 local rerank 품질을 비교한다."""
from __future__ import annotations

from ai_platform.reranker import (
    Candidate,
    LexicalCrossEncoder,
    evaluate_ranking,
    mean_ranking_metrics,
)

FIXTURES = (
    (
        "비밀번호 재설정 방법",
        {"account-recovery"},
        (
            Candidate("password-policy", "비밀번호 정책은 90일마다 변경합니다.", 0.99),
            Candidate(
                "account-recovery",
                "비밀번호를 잊었으면 계정 설정에서 비밀번호 재설정 방법을 따르세요.",
                0.71,
            ),
            Candidate("incident-guide", "서비스 장애 보고와 복구 절차입니다.", 0.63),
        ),
    ),
    (
        "장애 대응 연락처",
        {"incident-contacts"},
        (
            Candidate("infra-overview", "인프라 장애 대응 원칙과 점검 목록입니다.", 0.96),
            Candidate(
                "incident-contacts",
                "장애 대응 연락처: 온콜 운영팀 02-0000-0000으로 즉시 알립니다.",
                0.74,
            ),
            Candidate("release-calendar", "배포 일정과 변경 승인 일정을 확인합니다.", 0.57),
        ),
    ),
)


def main() -> None:
    """외부 API·모델 다운로드 없이 두 질의의 before/after 지표를 출력한다."""
    reranker = LexicalCrossEncoder()
    retriever_metrics = []
    reranker_metrics = []

    for query, relevant_ids, candidates in FIXTURES:
        retriever_ids = [candidate.candidate_id for candidate in candidates]
        reranked = reranker.rerank(query, candidates)
        reranked_ids = [result.candidate.candidate_id for result in reranked]
        retriever_metrics.append(evaluate_ranking(retriever_ids, relevant_ids, k=1))
        reranker_metrics.append(evaluate_ranking(reranked_ids, relevant_ids, k=1))
        print(f"query={query}")
        print("retriever_top1=" + retriever_ids[0])
        print(
            "reranker_top1="
            f"{reranked_ids[0]}; cross_encoder_score={reranked[0].cross_encoder_score}"
        )

    baseline = mean_ranking_metrics(retriever_metrics)
    reranked_summary = mean_ranking_metrics(reranker_metrics)
    print(
        "retriever_mean@1="
        f"precision={baseline.mean_precision_at_k:.3f}; "
        f"recall={baseline.mean_recall_at_k:.3f}; "
        f"mrr={baseline.mean_reciprocal_rank:.3f}; ndcg={baseline.mean_ndcg_at_k:.3f}"
    )
    print(
        "reranker_mean@1="
        f"precision={reranked_summary.mean_precision_at_k:.3f}; "
        f"recall={reranked_summary.mean_recall_at_k:.3f}; "
        f"mrr={reranked_summary.mean_reciprocal_rank:.3f}; "
        f"ndcg={reranked_summary.mean_ndcg_at_k:.3f}"
    )


if __name__ == "__main__":
    main()
