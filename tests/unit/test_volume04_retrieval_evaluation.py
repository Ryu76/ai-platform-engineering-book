"""Volume 04의 결정적 검색 품질 평가 계약 테스트."""
from __future__ import annotations

import math
from collections.abc import Callable

import pytest

from ai_platform.embeddings import (
    DeterministicEmbeddingModel,
    InMemoryVectorStore,
    RetrievalEvaluationError,
    RetrievalMetrics,
    RetrievalSummary,
    VectorPoint,
    evaluate_ranking,
    mean_retrieval_metrics,
    meets_score_threshold,
)


def test_evaluate_ranking_calculates_top_k_metrics() -> None:
    """top-k 관련 문서 수와 첫 정답 순위로 품질 지표를 계산해야 한다."""
    metrics = evaluate_ranking(["first", "irrelevant", "second"], {"first", "second"}, k=2)

    assert metrics.precision_at_k == pytest.approx(0.5)
    assert metrics.recall_at_k == pytest.approx(0.5)
    assert metrics.reciprocal_rank == pytest.approx(1.0)
    assert metrics.hit_at_k is True


def test_evaluate_ranking_scores_empty_top_k_result_as_zero() -> None:
    """관련 문서가 k 밖에 있으면 top-k precision, recall, hit은 0이어야 한다."""
    metrics = evaluate_ranking(["irrelevant", "relevant"], {"relevant"}, k=1)

    assert metrics == RetrievalMetrics(
        precision_at_k=0.0,
        recall_at_k=0.0,
        reciprocal_rank=0.5,
        hit_at_k=False,
    )


def test_mean_retrieval_metrics_reports_mean_and_hit_rate() -> None:
    """여러 질의의 품질은 질의별 지표의 평균과 hit rate로 요약해야 한다."""
    summary = mean_retrieval_metrics(
        [
            evaluate_ranking(["relevant"], {"relevant"}, k=1),
            evaluate_ranking([], {"relevant"}, k=1),
        ]
    )

    assert summary.mean_precision_at_k == pytest.approx(0.5)
    assert summary.mean_recall_at_k == pytest.approx(0.5)
    assert summary.mean_reciprocal_rank == pytest.approx(0.5)
    assert summary.hit_rate_at_k == pytest.approx(0.5)


@pytest.mark.parametrize("metrics", [[], (), "not-a-metric-batch", b"not-a-metric-batch", None])
def test_mean_retrieval_metrics_rejects_empty_or_non_sequence_inputs(metrics: object) -> None:
    """평균은 비어 있거나 sequence가 아닌 입력을 조용히 집계하면 안 된다."""
    with pytest.raises(RetrievalEvaluationError, match="non-empty sequence"):
        mean_retrieval_metrics(metrics)  # type: ignore[arg-type]


def test_mean_retrieval_metrics_rejects_one_shot_generator() -> None:
    """일회성 iterator는 길이 검증과 재현 가능한 집계를 우회하면 안 된다."""
    metrics = (evaluate_ranking(["relevant"], {"relevant"}, k=1) for _ in range(1))

    with pytest.raises(RetrievalEvaluationError, match="non-empty sequence"):
        mean_retrieval_metrics(metrics)  # type: ignore[arg-type]


def test_local_search_results_can_be_evaluated_by_stable_point_id() -> None:
    """로컬 mock 검색 결과를 정답 ID와 비교해 end-to-end 품질을 확인한다."""
    model = DeterministicEmbeddingModel(dimensions=256)
    store = InMemoryVectorStore()
    store.create_collection("docs", vector_size=256)
    store.upsert(
        "docs",
        [
            VectorPoint(
                "retry", model.embed_one("Python API 오류 처리와 재시도"), {"topic": "api"}
            ),
            VectorPoint(
                "network", model.embed_one("Docker 컨테이너 포트 네트워크"), {"topic": "infra"}
            ),
        ],
    )

    results = store.search("docs", model.embed_one("Python API 오류 처리 방법"), limit=2)
    metrics = evaluate_ranking([result.id for result in results], {"retry"}, k=1)

    assert metrics == RetrievalMetrics(1.0, 1.0, 1.0, True)


@pytest.mark.parametrize(
    ("score", "minimum_score", "expected"),
    [(0.5, 0.5, True), (0.499, 0.5, False), (-0.5, -0.75, True)],
)
def test_score_threshold_is_an_explicit_no_answer_gate(
    score: float, minimum_score: float, expected: bool
) -> None:
    """최상위 점수의 경계값은 결정적으로 no-answer 여부를 나눠야 한다."""
    assert meets_score_threshold(score, minimum_score=minimum_score) is expected


@pytest.mark.parametrize(
    ("ranked_ids", "relevant_ids", "k", "message"),
    [
        (["same", "same"], {"same"}, 1, "duplicates"),
        (["document"], set(), 1, "must not be empty"),
        (["document"], {"document"}, 0, "positive"),
    ],
)
def test_evaluation_rejects_ambiguous_or_invalid_inputs(
    ranked_ids: list[str], relevant_ids: set[str], k: int, message: str
) -> None:
    """중복 순위, 정답 없는 평가, 잘못된 k는 조용히 측정하면 안 된다."""
    with pytest.raises(RetrievalEvaluationError, match=message):
        evaluate_ranking(ranked_ids, relevant_ids, k=k)


def test_threshold_rejects_non_finite_or_out_of_range_values() -> None:
    """NaN, infinity, cosine 범위 밖 임계값은 명시적으로 실패해야 한다."""
    with pytest.raises(RetrievalEvaluationError, match="finite"):
        meets_score_threshold(math.nan, minimum_score=0.5)
    with pytest.raises(RetrievalEvaluationError, match="between"):
        meets_score_threshold(0.5, minimum_score=1.1)


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: RetrievalMetrics(math.nan, 0.0, 0.0, False),
            "precision_at_k must be a finite number",
        ),
        (
            lambda: RetrievalMetrics(1.1, 0.0, 0.0, False),
            "precision_at_k must be between",
        ),
        (
            lambda: RetrievalMetrics(0.0, 0.0, 0.0, 1),
            "hit_at_k must be a bool",
        ),
        (
            lambda: RetrievalSummary(0.0, 0.0, 0.0, math.inf),
            "hit_rate_at_k must be a finite number",
        ),
    ],
)
def test_public_metric_records_reject_invalid_values(
    factory: Callable[[], object], message: str
) -> None:
    """수동 생성한 public metric record도 집계 전에 유효해야 한다."""
    with pytest.raises(RetrievalEvaluationError, match=message):
        factory()
