"""Volume 04의 로컬 임베딩과 벡터 검색 교육용 인터페이스."""

from ai_platform.embeddings.embedding_service import (
    DeterministicEmbeddingModel,
    EmbeddingConfigurationError,
    EmbeddingModel,
    VectorDimensionError,
    cosine_similarity,
    dot_product,
    euclidean_distance,
)
from ai_platform.embeddings.reindex_lifecycle import (
    ReindexLifecycleReport,
    run_reindex_lifecycle,
)
from ai_platform.embeddings.retrieval_evaluation import (
    RetrievalEvaluationError,
    RetrievalMetrics,
    RetrievalSummary,
    evaluate_ranking,
    mean_retrieval_metrics,
    meets_score_threshold,
)
from ai_platform.embeddings.vector_store import (
    CollectionNotFoundError,
    InMemoryVectorStore,
    PayloadValue,
    SearchResult,
    VectorPoint,
    VectorStoreError,
)

__all__ = [
    "CollectionNotFoundError",
    "DeterministicEmbeddingModel",
    "EmbeddingConfigurationError",
    "EmbeddingModel",
    "InMemoryVectorStore",
    "PayloadValue",
    "RetrievalEvaluationError",
    "RetrievalMetrics",
    "RetrievalSummary",
    "ReindexLifecycleReport",
    "SearchResult",
    "VectorDimensionError",
    "VectorPoint",
    "VectorStoreError",
    "cosine_similarity",
    "dot_product",
    "euclidean_distance",
    "evaluate_ranking",
    "mean_retrieval_metrics",
    "meets_score_threshold",
    "run_reindex_lifecycle",
]
