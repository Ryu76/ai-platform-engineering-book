"""고정 후보로 1차 검색 순위와 local rerank 품질을 비교한다."""
from __future__ import annotations

from collections.abc import Sequence

from ai_platform.reranker import (
    BatchRerankPolicy,
    Candidate,
    CrossEncoderModelAdapter,
    RelevanceJudgment,
    RerankDecision,
    evaluate_graded_ranking,
    evaluate_ranking,
    mean_ranking_metrics,
    measure_rerank,
    measure_threshold_sweep,
    rerank_with_adapter,
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


class FixtureCrossEncoderModel:
    """다운로드 모델 없이 adapter 경계를 실행하는 결정론적 pair model fixture다."""

    def predict(
        self, pairs: Sequence[tuple[str, str]], *, timeout_ns: int
    ) -> tuple[float, ...]:
        """고정 query-document pair에 재현 가능한 연속 score를 돌려준다."""
        if timeout_ns < 1:
            raise TimeoutError("fixture model received no time budget")
        return tuple(self._score(query, text) for query, text in pairs)

    @staticmethod
    def _score(query: str, text: str) -> float:
        if "비밀번호" in query:
            if "잊었으면" in text:
                return 0.95
            if "정책" in text:
                return 0.20
            return 0.01
        if "연락처" in query:
            if "온콜" in text:
                return 0.95
            if "원칙" in text:
                return 0.20
        return 0.01


def _print_adapter_measurement() -> None:
    """동일 fixture로 batch adapter의 before/after ranking metrics를 local 측정한다."""
    adapter = CrossEncoderModelAdapter("fixture-cross-encoder-v1", FixtureCrossEncoderModel())
    policy = BatchRerankPolicy(max_batch_size=2, timeout_ns=1_000_000_000)
    retriever_metrics = []
    adapter_metrics = []
    retriever_graded_ndcg = []
    adapter_graded_ndcg = []
    batch_count = 0
    pair_evaluations = 0
    elapsed_ns = 0
    for query, judgments, candidates in FIXTURES:
        relevant_ids = {
            judgment.candidate_id for judgment in judgments if judgment.relevance_grade >= 2
        }
        result = rerank_with_adapter(query, candidates, adapter, policy)
        if result.outcome != "reranked":
            raise RuntimeError(f"fixture adapter unexpectedly fell back: {result.fallback_reason}")
        retriever_ids = [candidate.candidate_id for candidate in candidates]
        reranked_ids = [item.candidate.candidate_id for item in result.ranked]
        retriever_metrics.append(evaluate_ranking(retriever_ids, relevant_ids, k=1))
        adapter_metrics.append(evaluate_ranking(reranked_ids, relevant_ids, k=1))
        retriever_graded_ndcg.append(
            evaluate_graded_ranking(retriever_ids, judgments, k=1).ndcg_at_k
        )
        adapter_graded_ndcg.append(evaluate_graded_ranking(reranked_ids, judgments, k=1).ndcg_at_k)
        batch_count += result.batch_count
        pair_evaluations += result.pair_evaluations
        elapsed_ns += result.elapsed_ns

    retriever_summary = mean_ranking_metrics(retriever_metrics)
    adapter_summary = mean_ranking_metrics(adapter_metrics)
    fixture_count = len(FIXTURES)
    print(
        "adapter_candidate_count=3; top_k=1; "
        f"batch_count={batch_count}; pair_evaluations={pair_evaluations}; elapsed_ns={elapsed_ns}; "
        f"outcome=reranked; retriever_precision={retriever_summary.mean_precision_at_k:.3f}; "
        f"adapter_precision={adapter_summary.mean_precision_at_k:.3f}; "
        f"retriever_graded_ndcg={sum(retriever_graded_ndcg) / fixture_count:.3f}; "
        f"adapter_graded_ndcg={sum(adapter_graded_ndcg) / fixture_count:.3f}"
    )


def _print_threshold_sweep() -> None:
    """같은 pair score에서 threshold policy만 바꾼 acceptance/quality trade-off를 측정한다."""
    thresholds = (1, 303, 304, 305)
    decision_by_threshold: dict[int, list[tuple[RerankDecision, set[str]]]] = {
        threshold: [] for threshold in thresholds
    }
    pair_evaluations = 0
    elapsed_ns = 0
    for query, judgments, candidates in FIXTURES:
        relevant_ids = {
            judgment.candidate_id for judgment in judgments if judgment.relevance_grade >= 2
        }
        sweep = measure_threshold_sweep(
            query, candidates, min_scores=thresholds, top_k=1
        )
        pair_evaluations += sweep.rerank_measurement.pair_evaluations
        elapsed_ns += sweep.rerank_measurement.elapsed_ns
        for decision in sweep.decisions:
            decision_by_threshold[decision.min_score].append((decision, relevant_ids))

    fixture_count = len(FIXTURES)
    for threshold in thresholds:
        decisions = decision_by_threshold[threshold]
        accepted_count = sum(decision.outcome == "accepted" for decision, _ in decisions)
        effective_metrics = mean_ranking_metrics(
            [
                evaluate_ranking(
                    []
                    if decision.selected is None
                    else [decision.selected.candidate.candidate_id],
                    relevant_ids,
                    k=1,
                )
                for decision, relevant_ids in decisions
            ]
        )
        conditional_precision = (
            0.0
            if accepted_count == 0
            else sum(
                decision.selected is not None
                and decision.selected.candidate.candidate_id in relevant_ids
                for decision, relevant_ids in decisions
            )
            / accepted_count
        )
        print(
            f"threshold={threshold}; candidate_count=3; top_k=1; "
            f"shared_pair_evaluations={pair_evaluations}; shared_elapsed_ns={elapsed_ns}; "
            f"accepted={accepted_count}/{fixture_count}; "
            f"acceptance_rate={accepted_count / fixture_count:.3f}; "
            f"conditional_precision={conditional_precision:.3f}; "
            f"effective_precision={effective_metrics.mean_precision_at_k:.3f}; "
            f"effective_recall={effective_metrics.mean_recall_at_k:.3f}"
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

    _print_threshold_sweep()
    _print_adapter_measurement()
    no_answer_query, no_answer_candidates = NO_ANSWER_FIXTURE
    decision = rerank_with_threshold(no_answer_query, no_answer_candidates, min_score=1)
    print(
        f"threshold=1; outcome={decision.outcome}; top_score={decision.top_score}; "
        f"fallback_reason={decision.fallback_reason}"
    )


if __name__ == "__main__":
    main()
