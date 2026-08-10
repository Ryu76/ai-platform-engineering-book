"""오프라인·결정론적 AI 플랫폼 평가 도구."""

from ai_platform.evaluation.answer_metrics import (
    AnswerCase,
    AnswerCaseMetrics,
    AnswerEvaluationError,
    AnswerMetrics,
    RecordedAnswer,
    evaluate_answer_cases,
    evaluate_answers,
)
from ai_platform.evaluation.datasets import (
    FIXED_ANSWER_CASES,
    FIXED_GOLDEN_DATASET,
    FIXED_RECORDED_ANSWERS,
    FIXED_RETRIEVAL_CASES,
    FIXED_RETRIEVAL_RESULTS_AT_3,
)
from ai_platform.evaluation.golden_dataset import (
    GoldenCase,
    GoldenDataset,
    GoldenDatasetError,
    GoldenDatasetSummary,
    summarize_golden_dataset,
)
from ai_platform.evaluation.retrieval_metrics import (
    RetrievalCase,
    RetrievalCaseMetrics,
    RetrievalEvaluationError,
    RetrievalMetrics,
    evaluate_retrieval,
    evaluate_retrieval_cases,
)

__all__ = [
    "AnswerCase",
    "AnswerCaseMetrics",
    "AnswerEvaluationError",
    "AnswerMetrics",
    "FIXED_ANSWER_CASES",
    "FIXED_GOLDEN_DATASET",
    "FIXED_RECORDED_ANSWERS",
    "FIXED_RETRIEVAL_CASES",
    "FIXED_RETRIEVAL_RESULTS_AT_3",
    "GoldenCase",
    "GoldenDataset",
    "GoldenDatasetError",
    "GoldenDatasetSummary",
    "RecordedAnswer",
    "RetrievalCase",
    "RetrievalCaseMetrics",
    "RetrievalEvaluationError",
    "RetrievalMetrics",
    "evaluate_answer_cases",
    "evaluate_answers",
    "evaluate_retrieval",
    "evaluate_retrieval_cases",
    "summarize_golden_dataset",
]
