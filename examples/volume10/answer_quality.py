"""고정 답변 기록의 정확도·보류·환각·인용 품질을 외부 호출 없이 평가한다."""
from __future__ import annotations

from ai_platform.evaluation import (
    FIXED_ANSWER_CASES,
    FIXED_RECORDED_ANSWERS,
    evaluate_answers,
)


def main() -> None:
    """고정 답변 평가 기준선을 사람이 읽을 수 있는 형식으로 출력한다."""
    metrics = evaluate_answers(FIXED_ANSWER_CASES, FIXED_RECORDED_ANSWERS)
    print(f"Evaluation cases: {metrics.cases_evaluated}")
    print(f"Answer accuracy: {metrics.answer_accuracy:.6f}")
    print(f"Abstention accuracy: {metrics.abstention_accuracy:.6f}")
    print(f"Hallucination rate: {metrics.hallucination_rate:.6f}")
    print(f"Citation accuracy: {metrics.citation_accuracy:.6f}")


if __name__ == "__main__":
    main()
