"""고정된 골든 데이터셋의 검색 순위를 결정론적으로 평가한다."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import log2


class RetrievalEvaluationError(ValueError):
    """검색 평가 입력이 골든 데이터셋 계약을 위반할 때 발생한다."""


@dataclass(frozen=True, slots=True)
class RetrievalCase:
    """하나의 질의와 정답 문서 식별자로 구성된 오프라인 평가 사례다."""

    case_id: str
    query: str
    relevant_document_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """재현 가능한 집계를 위해 사례 식별자와 정답을 검증한다."""
        if not self.case_id.strip():
            raise RetrievalEvaluationError("case_id must not be empty")
        if not self.query.strip():
            raise RetrievalEvaluationError("query must not be empty")
        if not self.relevant_document_ids:
            raise RetrievalEvaluationError(
                "a retrieval case must have at least one relevant document"
            )
        if any(not document_id.strip() for document_id in self.relevant_document_ids):
            raise RetrievalEvaluationError("relevant document ids must not be empty")
        if len(set(self.relevant_document_ids)) != len(self.relevant_document_ids):
            raise RetrievalEvaluationError("relevant document ids must be unique")


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    """동일한 절단 순위 ``k``에서 계산한 검색 품질 지표 묶음이다."""

    cases_evaluated: int
    recall_at_k: float
    precision_at_k: float
    hit_rate_at_k: float
    mean_reciprocal_rank: float
    ndcg_at_k: float


@dataclass(frozen=True, slots=True)
class RetrievalCaseMetrics:
    """한 골든 사례의 절단 순위별 검색 품질과 실패 위치를 담는다."""

    case_id: str
    relevant_document_ids_retrieved: tuple[str, ...]
    first_relevant_rank: int | None
    recall_at_k: float
    precision_at_k: float
    hit_at_k: bool
    reciprocal_rank: float
    ndcg_at_k: float


def evaluate_retrieval(
    cases: Sequence[RetrievalCase],
    ranked_document_ids_by_case: Mapping[str, Sequence[str]],
    *,
    k: int,
) -> RetrievalMetrics:
    """골든 정답과 미리 기록한 순위 결과에서 평균 검색 지표를 계산한다.

    ``precision_at_k``는 결과가 ``k``개보다 적어도 분모를 ``k``로 유지한다. 따라서
    빈 순위나 짧은 순위가 품질 점수를 부풀리지 않는다. 이 함수는 모델, 시계, 네트워크에
    의존하지 않으며 입력 순서만으로 같은 결과를 반환한다.
    """
    case_metrics = evaluate_retrieval_cases(cases, ranked_document_ids_by_case, k=k)
    count = len(case_metrics)
    return RetrievalMetrics(
        cases_evaluated=count,
        recall_at_k=sum(metric.recall_at_k for metric in case_metrics) / count,
        precision_at_k=sum(metric.precision_at_k for metric in case_metrics) / count,
        hit_rate_at_k=sum(metric.hit_at_k for metric in case_metrics) / count,
        mean_reciprocal_rank=sum(metric.reciprocal_rank for metric in case_metrics) / count,
        ndcg_at_k=sum(metric.ndcg_at_k for metric in case_metrics) / count,
    )


def evaluate_retrieval_cases(
    cases: Sequence[RetrievalCase],
    ranked_document_ids_by_case: Mapping[str, Sequence[str]],
    *,
    k: int,
) -> tuple[RetrievalCaseMetrics, ...]:
    """사례 입력 순서대로 검색 지표와 첫 실패 위치를 결정론적으로 계산한다."""
    _validate_k(k)
    _validate_cases(cases)
    case_ids = {case.case_id for case in cases}
    result_case_ids = set(ranked_document_ids_by_case)
    if case_ids != result_case_ids:
        missing = sorted(case_ids - result_case_ids)
        unexpected = sorted(result_case_ids - case_ids)
        raise RetrievalEvaluationError(
            f"ranked results must match case ids; missing={missing}, unexpected={unexpected}"
        )

    metrics: list[RetrievalCaseMetrics] = []
    for case in cases:
        ranked_document_ids = ranked_document_ids_by_case[case.case_id]
        _validate_ranked_document_ids(case.case_id, ranked_document_ids)
        top_k = tuple(ranked_document_ids[:k])
        relevant = set(case.relevant_document_ids)
        relevance = tuple(document_id in relevant for document_id in top_k)
        relevant_retrieved = tuple(
            document_id for document_id in top_k if document_id in relevant
        )
        first_relevant_rank = _first_relevant_rank(relevance)
        metrics.append(
            RetrievalCaseMetrics(
                case_id=case.case_id,
                relevant_document_ids_retrieved=relevant_retrieved,
                first_relevant_rank=first_relevant_rank,
                recall_at_k=len(relevant_retrieved) / len(relevant),
                precision_at_k=len(relevant_retrieved) / k,
                hit_at_k=bool(relevant_retrieved),
                reciprocal_rank=_reciprocal_rank(relevance),
                ndcg_at_k=_ndcg(relevance, relevant_count=len(relevant), k=k),
            )
        )
    return tuple(metrics)


def _validate_k(k: int) -> None:
    """절단 순위는 양의 정수여야 한다."""
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise RetrievalEvaluationError("k must be a positive integer")


def _validate_cases(cases: Sequence[RetrievalCase]) -> None:
    """빈 평가와 중복 사례 식별자를 차단한다."""
    if not cases:
        raise RetrievalEvaluationError("at least one retrieval case is required")
    case_ids = [case.case_id for case in cases]
    if len(set(case_ids)) != len(case_ids):
        raise RetrievalEvaluationError("case ids must be unique")


def _validate_ranked_document_ids(case_id: str, ranked_document_ids: Sequence[str]) -> None:
    """중복 순위와 빈 문서 식별자가 점수를 왜곡하지 않게 한다."""
    if isinstance(ranked_document_ids, str):
        raise RetrievalEvaluationError(
            f"ranked document ids for {case_id} must be a sequence of strings"
        )
    has_invalid_id = any(
        not isinstance(document_id, str) or not document_id.strip()
        for document_id in ranked_document_ids
    )
    if has_invalid_id:
        raise RetrievalEvaluationError(
            f"ranked document ids for {case_id} must be non-empty strings"
        )
    if len(set(ranked_document_ids)) != len(ranked_document_ids):
        raise RetrievalEvaluationError(f"ranked document ids for {case_id} must be unique")


def _reciprocal_rank(relevance: Sequence[bool]) -> float:
    """첫 정답 문서의 역순위를 반환하고 정답이 없으면 0을 반환한다."""
    first_relevant_rank = _first_relevant_rank(relevance)
    if first_relevant_rank is None:
        return 0.0
    return 1.0 / first_relevant_rank


def _first_relevant_rank(relevance: Sequence[bool]) -> int | None:
    """첫 정답의 1부터 시작하는 순위 또는 정답이 없을 때 ``None``을 반환한다."""
    for position, is_relevant in enumerate(relevance, start=1):
        if is_relevant:
            return position
    return None


def _ndcg(relevance: Sequence[bool], *, relevant_count: int, k: int) -> float:
    """이진 관련도 기준의 NDCG@k를 계산한다."""
    dcg = sum(
        1.0 / log2(position + 1)
        for position, is_relevant in enumerate(relevance, start=1)
        if is_relevant
    )
    ideal_hits = min(relevant_count, k)
    ideal_dcg = sum(1.0 / log2(position + 1) for position in range(1, ideal_hits + 1))
    return dcg / ideal_dcg
