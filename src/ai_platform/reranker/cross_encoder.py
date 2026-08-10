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
from typing import Literal, Protocol


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
class RelevanceJudgment:
    """사람이 후보 하나에 부여한 0 이상의 ordinal relevance grade다.

    ``0``은 비관련, 큰 수는 더 강한 관련성을 뜻한다. grade는 점수가 아니라 사람이
    검토한 평가 label이므로 reranker의 ``cross_encoder_score``와 섞어 쓰지 않는다.
    """

    candidate_id: str
    relevance_grade: int

    def __post_init__(self) -> None:
        _require_identifier(self.candidate_id, name="candidate_id")
        _require_non_negative_integer(self.relevance_grade, name="relevance_grade")


@dataclass(frozen=True, slots=True)
class GradedRankingMetrics:
    """ordinal relevance judgment를 이용한 단일 질의의 top-k ranking metrics다."""

    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float


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


@dataclass(frozen=True, slots=True)
class RerankDecision:
    """threshold를 적용한 결과와 no-answer fallback 여부를 보존한다.

    ``ranked``는 관측과 디버깅을 위해 보존하지만, ``selected``가 ``None``이면 호출자는
    그 후보를 답변 근거로 사용하지 않고 fallback을 수행해야 한다.
    """

    ranked: tuple[RerankedCandidate, ...]
    selected: RerankedCandidate | None
    min_score: int
    top_score: int
    outcome: Literal["accepted", "no_answer"]
    fallback_reason: str | None


@dataclass(frozen=True, slots=True)
class ThresholdSweepMeasurement:
    """한 번의 pair scoring 결과에 여러 threshold 정책을 적용한 local 측정값이다.

    Threshold는 이미 계산된 최상위 score를 선택 또는 거부할 뿐 model pair work를 다시
    수행하지 않는다. 따라서 ``rerank_measurement.pair_evaluations``는 threshold 개수가
    아니라 reranker에 전달한 candidate 수를 나타낸다.
    """

    rerank_measurement: RerankMeasurement
    decisions: tuple[RerankDecision, ...]


class CrossEncoderModel(Protocol):
    """외부 또는 local Cross-Encoder 모델이 제공해야 하는 최소 경계다.

    ``pairs``의 출력 순서는 입력 순서와 같아야 한다. 어댑터는 호출마다 남은 timeout
    budget을 전달하므로, 실제 모델 client는 이 값을 모델 호출의 deadline으로 사용해야
    한다. 이 protocol은 모델 라이브러리를 이 교육 모듈의 의존성으로 만들지 않으면서도
    batch pair scoring 계약을 명시한다.
    """

    def predict(
        self, pairs: Sequence[tuple[str, str]], *, timeout_ns: int
    ) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class CrossEncoderModelAdapter:
    """실제 Cross-Encoder client를 candidate contract에 연결하는 얇은 adapter다.

    모델 로딩, 네트워크 전송, retry는 이 경계 밖의 client가 담당한다. 이 adapter는
    query와 candidate text를 순서 보존 pair로 만들고 timeout budget을 그대로 전달한다.
    """

    model_id: str
    model: CrossEncoderModel

    def __post_init__(self) -> None:
        _require_identifier(self.model_id, name="model_id")
        if not callable(getattr(self.model, "predict", None)):
            raise RerankerConfigurationError("model must provide a callable predict method")

    def score_pairs(
        self, query: str, candidates: Sequence[Candidate], *, timeout_ns: int
    ) -> Sequence[float]:
        """입력 순서 그대로 ``(query, candidate.text)`` pair를 모델에 전달한다."""
        _require_positive_integer(timeout_ns, name="timeout_ns")
        return self.model.predict(
            tuple((query, candidate.text) for candidate in candidates), timeout_ns=timeout_ns
        )


