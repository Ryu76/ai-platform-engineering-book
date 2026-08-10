"""Volume 10의 고정 답변 정확도·환각·인용 평가 계약을 검증한다."""
from __future__ import annotations

import pytest

from ai_platform.evaluation import (
    FIXED_ANSWER_CASES,
    FIXED_RECORDED_ANSWERS,
    AnswerCase,
    AnswerEvaluationError,
    RecordedAnswer,
    evaluate_answer_cases,
    evaluate_answers,
)


def test_fixed_recorded_answers_have_reproducible_quality_metrics() -> None:
    """같은 고정 라벨과 답변 기록은 항상 동일한 품질 기준선을 만든다."""
    metrics = evaluate_answers(FIXED_ANSWER_CASES, FIXED_RECORDED_ANSWERS)

    assert metrics.cases_evaluated == 5
    assert metrics.answer_accuracy == pytest.approx(0.8)
    assert metrics.abstention_accuracy == pytest.approx(0.0)
    assert metrics.hallucination_rate == pytest.approx(1 / 6)
    assert metrics.citation_accuracy == pytest.approx(2 / 3)


def test_case_metrics_expose_unsupported_answer_and_citations() -> None:
    """평균이 숨기는 no-answer 위반과 부정확한 인용을 사례별로 확인한다."""
    case_metrics = evaluate_answer_cases(FIXED_ANSWER_CASES, FIXED_RECORDED_ANSWERS)

    assert tuple(metric.case_id for metric in case_metrics) == (
        "access-reset",
        "expense-receipt",
        "incident-response",
        "benefits-enrollment",
        "office-parking",
    )
    assert case_metrics[3].answer_is_correct is True
    assert case_metrics[3].unsupported_citation_ids == ("identity-access",)
    assert case_metrics[4].response_matches_expectation is False
    assert case_metrics[4].answer_is_correct is False
    assert case_metrics[4].unsupported_fact_ids == ("parking-pass-application-is-available",)
    assert case_metrics[4].unsupported_citation_ids == ("service-overview",)


def test_answer_metrics_reject_missing_or_unexpected_recorded_answers() -> None:
    """일부 사례만 평가해 평균을 좋게 보이게 하는 입력을 거부한다."""
    incomplete = {"access-reset": FIXED_RECORDED_ANSWERS["access-reset"]}

    with pytest.raises(AnswerEvaluationError, match="missing="):
        evaluate_answers(FIXED_ANSWER_CASES, incomplete)


def test_answer_metrics_reject_record_key_and_payload_case_id_mismatch() -> None:
    """사전 키와 응답의 사례 ID가 다르면 다른 라벨로 측정하지 않는다."""
    answers = dict(FIXED_RECORDED_ANSWERS)
    answers["access-reset"] = RecordedAnswer(
        case_id="expense-receipt",
        response_mode="answer",
        asserted_fact_ids=("reset-identity-verification",),
        cited_document_ids=("identity-access",),
    )

    with pytest.raises(AnswerEvaluationError, match="key and case_id"):
        evaluate_answers(FIXED_ANSWER_CASES, answers)


@pytest.mark.parametrize(
    ("expected_response", "facts", "citations", "message"),
    [
        ("answer", (), ("policy-a",), "supported fact"),
        ("abstain", ("claim-a",), (), "abstain cases"),
        ("abstain", (), ("policy-a",), "abstain cases"),
    ],
)
def test_answer_cases_reject_ambiguous_grounding_contracts(
    expected_response: str,
    facts: tuple[str, ...],
    citations: tuple[str, ...],
    message: str,
) -> None:
    """답변 가능·보류 라벨은 허용 사실과 인용 근거에 대해 모순될 수 없다."""
    with pytest.raises(AnswerEvaluationError, match=message):
        AnswerCase(
            case_id="case-a",
            expected_response=expected_response,  # type: ignore[arg-type]
            supported_fact_ids=facts,
            allowed_citation_document_ids=citations,
        )


def test_recorded_abstention_rejects_facts_or_citations() -> None:
    """보류 응답에 주장이나 인용을 숨겨 넣는 기록을 허용하지 않는다."""
    with pytest.raises(AnswerEvaluationError, match="must not assert"):
        RecordedAnswer("case-a", "abstain", ("claim-a",), ())
    with pytest.raises(AnswerEvaluationError, match="must not cite"):
        RecordedAnswer("case-a", "abstain", (), ("policy-a",))
