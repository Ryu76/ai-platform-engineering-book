"""고정 골든 라벨과 기록된 답변을 결정론적으로 평가한다."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from ai_platform.evaluation.golden_dataset import ExpectedResponse


class AnswerEvaluationError(ValueError):
    """답변 평가 입력이 고정 골든 계약을 위반할 때 발생한다."""


ResponseMode = Literal["answer", "abstain"]


@dataclass(frozen=True, slots=True)
class AnswerCase:
    """기대 동작, 허용 사실, 인용 가능한 문서로 구성한 오프라인 답변 사례다."""

    case_id: str
    expected_response: ExpectedResponse
    supported_fact_ids: tuple[str, ...]
    allowed_citation_document_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """answer/no-answer 라벨과 사실·인용 근거의 모순을 차단한다."""
        _require_non_empty("case_id", self.case_id)
        _validate_identifiers("supported fact ids", self.supported_fact_ids)
        _validate_identifiers(
            "allowed citation document ids", self.allowed_citation_document_ids
        )
        if self.expected_response not in {"answer", "abstain"}:
            raise AnswerEvaluationError("expected_response must be 'answer' or 'abstain'")
        if self.expected_response == "answer" and not self.supported_fact_ids:
            raise AnswerEvaluationError("answer cases must define at least one supported fact")
        if self.expected_response == "answer" and not self.allowed_citation_document_ids:
            raise AnswerEvaluationError("answer cases must define at least one allowed citation")
        if self.expected_response == "abstain" and self.supported_fact_ids:
            raise AnswerEvaluationError("abstain cases must not define supported facts")
        if self.expected_response == "abstain" and self.allowed_citation_document_ids:
            raise AnswerEvaluationError("abstain cases must not define allowed citations")


@dataclass(frozen=True, slots=True)
class RecordedAnswer:
    """라이브 모델 호출 없이 검토 가능한 답변 행동·주장·인용 기록이다."""

    case_id: str
    response_mode: ResponseMode
    asserted_fact_ids: tuple[str, ...]
    cited_document_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """모호한 응답 모드와 중복 주장·인용을 평가 전에 거부한다."""
        _require_non_empty("case_id", self.case_id)
        if self.response_mode not in {"answer", "abstain"}:
            raise AnswerEvaluationError("response_mode must be 'answer' or 'abstain'")
        _validate_identifiers("asserted fact ids", self.asserted_fact_ids)
        _validate_identifiers("cited document ids", self.cited_document_ids)
        if self.response_mode == "abstain" and self.asserted_fact_ids:
            raise AnswerEvaluationError("abstain responses must not assert facts")
        if self.response_mode == "abstain" and self.cited_document_ids:
            raise AnswerEvaluationError("abstain responses must not cite documents")


@dataclass(frozen=True, slots=True)
class AnswerCaseMetrics:
    """한 사례의 행동 일치, 사실 지원, 인용 지원, 환각 주장을 보관한다."""

    case_id: str
    response_matches_expectation: bool
    answer_is_correct: bool
    unsupported_fact_ids: tuple[str, ...]
    supported_citation_ids: tuple[str, ...]
    unsupported_citation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnswerMetrics:
    """고정 사례 집합에서 계산한 답변·보류·환각·인용 품질 지표다."""

    cases_evaluated: int
    answer_accuracy: float
    abstention_accuracy: float
    hallucination_rate: float
    citation_accuracy: float


def evaluate_answers(
    cases: Sequence[AnswerCase],
    recorded_answers_by_case: Mapping[str, RecordedAnswer],
) -> AnswerMetrics:
    """고정 사실·인용 라벨과 기록 답변을 집계해 결정론적 지표를 반환한다."""
    case_metrics = evaluate_answer_cases(cases, recorded_answers_by_case)
    abstain_metrics = tuple(
        metric
        for case, metric in zip(cases, case_metrics, strict=True)
        if case.expected_response == "abstain"
    )
    asserted_fact_count = sum(
        len(recorded_answers_by_case[case.case_id].asserted_fact_ids) for case in cases
    )
    cited_document_count = sum(
        len(recorded_answers_by_case[case.case_id].cited_document_ids) for case in cases
    )
    unsupported_fact_count = sum(
        len(metric.unsupported_fact_ids) for metric in case_metrics
    )
    supported_citation_count = sum(
        len(metric.supported_citation_ids) for metric in case_metrics
    )
    return AnswerMetrics(
        cases_evaluated=len(case_metrics),
        answer_accuracy=sum(metric.answer_is_correct for metric in case_metrics)
        / len(case_metrics),
        abstention_accuracy=(
            sum(metric.response_matches_expectation for metric in abstain_metrics)
            / len(abstain_metrics)
            if abstain_metrics
            else 0.0
        ),
        hallucination_rate=(
            unsupported_fact_count / asserted_fact_count if asserted_fact_count else 0.0
        ),
        citation_accuracy=(
            supported_citation_count / cited_document_count if cited_document_count else 0.0
        ),
    )


def evaluate_answer_cases(
    cases: Sequence[AnswerCase],
    recorded_answers_by_case: Mapping[str, RecordedAnswer],
) -> tuple[AnswerCaseMetrics, ...]:
    """입력 사례 순서대로 답변 행동·사실·인용의 지원 여부를 계산한다."""
    _validate_cases(cases)
    case_ids = {case.case_id for case in cases}
    answer_case_ids = set(recorded_answers_by_case)
    if case_ids != answer_case_ids:
        missing = sorted(case_ids - answer_case_ids)
        unexpected = sorted(answer_case_ids - case_ids)
        raise AnswerEvaluationError(
            f"recorded answers must match case ids; missing={missing}, unexpected={unexpected}"
        )

    metrics: list[AnswerCaseMetrics] = []
    for case in cases:
        answer = recorded_answers_by_case[case.case_id]
        if answer.case_id != case.case_id:
            raise AnswerEvaluationError(
                f"recorded answer key and case_id must match for {case.case_id}"
            )
        supported_facts = set(case.supported_fact_ids)
        allowed_citations = set(case.allowed_citation_document_ids)
        unsupported_facts = tuple(
            fact_id for fact_id in answer.asserted_fact_ids if fact_id not in supported_facts
        )
        supported_citations = tuple(
            document_id
            for document_id in answer.cited_document_ids
            if document_id in allowed_citations
        )
        unsupported_citations = tuple(
            document_id
            for document_id in answer.cited_document_ids
            if document_id not in allowed_citations
        )
        response_matches = answer.response_mode == case.expected_response
        answer_is_correct = (
            response_matches
            and not unsupported_facts
            and (
                case.expected_response == "abstain"
                or set(case.supported_fact_ids).issubset(answer.asserted_fact_ids)
            )
        )
        metrics.append(
            AnswerCaseMetrics(
                case_id=case.case_id,
                response_matches_expectation=response_matches,
                answer_is_correct=answer_is_correct,
                unsupported_fact_ids=unsupported_facts,
                supported_citation_ids=supported_citations,
                unsupported_citation_ids=unsupported_citations,
            )
        )
    return tuple(metrics)


def _validate_cases(cases: Sequence[AnswerCase]) -> None:
    """빈 평가와 중복 사례 ID를 차단한다."""
    if not cases:
        raise AnswerEvaluationError("at least one answer case is required")
    case_ids = tuple(case.case_id for case in cases)
    if len(set(case_ids)) != len(case_ids):
        raise AnswerEvaluationError("answer case ids must be unique")


def _require_non_empty(field_name: str, value: str) -> None:
    """사례 식별자의 빈 값과 비문자열 값을 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise AnswerEvaluationError(f"{field_name} must be a non-empty string")


def _validate_identifiers(field_name: str, identifiers: tuple[str, ...]) -> None:
    """사실·문서 식별자는 중복 없는 비어 있지 않은 문자열이어야 한다."""
    if any(not isinstance(identifier, str) or not identifier.strip() for identifier in identifiers):
        raise AnswerEvaluationError(f"{field_name} must be non-empty strings")
    if len(set(identifiers)) != len(identifiers):
        raise AnswerEvaluationError(f"{field_name} must be unique")
