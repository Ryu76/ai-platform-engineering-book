"""외부 모델 없이 Cross-Encoder 순서와 품질 측정을 학습하는 결정론적 도구.

`LexicalCrossEncoder`는 실제 신경망 Cross-Encoder가 아니다. 질의와 후보를 한 쌍으로
입력해 후보마다 점수를 다시 계산하는 경계를, 네트워크·모델 다운로드 없이 재현한다.
실무에서는 검증된 모델 어댑터로 교체하고 같은 평가 fixture를 회귀 검사에 사용한다.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from math import isfinite, log2
from time import perf_counter_ns


class RerankerConfigurationError(ValueError):
    """후보, 순위 또는 평가 계약이 유효하지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class Candidate:
    """1차 검색기가 반환한 불변 후보다."""

    candidate_id: str
    text: str
    retriever_score: float

    def __post_init__(self) -> None:
        _require_identifier(self.candidate_id, name="candidate_id")
        if not isinstance(self.text, str) or not self.text.strip():
            raise RerankerConfigurationError("text must be a non-empty string")
        _require_finite_number(self.retriever_score, name="retriever_score")


@dataclass(frozen=True, slots=True)
class RerankedCandidate:
    """질의-후보 쌍에서 다시 계산한 점수와 일치 용어를 보존한다."""

    candidate: Candidate
    cross_encoder_score: int
    matched_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RankingMetrics:
    """단일 질의의 binary relevance 기반 top-k 지표다."""

    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float


@dataclass(frozen=True, slots=True)
class RankingSummary:
    """여러 질의의 산술 평균 ranking metrics다."""

    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_reciprocal_rank: float
    mean_ndcg_at_k: float


@dataclass(frozen=True, slots=True)
class RerankMeasurement:
    """한 번의 local rerank에서 비교한 후보 수와 경과 시간을 보존한다.

    ``pair_evaluations``는 이 교육용 scorer가 실제로 질의와 함께 비교한 후보 쌍의
    수다. 모델 비용의 대용 지표일 뿐, 운영 모델의 금액이나 처리량을 뜻하지 않는다.
    """

    ranked: tuple[RerankedCandidate, ...]
    candidate_count: int
    pair_evaluations: int
    elapsed_ns: int


class LexicalCrossEncoder:
    """질의와 각 후보를 함께 비교하는 결정론적 교육용 reranker다.

    후보의 원래 retriever score는 점수 계산에 쓰지 않는다. 같은 후보 집합이라면
    입력 순서가 달라도 결과가 같아야 하며, 동점은 candidate ID로 안정적으로 정렬한다.
    """

    def rerank(
        self, query: str, candidates: Sequence[Candidate], *, top_k: int | None = None
    ) -> tuple[RerankedCandidate, ...]:
        """각 질의-후보 쌍의 용어 coverage와 반복 일치로 순위를 새로 계산한다."""
        query_terms = _tokenize_query(query)
        prepared_candidates = _prepare_candidates(candidates)
        if top_k is not None:
            _require_top_k(top_k)

        unique_query_terms = tuple(sorted(set(query_terms)))
        reranked = [
            RerankedCandidate(
                candidate=candidate,
                cross_encoder_score=_score_pair(unique_query_terms, candidate.text),
                matched_terms=tuple(
                    term
                    for term in unique_query_terms
                    if _term_match_count(term, candidate.text) > 0
                ),
            )
            for candidate in prepared_candidates
        ]
        reranked.sort(
            key=lambda result: (-result.cross_encoder_score, result.candidate.candidate_id)
        )
        return tuple(reranked if top_k is None else reranked[:top_k])


def measure_rerank(
    query: str,
    candidates: Sequence[Candidate],
    *,
    top_k: int | None = None,
    clock_ns: Callable[[], int] = perf_counter_ns,
) -> RerankMeasurement:
    """rerank 범위만 monotonic local clock으로 측정하고 후보 비교 수를 함께 반환한다.

    후보 검증, clock 호출, 출력은 타이밍 범위 밖에 둔다. ``top_k``는 전체 후보를
    pair scoring한 뒤 출력만 제한하므로 ``pair_evaluations``를 줄이지 않는다.
    테스트에서는 결정론적 clock을 주입해 경과 시간 계약을 재현할 수 있다.
    """
    prepared_candidates = _prepare_candidates(candidates)
    if not callable(clock_ns):
        raise RerankerConfigurationError("clock_ns must be callable")

    started_ns = _require_clock_reading(clock_ns(), name="clock_ns start")
    ranked = LexicalCrossEncoder().rerank(query, prepared_candidates, top_k=top_k)
    finished_ns = _require_clock_reading(clock_ns(), name="clock_ns end")
    if finished_ns < started_ns:
        raise RerankerConfigurationError("clock_ns must not move backwards")
    return RerankMeasurement(
        ranked=ranked,
        candidate_count=len(prepared_candidates),
        pair_evaluations=len(prepared_candidates),
        elapsed_ns=finished_ns - started_ns,
    )


