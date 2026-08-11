"""결정적 로컬 검색 결과의 품질을 측정하는 Volume 04 교육용 도구."""
from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from math import isfinite


class RetrievalEvaluationError(ValueError):
    """검색 순위 또는 평가 입력 계약이 유효하지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    """한 질의의 top-k 검색 품질 지표다.

    `precision_at_k`는 상위 k개 중 관련 결과의 비율, `recall_at_k`는 모든 관련
    문서 중 상위 k개에서 찾은 비율이다. `reciprocal_rank`는 첫 관련 결과의 순위의
    역수이며, `hit_at_k`는 상위 k개에 관련 결과가 하나라도 있는지를 뜻한다.
    """

    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    hit_at_k: bool

    def __post_init__(self) -> None:
        """집계 전에 지표가 유한한 단위 구간 값인지 확인한다."""
        _require_unit_interval_metric(self.precision_at_k, name="precision_at_k")
        _require_unit_interval_metric(self.recall_at_k, name="recall_at_k")
        _require_unit_interval_metric(self.reciprocal_rank, name="reciprocal_rank")
        if not isinstance(self.hit_at_k, bool):
            raise RetrievalEvaluationError("hit_at_k must be a bool")


@dataclass(frozen=True, slots=True)
class RetrievalSummary:
    """여러 질의의 평균 검색 품질과 hit rate를 담는 요약값이다."""

    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_reciprocal_rank: float
    hit_rate_at_k: float

    def __post_init__(self) -> None:
        """요약 지표가 유한한 단위 구간 값인지 확인한다."""
        _require_unit_interval_metric(self.mean_precision_at_k, name="mean_precision_at_k")
        _require_unit_interval_metric(self.mean_recall_at_k, name="mean_recall_at_k")
        _require_unit_interval_metric(
            self.mean_reciprocal_rank, name="mean_reciprocal_rank"
        )
        _require_unit_interval_metric(self.hit_rate_at_k, name="hit_rate_at_k")


def evaluate_ranking(
    ranked_ids: Sequence[str], relevant_ids: Collection[str], *, k: int
) -> RetrievalMetrics:
    """한 질의의 결정적 ID 순위를 precision, recall, MRR 구성 지표로 평가한다.

    검색 결과가 k개보다 적어도 precision의 분모는 k로 유지한다. 따라서 빈 결과는
    0점이고, 작은 후보 집합이 결과를 부당하게 높게 보이게 하지 않는다.
    """
    _require_positive_k(k)
    prepared_ranked = _prepare_ranked_ids(ranked_ids)
    prepared_relevant = _prepare_relevant_ids(relevant_ids)

    top_k = prepared_ranked[:k]
    relevant_in_top_k = [point_id for point_id in top_k if point_id in prepared_relevant]
    first_relevant_rank = next(
        (
            rank
            for rank, point_id in enumerate(prepared_ranked, start=1)
            if point_id in prepared_relevant
        ),
        None,
    )
    return RetrievalMetrics(
        precision_at_k=len(relevant_in_top_k) / k,
        recall_at_k=len(relevant_in_top_k) / len(prepared_relevant),
        reciprocal_rank=0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank,
        hit_at_k=bool(relevant_in_top_k),
    )


def mean_retrieval_metrics(metrics: Sequence[RetrievalMetrics]) -> RetrievalSummary:
    """여러 질의의 지표를 산술 평균과 hit rate로 요약한다."""
    if not metrics:
        raise RetrievalEvaluationError("metrics must not be empty")
    if not all(isinstance(metric, RetrievalMetrics) for metric in metrics):
        raise RetrievalEvaluationError("metrics must contain RetrievalMetrics instances")

    count = len(metrics)
    return RetrievalSummary(
        mean_precision_at_k=sum(metric.precision_at_k for metric in metrics) / count,
        mean_recall_at_k=sum(metric.recall_at_k for metric in metrics) / count,
        mean_reciprocal_rank=sum(metric.reciprocal_rank for metric in metrics) / count,
        hit_rate_at_k=sum(metric.hit_at_k for metric in metrics) / count,
    )


def meets_score_threshold(score: float, *, minimum_score: float) -> bool:
    """최상위 검색 점수가 명시한 no-answer 임계값을 넘는지 판단한다.

    이 함수는 답변의 사실성을 보장하지 않는다. 검색 점수만으로 답할 근거가 없다고
    판단하는 보수적인 로컬 gate이며, 운영 임계값은 대표 질의 평가 결과로 정해야 한다.
    """
    _require_finite_score(score, name="score")
    _require_finite_score(minimum_score, name="minimum_score")
    if not -1.0 <= minimum_score <= 1.0:
        raise RetrievalEvaluationError("minimum_score must be between -1.0 and 1.0")
    return score >= minimum_score


def _prepare_ranked_ids(ranked_ids: Sequence[str]) -> tuple[str, ...]:
    """순위가 있는 검색 ID 목록의 타입, 빈 값, 중복을 검증한다."""
    if isinstance(ranked_ids, (str, bytes)) or not isinstance(ranked_ids, Sequence):
        raise RetrievalEvaluationError("ranked_ids must be a sequence of strings")

    prepared = tuple(ranked_ids)
    for point_id in prepared:
        _require_id(point_id, name="ranked_ids")
    if len(set(prepared)) != len(prepared):
        raise RetrievalEvaluationError("ranked_ids must not contain duplicates")
    return prepared


def _prepare_relevant_ids(relevant_ids: Collection[str]) -> frozenset[str]:
    """정답으로 간주할 ID 집합을 검증해 membership lookup에 맞춘다."""
    if isinstance(relevant_ids, (str, bytes)) or not isinstance(relevant_ids, Collection):
        raise RetrievalEvaluationError("relevant_ids must be a collection of strings")
    for point_id in relevant_ids:
        _require_id(point_id, name="relevant_ids")

    prepared = frozenset(relevant_ids)
    if not prepared:
        raise RetrievalEvaluationError("relevant_ids must not be empty")
    return prepared


def _require_positive_k(k: int) -> None:
    """top-k 평가 범위를 검증한다."""
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise RetrievalEvaluationError("k must be a positive integer")


def _require_id(point_id: str, *, name: str) -> None:
    """검색 또는 정답 ID가 비어 있지 않은 문자열인지 검증한다."""
    if not isinstance(point_id, str) or not point_id.strip():
        raise RetrievalEvaluationError(f"{name} must contain non-empty strings")


def _require_finite_score(score: float, *, name: str) -> None:
    """점수와 임계값의 수치성과 유한성을 검증한다."""
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not isfinite(score):
        raise RetrievalEvaluationError(f"{name} must be a finite number")


def _require_unit_interval_metric(value: float, *, name: str) -> None:
    """공개 평가 지표가 bool이 아닌 유한한 0부터 1 사이 수인지 검증한다."""
    _require_finite_score(value, name=name)
    if not 0.0 <= value <= 1.0:
        raise RetrievalEvaluationError(f"{name} must be between 0.0 and 1.0")