class CrossEncoderScorer(Protocol):
    """batch rerank 실행기가 의존하는 adapter 측 경계다."""

    def score_pairs(
        self, query: str, candidates: Sequence[Candidate], *, timeout_ns: int
    ) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class BatchRerankPolicy:
    """모든 batch가 공유하는 최대 크기와 전체 rerank deadline이다."""

    max_batch_size: int
    timeout_ns: int

    def __post_init__(self) -> None:
        _require_positive_integer(self.max_batch_size, name="max_batch_size")
        _require_positive_integer(self.timeout_ns, name="timeout_ns")


@dataclass(frozen=True, slots=True)
class AdapterRerankedCandidate:
    """adapter score 또는 명시적인 retriever fallback 출처를 가진 후보다."""

    candidate: Candidate
    cross_encoder_score: float | None
    rank_source: Literal["cross_encoder", "retriever_fallback"]


@dataclass(frozen=True, slots=True)
class AdapterRerankResult:
    """batched adapter rerank의 순위, 작업량, timeout/error 관측값이다.

    timeout 또는 adapter error 뒤에는 일부 batch score를 사용하지 않는다. 기본
    ``no_answer`` 정책은 빈 ranked 결과를 반환한다. 명시적으로 ``retriever`` fallback을
    선택한 경우에만 원래 retriever score 순위가 반환되고 그 출처가 표시된다.
    """

    ranked: tuple[AdapterRerankedCandidate, ...]
    candidate_count: int
    batch_count: int
    pair_evaluations: int
    elapsed_ns: int
    outcome: Literal["reranked", "no_answer", "retriever_fallback"]
    fallback_reason: Literal["adapter_timeout", "adapter_error"] | None


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


def rerank_with_threshold(
    query: str,
    candidates: Sequence[Candidate],
    *,
    min_score: int,
    top_k: int | None = None,
) -> RerankDecision:
    """최상위 pair score가 threshold 미만이면 fail-closed no-answer를 반환한다.

    threshold는 모든 후보를 score·정렬한 뒤 최상위 결과에 적용한다. 거부된 후보는
    ``selected``로 승격되지 않으며, 호출자는 ``fallback_reason``을 구조화된 local
    관측값으로 기록할 수 있다. 이 함수는 네트워크나 생성 모델 fallback을 호출하지
    않는다.
    """
    _require_non_negative_integer(min_score, name="min_score")
    ranked = LexicalCrossEncoder().rerank(query, candidates, top_k=top_k)
    return _threshold_decision(ranked, min_score=min_score)


def measure_threshold_sweep(
    query: str,
    candidates: Sequence[Candidate],
    *,
    min_scores: Sequence[int],
    top_k: int | None = None,
    clock_ns: Callable[[], int] = perf_counter_ns,
) -> ThresholdSweepMeasurement:
    """하나의 local rerank로 여러 threshold의 acceptance/no-answer를 비교한다.

    같은 candidate set과 score에서 policy만 바꾸는 offline sweep이다. threshold마다
    reranker를 다시 실행하면 pair work와 local elapsed가 정책 수에 비례해 부풀어
    비교를 왜곡하므로, 이 함수는 pair score를 한 번만 계산하고 그 결과에만 threshold를
    적용한다. 실제 model/provider latency와 비용을 추정하는 함수는 아니다.
    """
    prepared_min_scores = _prepare_min_scores(min_scores)
    measurement = measure_rerank(query, candidates, top_k=top_k, clock_ns=clock_ns)
    return ThresholdSweepMeasurement(
        rerank_measurement=measurement,
        decisions=tuple(
            _threshold_decision(measurement.ranked, min_score=min_score)
            for min_score in prepared_min_scores
        ),
    )