def evaluate_ranking(
    ranked_ids: Sequence[str], relevant_ids: Collection[str], *, k: int
) -> RankingMetrics:
    """ID 순위를 사람의 binary relevance judgment와 비교해 네 지표를 계산한다.

    후보 수가 k보다 적어도 precision@k의 분모는 k로 유지한다. 이는 작은 후보
    집합이 precision을 부당하게 높이지 않게 한다. reciprocal rank는 전체 순위의
    첫 관련 문서 위치를 보고, nDCG@k는 관련 문서를 상위에 둘수록 높게 평가한다.
    """
    _require_top_k(k)
    prepared_ranked = _prepare_ranked_ids(ranked_ids)
    prepared_relevant = _prepare_relevant_ids(relevant_ids)

    top_k = prepared_ranked[:k]
    relevant_count = sum(identifier in prepared_relevant for identifier in top_k)
    first_relevant_rank = next(
        (
            position
            for position, identifier in enumerate(prepared_ranked, start=1)
            if identifier in prepared_relevant
        ),
        None,
    )
    dcg = sum(
        1.0 / log2(position + 1)
        for position, identifier in enumerate(top_k, start=1)
        if identifier in prepared_relevant
    )
    ideal_count = min(k, len(prepared_relevant))
    ideal_dcg = sum(1.0 / log2(position + 1) for position in range(1, ideal_count + 1))
    return RankingMetrics(
        precision_at_k=relevant_count / k,
        recall_at_k=relevant_count / len(prepared_relevant),
        reciprocal_rank=0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank,
        ndcg_at_k=dcg / ideal_dcg,
    )


def mean_ranking_metrics(metrics: Sequence[RankingMetrics]) -> RankingSummary:
    """질의별 ranking metrics를 동일 가중치 평균으로 요약한다."""
    if not metrics:
        raise RerankerConfigurationError("metrics must not be empty")
    if not all(isinstance(metric, RankingMetrics) for metric in metrics):
        raise RerankerConfigurationError("metrics must contain RankingMetrics instances")

    count = len(metrics)
    return RankingSummary(
        mean_precision_at_k=sum(metric.precision_at_k for metric in metrics) / count,
        mean_recall_at_k=sum(metric.recall_at_k for metric in metrics) / count,
        mean_reciprocal_rank=sum(metric.reciprocal_rank for metric in metrics) / count,
        mean_ndcg_at_k=sum(metric.ndcg_at_k for metric in metrics) / count,
    )


def _score_pair(query_terms: tuple[str, ...], candidate_text: str) -> int:
    """coverage를 우선하고 반복 일치를 보조 신호로 쓰는 재현 가능한 pair 점수다."""
    match_counts = [_term_match_count(term, candidate_text) for term in query_terms]
    coverage = sum(count > 0 for count in match_counts)
    occurrences = sum(match_counts)
    return coverage * 100 + occurrences


def _term_match_count(query_term: str, candidate_text: str) -> int:
    """한글 조사·활용형을 위해 한글 질의어에는 안전한 접두 일치를 허용한다."""
    candidate_terms = _tokenize(candidate_text)
    if re.fullmatch(r"[가-힣]+", query_term):
        return sum(term.startswith(query_term) for term in candidate_terms)
    return sum(term == query_term for term in candidate_terms)


def _tokenize_query(query: str) -> tuple[str, ...]:
    if not isinstance(query, str) or not query.strip():
        raise RerankerConfigurationError("query must be a non-empty string")
    terms = _tokenize(query)
    if not terms:
        raise RerankerConfigurationError("query must contain searchable terms")
    return terms


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(term.casefold() for term in re.findall(r"[0-9A-Za-z가-힣_]+", text))


def _prepare_candidates(candidates: Sequence[Candidate]) -> tuple[Candidate, ...]:
    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
        raise RerankerConfigurationError("candidates must be a sequence of Candidate instances")
    prepared = tuple(candidates)
    if not prepared:
        raise RerankerConfigurationError("candidates must not be empty")
    if not all(isinstance(candidate, Candidate) for candidate in prepared):
        raise RerankerConfigurationError("candidates must contain Candidate instances")
    identifiers = [candidate.candidate_id for candidate in prepared]
    if len(set(identifiers)) != len(identifiers):
        raise RerankerConfigurationError("candidate_id values must be unique")
    return prepared


def _prepare_ranked_ids(ranked_ids: Sequence[str]) -> tuple[str, ...]:
    if isinstance(ranked_ids, (str, bytes)) or not isinstance(ranked_ids, Sequence):
        raise RerankerConfigurationError("ranked_ids must be a sequence of strings")
    prepared = tuple(ranked_ids)
    for identifier in prepared:
        _require_identifier(identifier, name="ranked_ids")
    if len(set(prepared)) != len(prepared):
        raise RerankerConfigurationError("ranked_ids must not contain duplicates")
    return prepared


def _prepare_relevant_ids(relevant_ids: Collection[str]) -> frozenset[str]:
    if isinstance(relevant_ids, (str, bytes)) or not isinstance(relevant_ids, Collection):
        raise RerankerConfigurationError("relevant_ids must be a collection of strings")
    prepared = frozenset(relevant_ids)
    if not prepared:
        raise RerankerConfigurationError("relevant_ids must not be empty")
    for identifier in prepared:
        _require_identifier(identifier, name="relevant_ids")
    return prepared


def _require_identifier(identifier: str, *, name: str) -> None:
    if not isinstance(identifier, str) or not identifier.strip():
        raise RerankerConfigurationError(f"{name} must be a non-empty string")


def _require_top_k(k: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise RerankerConfigurationError("k must be a positive integer")


def _require_finite_number(value: float, *, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise RerankerConfigurationError(f"{name} must be a finite number")


def _require_clock_reading(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RerankerConfigurationError(f"{name} must be a non-negative integer")
    return value
