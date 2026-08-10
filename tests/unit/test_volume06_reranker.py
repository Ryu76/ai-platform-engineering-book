"""Volume 06 결정론적 Cross-Encoder reranker와 ranking metrics 계약 테스트."""
from __future__ import annotations

import math

import pytest

from ai_platform.reranker import (
    Candidate,
    LexicalCrossEncoder,
    RankingMetrics,
    RerankerConfigurationError,
    evaluate_ranking,
    mean_ranking_metrics,
)


def test_reranker_promotes_candidate_with_full_query_coverage() -> None:
    """1차 점수가 높아도 pair relevance가 낮으면 재정렬에서 뒤로 가야 한다."""
    candidates = (
        Candidate("policy", "비밀번호 정책은 주기적으로 변경합니다.", 0.99),
        Candidate("recovery", "비밀번호 재설정 방법은 계정 설정에서 확인합니다.", 0.71),
        Candidate("incident", "장애 보고 절차입니다.", 0.61),
    )

    reranked = LexicalCrossEncoder().rerank("비밀번호 재설정 방법", candidates)

    assert [result.candidate.candidate_id for result in reranked] == [
        "recovery",
        "policy",
        "incident",
    ]
    assert reranked[0].cross_encoder_score == 303
    assert reranked[0].matched_terms == ("방법", "비밀번호", "재설정")


def test_reranker_is_input_order_independent_and_has_stable_tie_breaking() -> None:
    """재현 가능한 fixture 평가를 위해 입력 순서와 동점이 결과를 흔들면 안 된다."""
    candidates = (
        Candidate("zeta", "배포 승인", 0.1),
        Candidate("alpha", "배포 승인", 0.9),
    )

    forward = LexicalCrossEncoder().rerank("배포 승인", candidates)
    reversed_order = LexicalCrossEncoder().rerank("배포 승인", tuple(reversed(candidates)))

    assert [result.candidate.candidate_id for result in forward] == ["alpha", "zeta"]
    assert forward == reversed_order


def test_reranker_honors_top_k_after_global_sorting() -> None:
    """top_k는 후보를 자르기 전에 rerank 전체 순위에 적용되어야 한다."""
    candidates = (
        Candidate("weak", "비밀번호 정책", 0.99),
        Candidate("strong", "비밀번호 재설정 방법", 0.1),
    )

    reranked = LexicalCrossEncoder().rerank("비밀번호 재설정 방법", candidates, top_k=1)

    assert [result.candidate.candidate_id for result in reranked] == ["strong"]


def test_evaluate_ranking_calculates_precision_recall_mrr_and_ndcg() -> None:
    """관련 문서의 top-k 위치는 네 개의 명시적 품질 지표에 반영되어야 한다."""
    metrics = evaluate_ranking(["noise", "relevant", "other"], {"relevant"}, k=2)

    assert metrics == RankingMetrics(
        precision_at_k=0.5,
        recall_at_k=1.0,
        reciprocal_rank=0.5,
        ndcg_at_k=pytest.approx(1.0 / math.log2(3)),
    )


def test_mean_metrics_prove_rerank_improves_fixed_fixture_at_one() -> None:
    """고정 후보에서 before/after 품질 회귀를 외부 서비스 없이 측정한다."""
    baseline = mean_ranking_metrics(
        [
            evaluate_ranking(["noise", "relevant"], {"relevant"}, k=1),
            evaluate_ranking(["relevant"], {"relevant"}, k=1),
        ]
    )
    reranked = mean_ranking_metrics(
        [
            evaluate_ranking(["relevant", "noise"], {"relevant"}, k=1),
            evaluate_ranking(["relevant"], {"relevant"}, k=1),
        ]
    )

    assert baseline.mean_precision_at_k == pytest.approx(0.5)
    assert baseline.mean_recall_at_k == pytest.approx(0.5)
    assert baseline.mean_reciprocal_rank == pytest.approx(0.75)
    assert baseline.mean_ndcg_at_k == pytest.approx(0.5)
    assert reranked.mean_precision_at_k == pytest.approx(1.0)
    assert reranked.mean_recall_at_k == pytest.approx(1.0)
    assert reranked.mean_reciprocal_rank == pytest.approx(1.0)
    assert reranked.mean_ndcg_at_k == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: Candidate("", "text", 0.1), "candidate_id"),
        (lambda: Candidate("id", "", 0.1), "text"),
        (lambda: Candidate("id", "text", math.nan), "retriever_score"),
        (
            lambda: LexicalCrossEncoder().rerank(
                "query", (Candidate("same", "query", 0.1), Candidate("same", "query", 0.2))
            ),
            "unique",
        ),
        (lambda: LexicalCrossEncoder().rerank("query", (), top_k=1), "must not be empty"),
        (
            lambda: evaluate_ranking(["same", "same"], {"same"}, k=1),
            "duplicates",
        ),
        (lambda: evaluate_ranking(["id"], set(), k=1), "must not be empty"),
        (lambda: evaluate_ranking(["id"], {"id"}, k=0), "positive"),
    ],
)
def test_invalid_contracts_fail_closed(factory: object, message: str) -> None:
    """모호한 후보·평가 입력은 조용히 순위에 반영하면 안 된다."""
    with pytest.raises(RerankerConfigurationError, match=message):
        factory()
