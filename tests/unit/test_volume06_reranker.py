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
    measure_rerank,
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


def test_measure_rerank_reports_all_pair_evaluations_and_injected_elapsed_time() -> None:
    """top-k 출력 제한은 비교 비용을 줄이지 않으며 측정 범위는 재현 가능해야 한다."""
    readings = iter((100, 145))
    candidates = (
        Candidate("weak", "비밀번호 정책", 0.99),
        Candidate("strong", "비밀번호 재설정 방법", 0.1),
    )

    measurement = measure_rerank(
        "비밀번호 재설정 방법", candidates, top_k=1, clock_ns=lambda: next(readings)
    )

    assert [result.candidate.candidate_id for result in measurement.ranked] == ["strong"]
    assert measurement.candidate_count == 2
    assert measurement.pair_evaluations == 2
    assert measurement.elapsed_ns == 45


def test_candidate_count_bounds_recall_and_top_k_does_not_reduce_pair_work() -> None:
    """관련 후보가 rerank 입력 밖이면 pair scorer는 recall을 회복할 수 없다."""
    candidates = (
        Candidate("policy", "비밀번호 정책은 주기적으로 변경합니다.", 0.99),
        Candidate("recovery", "비밀번호 재설정 방법은 계정 설정에서 확인합니다.", 0.71),
        Candidate("incident", "장애 보고 절차입니다.", 0.61),
    )

    one_candidate = measure_rerank("비밀번호 재설정 방법", candidates[:1], top_k=1)
    two_candidates = measure_rerank("비밀번호 재설정 방법", candidates[:2], top_k=1)

    assert evaluate_ranking(
        [result.candidate.candidate_id for result in one_candidate.ranked], {"recovery"}, k=1
    ) == RankingMetrics(0.0, 0.0, 0.0, 0.0)
    assert evaluate_ranking(
        [result.candidate.candidate_id for result in two_candidates.ranked], {"recovery"}, k=1
    ) == RankingMetrics(1.0, 1.0, 1.0, 1.0)
    assert one_candidate.pair_evaluations == 1
    assert two_candidates.pair_evaluations == 2


@pytest.mark.parametrize(
    ("clock_ns", "message"),
    [
        (lambda: -1, "non-negative"),
        (lambda: "10", "non-negative"),
        (1, "callable"),
    ],
)
def test_measure_rerank_rejects_invalid_clock_contract(
    clock_ns: object, message: str
) -> None:
    """깨진 local clock은 그럴듯한 latency 수치로 변환하면 안 된다."""
    with pytest.raises(RerankerConfigurationError, match=message):
        measure_rerank(
            "query", (Candidate("id", "query", 0.1),), clock_ns=clock_ns  # type: ignore[arg-type]
        )


def test_measure_rerank_rejects_clock_that_moves_backwards() -> None:
    """monotonic elapsed time의 기본 계약을 fail-closed로 보장한다."""
    readings = iter((20, 19))

    with pytest.raises(RerankerConfigurationError, match="backwards"):
        measure_rerank(
            "query",
            (Candidate("id", "query", 0.1),),
            clock_ns=lambda: next(readings),
        )


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