def rerank_with_adapter(
    query: str,
    candidates: Sequence[Candidate],
    adapter: CrossEncoderScorer,
    policy: BatchRerankPolicy,
    *,
    fallback: Literal["no_answer", "retriever"] = "no_answer",
    clock_ns: Callable[[], int] = perf_counter_ns,
) -> AdapterRerankResult:
    """batch Cross-Encoder adapter를 전체 deadline 아래 실행한다.

    각 model call에는 전체 deadline에서 이미 사용한 시간을 뺀 budget을 넘긴다. timeout,
    adapter exception, 또는 deadline 초과가 발생하면 이전 batch의 partial score를 폐기한다.
    기본값은 후보를 선택하지 않는 ``no_answer``다. ``fallback="retriever"``는 호출자가
    명시적으로 허용한 경우에만 retriever score 순위를 반환하며 출처를 표시한다.
    """
    _tokenize_query(query)
    prepared_candidates = _prepare_candidates(candidates)
    _require_scorer(adapter)
    if not isinstance(policy, BatchRerankPolicy):
        raise RerankerConfigurationError("policy must be a BatchRerankPolicy")
    _require_fallback(fallback)
    if not callable(clock_ns):
        raise RerankerConfigurationError("clock_ns must be callable")

    started_ns = _require_clock_reading(clock_ns(), name="clock_ns start")
    deadline_ns = started_ns + policy.timeout_ns
    scores: list[float] = []
    batch_count = 0
    pair_evaluations = 0
    for offset in range(0, len(prepared_candidates), policy.max_batch_size):
        current_ns = _require_clock_reading(clock_ns(), name="clock_ns before batch")
        if current_ns < started_ns:
            raise RerankerConfigurationError("clock_ns must not move backwards")
        if current_ns >= deadline_ns:
            return _adapter_fallback_result(
                prepared_candidates,
                fallback=fallback,
                reason="adapter_timeout",
                batch_count=batch_count,
                pair_evaluations=pair_evaluations,
                elapsed_ns=current_ns - started_ns,
            )

        batch = prepared_candidates[offset : offset + policy.max_batch_size]
        batch_count += 1
        pair_evaluations += len(batch)
        try:
            batch_scores = _prepare_adapter_scores(
                adapter.score_pairs(query, batch, timeout_ns=deadline_ns - current_ns),
                expected_count=len(batch),
            )
        except TimeoutError:
            return _adapter_fallback_result(
                prepared_candidates,
                fallback=fallback,
                reason="adapter_timeout",
                batch_count=batch_count,
                pair_evaluations=pair_evaluations,
                elapsed_ns=_elapsed_since(started_ns, clock_ns),
            )
        except Exception:
            return _adapter_fallback_result(
                prepared_candidates,
                fallback=fallback,
                reason="adapter_error",
                batch_count=batch_count,
                pair_evaluations=pair_evaluations,
                elapsed_ns=_elapsed_since(started_ns, clock_ns),
            )

        finished_batch_ns = _require_clock_reading(clock_ns(), name="clock_ns after batch")
        if finished_batch_ns < started_ns:
            raise RerankerConfigurationError("clock_ns must not move backwards")
        if finished_batch_ns > deadline_ns:
            return _adapter_fallback_result(
                prepared_candidates,
                fallback=fallback,
                reason="adapter_timeout",
                batch_count=batch_count,
                pair_evaluations=pair_evaluations,
                elapsed_ns=finished_batch_ns - started_ns,
            )
        scores.extend(batch_scores)

    reranked = tuple(
        sorted(
            (
                AdapterRerankedCandidate(candidate, score, "cross_encoder")
                for candidate, score in zip(prepared_candidates, scores, strict=True)
            ),
            key=lambda result: (
                -result.cross_encoder_score
                if result.cross_encoder_score is not None
                else float("inf"),
                result.candidate.candidate_id,
            ),
        )
    )
    return AdapterRerankResult(
        ranked=reranked,
        candidate_count=len(prepared_candidates),
        batch_count=batch_count,
        pair_evaluations=pair_evaluations,
        elapsed_ns=_elapsed_since(started_ns, clock_ns),
        outcome="reranked",
        fallback_reason=None,
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


def evaluate_graded_ranking(
    ranked_ids: Sequence[str], judgments: Sequence[RelevanceJudgment], *, k: int
) -> GradedRankingMetrics:
    """ordinal judgments로 binary metrics와 graded nDCG@k를 fail-closed 계산한다.

    Precision, recall, MRR에서 grade가 2 이상인 문서는 직접 관련 문서다. nDCG는
    ``2**grade - 1`` gain을 사용하므로 더 강한 관련 문서를 상위에 놓을수록 높다.
    평가되는 모든 rank ID에는 명시적 judgment가 있어야 한다. 누락 label을 0으로
    추측하면 품질 저하를 숨길 수 있으므로 거부한다.
    """
    _require_top_k(k)
    prepared_ranked = _prepare_ranked_ids(ranked_ids)
    prepared_judgments = _prepare_relevance_judgments(judgments)
    grade_by_id = {
        judgment.candidate_id: judgment.relevance_grade for judgment in prepared_judgments
    }
    unlabeled_ids = set(prepared_ranked).difference(grade_by_id)
    if unlabeled_ids:
        raise RerankerConfigurationError("ranked_ids must all have a relevance judgment")

    top_ranked = prepared_ranked[:k]
    relevant_ids = {identifier for identifier, grade in grade_by_id.items() if grade >= 2}
    relevant_count = sum(identifier in relevant_ids for identifier in top_ranked)
    first_relevant_rank = next(
        (
            position
            for position, identifier in enumerate(prepared_ranked, start=1)
            if identifier in relevant_ids
        ),
        None,
    )
    dcg = sum(
        (2**grade_by_id[identifier] - 1) / log2(position + 1)
        for position, identifier in enumerate(top_ranked, start=1)
    )
    ideal_grades = sorted(grade_by_id.values(), reverse=True)[:k]
    ideal_dcg = sum(
        (2**grade - 1) / log2(position + 1)
        for position, grade in enumerate(ideal_grades, start=1)
    )
    return GradedRankingMetrics(
        precision_at_k=relevant_count / k,
        recall_at_k=0.0 if not relevant_ids else relevant_count / len(relevant_ids),
        reciprocal_rank=0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank,
        ndcg_at_k=0.0 if ideal_dcg == 0.0 else dcg / ideal_dcg,
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


def _threshold_decision(
    ranked: tuple[RerankedCandidate, ...], *, min_score: int
) -> RerankDecision:
    """이미 계산된 ranking의 최상위 후보를 threshold policy로 선택 또는 거부한다."""
    top_result = ranked[0]
    if top_result.cross_encoder_score >= min_score:
        return RerankDecision(
            ranked=ranked,
            selected=top_result,
            min_score=min_score,
            top_score=top_result.cross_encoder_score,
            outcome="accepted",
            fallback_reason=None,
        )
    return RerankDecision(
        ranked=ranked,
        selected=None,
        min_score=min_score,
        top_score=top_result.cross_encoder_score,
        outcome="no_answer",
        fallback_reason="top_score_below_threshold",
    )


def _prepare_min_scores(min_scores: Sequence[int]) -> tuple[int, ...]:
    """sweep policy가 비어 있거나 중복되지 않도록 명시적으로 검증한다."""
    if isinstance(min_scores, (str, bytes)) or not isinstance(min_scores, Sequence):
        raise RerankerConfigurationError("min_scores must be a sequence of non-negative integers")
    prepared = tuple(min_scores)
    if not prepared:
        raise RerankerConfigurationError("min_scores must not be empty")
    for min_score in prepared:
        _require_non_negative_integer(min_score, name="min_scores")
    if len(set(prepared)) != len(prepared):
        raise RerankerConfigurationError("min_scores must not contain duplicates")
    return prepared


def _adapter_fallback_result(
    candidates: tuple[Candidate, ...],
    *,
    fallback: Literal["no_answer", "retriever"],
    reason: Literal["adapter_timeout", "adapter_error"],
    batch_count: int,
    pair_evaluations: int,
    elapsed_ns: int,
) -> AdapterRerankResult:
    """partial Cross-Encoder score를 버리고 명시된 fallback 결과만 만든다."""
    if fallback == "no_answer":
        return AdapterRerankResult(
            ranked=(),
            candidate_count=len(candidates),
            batch_count=batch_count,
            pair_evaluations=pair_evaluations,
            elapsed_ns=elapsed_ns,
            outcome="no_answer",
            fallback_reason=reason,
        )
    return AdapterRerankResult(
        ranked=tuple(
            AdapterRerankedCandidate(candidate, None, "retriever_fallback")
            for candidate in sorted(
                candidates,
                key=lambda candidate: (
                    -candidate.retriever_score,
                    candidate.candidate_id,
                ),
            )
        ),
        candidate_count=len(candidates),
        batch_count=batch_count,
        pair_evaluations=pair_evaluations,
        elapsed_ns=elapsed_ns,
        outcome="retriever_fallback",
        fallback_reason=reason,
    )


def _prepare_adapter_scores(scores: Sequence[float], *, expected_count: int) -> tuple[float, ...]:
    """adapter output의 cardinality와 수치 계약을 fail-closed로 검증한다."""
    if isinstance(scores, (str, bytes)) or not isinstance(scores, Sequence):
        raise RerankerConfigurationError("adapter scores must be a sequence of finite numbers")
    prepared = tuple(scores)
    if len(prepared) != expected_count:
        raise RerankerConfigurationError("adapter scores must match the submitted batch size")
    for score in prepared:
        _require_finite_number(score, name="adapter score")
    return tuple(float(score) for score in prepared)


def _require_scorer(adapter: CrossEncoderScorer) -> None:
    if not callable(getattr(adapter, "score_pairs", None)):
        raise RerankerConfigurationError("adapter must provide a callable score_pairs method")


def _require_fallback(fallback: str) -> None:
    if fallback not in {"no_answer", "retriever"}:
        raise RerankerConfigurationError("fallback must be 'no_answer' or 'retriever'")


def _elapsed_since(started_ns: int, clock_ns: Callable[[], int]) -> int:
    """deadline 종료/오류 시에도 local monotonic elapsed를 검증해 계산한다."""
    current_ns = _require_clock_reading(clock_ns(), name="clock_ns elapsed")
    if current_ns < started_ns:
        raise RerankerConfigurationError("clock_ns must not move backwards")
    return current_ns - started_ns


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


def _prepare_relevance_judgments(
    judgments: Sequence[RelevanceJudgment],
) -> tuple[RelevanceJudgment, ...]:
    if isinstance(judgments, (str, bytes)) or not isinstance(judgments, Sequence):
        raise RerankerConfigurationError(
            "judgments must be a sequence of RelevanceJudgment instances"
        )
    prepared = tuple(judgments)
    if not prepared:
        raise RerankerConfigurationError("judgments must not be empty")
    if not all(isinstance(judgment, RelevanceJudgment) for judgment in prepared):
        raise RerankerConfigurationError("judgments must contain RelevanceJudgment instances")
    identifiers = [judgment.candidate_id for judgment in prepared]
    if len(set(identifiers)) != len(identifiers):
        raise RerankerConfigurationError("judgment candidate_id values must be unique")
    return prepared


def _require_identifier(identifier: str, *, name: str) -> None:
    if not isinstance(identifier, str) or not identifier.strip():
        raise RerankerConfigurationError(f"{name} must be a non-empty string")


def _require_top_k(k: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise RerankerConfigurationError("k must be a positive integer")


def _require_non_negative_integer(value: int, *, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RerankerConfigurationError(f"{name} must be a non-negative integer")


def _require_positive_integer(value: int, *, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RerankerConfigurationError(f"{name} must be a positive integer")


def _require_finite_number(value: float, *, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise RerankerConfigurationError(f"{name} must be a finite number")


def _require_clock_reading(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RerankerConfigurationError(f"{name} must be a non-negative integer")
    return value
