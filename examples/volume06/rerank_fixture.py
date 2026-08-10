"""고정 후보로 1차 검색 순위와 local rerank 품질을 비교한다."""
from __future__ import annotations

from ai_platform.reranker import (
    Candidate,
    RelevanceJudgment,
    evaluate_graded_ranking,
    evaluate_ranking,
    mean_ranking_metrics,
    measure_rerank,
    rerank_with_threshold,
)

FIXTURES = (
    (
        "비밀번호 재설정 방법",
        (
            RelevanceJudgment("password-policy", 1),
            RelevanceJudgment("account-recovery", 3),
            RelevanceJudgment("incident-guide", 0),
        ),
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
        (
            RelevanceJudgment("infra-overview", 1),
            RelevanceJudgment("incident-contacts", 3),
            RelevanceJudgment("release-calendar", 0),
        ),
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

NO_ANSWER_FIXTURE = (
    "휴가 신청 방법",
    (Candidate("incident", "장애 대응 절차와 연락망입니다.", 0.9),),
)


def main() -> None:
    """외부 API·모델 다운로드 없이 fixed-fixture rerank sweep을 출력한다."""
    for candidate_count in range(1, 4):
        for top_k in range(1, candidate_count + 1):
            retriever_metrics = []
            reranker_metrics = []
            retriever_graded_ndcg = []
            reranker_graded_ndcg = []
            elapsed_ns = 0
            pair_evaluations = 0
            for query, judgments, candidates in FIXTURES:
                limited_candidates = candidates[:candidate_count]
                relevant_ids = {
                    judgment.candidate_id
                    for judgment in judgments
                    if judgment.relevance_grade >= 2
                }
                retriever_ids = [candidate.candidate_id for candidate in limited_candidates]
                measurement = measure_rerank(query, limited_candidates, top_k=top_k)
                reranked_ids = [result.candidate.candidate_id for result in measurement.ranked]
                retriever_metrics.append(evaluate_ranking(retriever_ids, relevant_ids, k=top_k))
                reranker_metrics.append(evaluate_ranking(reranked_ids, relevant_ids, k=top_k))
                retriever_graded_ndcg.append(
                    evaluate_graded_ranking(retriever_ids, judgments, k=top_k).ndcg_at_k
                )
                reranker_graded_ndcg.append(
                    evaluate_graded_ranking(reranked_ids, judgments, k=top_k).ndcg_at_k
                )
                elapsed_ns += measurement.elapsed_ns
                pair_evaluations += measurement.pair_evaluations

            baseline = mean_ranking_metrics(retriever_metrics)
            reranked_summary = mean_ranking_metrics(reranker_metrics)
            fixture_count = len(FIXTURES)
            print(
                f"candidate_count={candidate_count}; top_k={top_k}; "
                f"pair_evaluations={pair_evaluations}; elapsed_ns={elapsed_ns}; "
                f"retriever_precision={baseline.mean_precision_at_k:.3f}; "
                f"reranker_precision={reranked_summary.mean_precision_at_k:.3f}; "
                f"retriever_recall={baseline.mean_recall_at_k:.3f}; "
                f"reranker_recall={reranked_summary.mean_recall_at_k:.3f}; "
                f"retriever_mrr={baseline.mean_reciprocal_rank:.3f}; "
                f"reranker_mrr={reranked_summary.mean_reciprocal_rank:.3f}; "
                f"retriever_ndcg={baseline.mean_ndcg_at_k:.3f}; "
                f"reranker_ndcg={reranked_summary.mean_ndcg_at_k:.3f}; "
                f"retriever_graded_ndcg={sum(retriever_graded_ndcg) / fixture_count:.3f}; "
                f"reranker_graded_ndcg={sum(reranker_graded_ndcg) / fixture_count:.3f}"
            )

    no_answer_query, no_answer_candidates = NO_ANSWER_FIXTURE
    decision = rerank_with_threshold(no_answer_query, no_answer_candidates, min_score=1)
    print(
        f"threshold=1; outcome={decision.outcome}; top_score={decision.top_score}; "
        f"fallback_reason={decision.fallback_reason}"
    )


if __name__ == "__main__":
    main()
