"""고정 로컬 질의로 RAG 검색 품질을 재현 가능하게 평가한다.

이 모듈은 네트워크, 제공자 SDK, 생성 모델 또는 실시간 데이터를 사용하지 않는다.
호출자가 제공한 작은 고정 평가 세트와 ``SearchableIndex``만 사용해 검색 결과의
Recall@k, Hit rate, MRR을 계산한다. 문서 원문이나 생성 답변을 결과에 복사하지 않아
평가 산출물은 테스트 가능한 청크 식별자와 집계 지표만 포함한다.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ai_platform.rag.retrieval import RagConfigurationError, SearchableIndex, SearchHit


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    """하나 이상의 기대 근거 청크를 갖는 고정 로컬 검색 평가 질의다."""

    case_id: str
    query: str
    expected_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise RagConfigurationError("evaluation case_id must be a non-empty string")
        if not isinstance(self.query, str) or not self.query.strip():
            raise RagConfigurationError("evaluation query must be a non-empty string")
        if not isinstance(self.expected_chunk_ids, tuple) or not self.expected_chunk_ids:
            raise RagConfigurationError("evaluation expected_chunk_ids must be a non-empty tuple")
        if any(
            not isinstance(chunk_id, str) or not chunk_id.strip()
            for chunk_id in self.expected_chunk_ids
        ):
            raise RagConfigurationError(
                "evaluation expected_chunk_ids must contain non-empty strings"
            )
        if len(set(self.expected_chunk_ids)) != len(self.expected_chunk_ids):
            raise RagConfigurationError("evaluation expected_chunk_ids must not contain duplicates")


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationConfig:
    """재현 가능한 고정 질의 평가의 반환 근거 수와 최대 사례 수다."""

    top_k: int = 3
    max_cases: int = 100

    def __post_init__(self) -> None:
        for field_name, value, maximum in (
            ("top_k", self.top_k, 20),
            ("max_cases", self.max_cases, 1_000),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise RagConfigurationError(
                    f"evaluation {field_name} must be an integer between 1 and {maximum}"
                )


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationResult:
    """한 고정 질의의 검색 순위와 근거 회수 지표다."""

    case_id: str
    expected_chunk_ids: tuple[str, ...]
    retrieved_chunk_ids: tuple[str, ...]
    first_relevant_rank: int | None
    recall_at_k: float
    reciprocal_rank: float

    @property
    def passed(self) -> bool:
        """상위 k 안에 기대 근거가 하나 이상 있으면 참이다."""
        return self.first_relevant_rank is not None

    def to_payload(self) -> dict[str, object]:
        """원문·생성 답변 없이 JSON 호환 평가 결과를 반환한다."""
        return {
            "case_id": self.case_id,
            "expected_chunk_ids": list(self.expected_chunk_ids),
            "retrieved_chunk_ids": list(self.retrieved_chunk_ids),
            "first_relevant_rank": self.first_relevant_rank,
            "passed": self.passed,
            "recall_at_k": self.recall_at_k,
            "reciprocal_rank": self.reciprocal_rank,
        }


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationReport:
    """고정 평가 세트 전체의 Recall@k·Hit rate·MRR 집계다."""

    top_k: int
    results: tuple[RetrievalEvaluationResult, ...]
    recall_at_k: float
    hit_rate: float
    mean_reciprocal_rank: float

    @property
    def evaluated_cases(self) -> int:
        """평가된 고정 질의 수를 반환한다."""
        return len(self.results)

    def to_payload(self) -> dict[str, object]:
        """프레임워크 없이 기록·비교할 수 있는 JSON 호환 평가 보고서를 반환한다."""
        return {
            "top_k": self.top_k,
            "evaluated_cases": self.evaluated_cases,
            "recall_at_k": self.recall_at_k,
            "hit_rate": self.hit_rate,
            "mean_reciprocal_rank": self.mean_reciprocal_rank,
            "results": [result.to_payload() for result in self.results],
        }


class RetrievalEvaluator:
    """주입된 로컬 검색기를 고정 기대 청크 ID로 평가한다.

    생성기를 호출하지 않고 ``search``만 실행한다. 검색기가 반환하는 값도 다시 검증해
    tuple 이외 값, 요청보다 많은 결과, ``SearchHit`` 이외 값, 중복 청크 ID를 평가
    지표에 반영하지 않는다. 검색기 내부 오류는 숨기지 않고 호출자에게 전파한다.
    """

    def __init__(
        self, *, index: SearchableIndex, config: RetrievalEvaluationConfig | None = None
    ) -> None:
        if not hasattr(index, "search"):
            raise RagConfigurationError("index must provide a search method")
        self._index = index
        self._config = config or RetrievalEvaluationConfig()

    def evaluate(self, cases: Iterable[RetrievalEvaluationCase]) -> RetrievalEvaluationReport:
        """명시한 고정 사례만 평가하고 마이크로 Recall@k·Hit rate·MRR을 반환한다."""
        evaluation_cases = self._validated_cases(cases)
        results = tuple(self._evaluate_case(case) for case in evaluation_cases)
        expected_count = sum(len(result.expected_chunk_ids) for result in results)
        recovered_count = sum(
            len(set(result.expected_chunk_ids).intersection(result.retrieved_chunk_ids))
            for result in results
        )
        hit_count = sum(result.passed for result in results)
        return RetrievalEvaluationReport(
            top_k=self._config.top_k,
            results=results,
            recall_at_k=recovered_count / expected_count,
            hit_rate=hit_count / len(results),
            mean_reciprocal_rank=sum(result.reciprocal_rank for result in results) / len(results),
        )

    def _validated_cases(
        self, cases: Iterable[RetrievalEvaluationCase]
    ) -> tuple[RetrievalEvaluationCase, ...]:
        try:
            evaluation_cases = tuple(cases)
        except TypeError as error:
            raise RagConfigurationError(
                "evaluation cases must be an iterable of RetrievalEvaluationCase values"
            ) from error
        if not evaluation_cases:
            raise RagConfigurationError("at least one evaluation case is required")
        if len(evaluation_cases) > self._config.max_cases:
            raise RagConfigurationError("evaluation received more cases than configured")
        if any(not isinstance(case, RetrievalEvaluationCase) for case in evaluation_cases):
            raise RagConfigurationError("evaluation cases must be RetrievalEvaluationCase values")
        case_ids = [case.case_id for case in evaluation_cases]
        if len(set(case_ids)) != len(case_ids):
            raise RagConfigurationError("evaluation case_id values must be unique")
        return evaluation_cases

    def _evaluate_case(self, case: RetrievalEvaluationCase) -> RetrievalEvaluationResult:
        hits = self._validated_hits(self._index.search(case.query, top_k=self._config.top_k))
        retrieved_chunk_ids = tuple(hit.chunk.chunk_id for hit in hits)
        expected_chunk_ids = set(case.expected_chunk_ids)
        first_relevant_rank = next(
            (
                rank
                for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1)
                if chunk_id in expected_chunk_ids
            ),
            None,
        )
        recovered_count = len(expected_chunk_ids.intersection(retrieved_chunk_ids))
        return RetrievalEvaluationResult(
            case_id=case.case_id,
            expected_chunk_ids=case.expected_chunk_ids,
            retrieved_chunk_ids=retrieved_chunk_ids,
            first_relevant_rank=first_relevant_rank,
            recall_at_k=recovered_count / len(expected_chunk_ids),
            reciprocal_rank=0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank,
        )

    def _validated_hits(self, hits: tuple[SearchHit, ...]) -> tuple[SearchHit, ...]:
        if not isinstance(hits, tuple):
            raise RagConfigurationError("index must return a tuple of SearchHit values")
        if len(hits) > self._config.top_k:
            raise RagConfigurationError("index returned more hits than requested")
        chunk_ids: set[str] = set()
        for hit in hits:
            if not isinstance(hit, SearchHit):
                raise RagConfigurationError("index must return SearchHit values")
            if hit.chunk.chunk_id in chunk_ids:
                raise RagConfigurationError("index must not return duplicate hit chunk IDs")
            chunk_ids.add(hit.chunk.chunk_id)
        return hits
