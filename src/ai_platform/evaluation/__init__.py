"""오프라인·결정론적 AI 플랫폼 평가 도구."""

from ai_platform.evaluation.datasets import (
    FIXED_GOLDEN_DATASET,
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
    "FIXED_GOLDEN_DATASET",
    "FIXED_RETRIEVAL_CASES",
    "FIXED_RETRIEVAL_RESULTS_AT_3",
    "GoldenCase",
    "GoldenDataset",
    "GoldenDatasetError",
    "GoldenDatasetSummary",
    "RetrievalCase",
    "RetrievalCaseMetrics",
    "RetrievalEvaluationError",
    "RetrievalMetrics",
    "evaluate_retrieval",
    "evaluate_retrieval_cases",
    "summarize_golden_dataset",
]
