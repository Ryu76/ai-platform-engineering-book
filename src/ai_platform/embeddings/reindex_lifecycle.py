"""결정적 local mock으로 삭제와 재색인을 검증하는 Volume 04 미니 프로젝트."""
from __future__ import annotations

from dataclasses import dataclass

from ai_platform.embeddings.embedding_service import DeterministicEmbeddingModel
from ai_platform.embeddings.retrieval_evaluation import RetrievalMetrics, evaluate_ranking
from ai_platform.embeddings.vector_store import InMemoryVectorStore, VectorPoint


@dataclass(frozen=True, slots=True)
class ReindexLifecycleReport:
    """삭제 전후와 재색인 뒤의 검색 계약을 담는 불변 실행 결과다."""

    initial_ranked_ids: tuple[str, ...]
    ranked_ids_after_delete: tuple[str, ...]
    reindexed_ranked_ids: tuple[str, ...]
    initial_metrics: RetrievalMetrics
    reindexed_metrics: RetrievalMetrics
    deleted_count: int
    collection_size_after_delete: int
    collection_size: int
    reindexed_version: int


def run_reindex_lifecycle() -> ReindexLifecycleReport:
    """같은 point ID를 삭제한 뒤 새 vector와 metadata로 재색인한다.

    네트워크, Docker, API 키, 외부 모델을 사용하지 않는다. 반환값은 예제 출력과
    단위 테스트가 공유하는 작은 lifecycle 계약이다.
    """
    model = DeterministicEmbeddingModel(dimensions=256)
    store = InMemoryVectorStore()
    collection_name = "platform_docs"
    store.create_collection(collection_name, vector_size=256)
    store.upsert(
        collection_name,
        [
            VectorPoint(
                id="retry-guide",
                vector=model.embed_one("Python API 오류 처리와 재시도 전략"),
                payload={"topic": "api", "version": 1, "state": "published"},
            ),
            VectorPoint(
                id="vector-guide",
                vector=model.embed_one("벡터 데이터베이스에서 문서를 검색하는 방법"),
                payload={"topic": "vector", "version": 1, "state": "published"},
            ),
            VectorPoint(
                id="docker-guide",
                vector=model.embed_one("Docker 컨테이너의 포트 설정"),
                payload={"topic": "infra", "version": 1, "state": "published"},
            ),
        ],
    )

    initial_query = "Python API 오류 처리와 재시도 전략"
    initial_results = store.search(collection_name, model.embed_one(initial_query), limit=3)
    initial_metrics = evaluate_ranking(
        [result.id for result in initial_results], {"retry-guide"}, k=1
    )

    deleted_count = store.delete(collection_name, ["retry-guide"])
    collection_size_after_delete = store.collection_size(collection_name)
    results_after_delete = store.search(collection_name, model.embed_one(initial_query), limit=3)

    reindexed_query = "Python API 오류 처리와 지수 백오프 재시도 전략"
    store.upsert(
        collection_name,
        [
            VectorPoint(
                id="retry-guide",
                vector=model.embed_one(reindexed_query),
                payload={"topic": "api", "version": 2, "state": "published"},
            )
        ],
    )
    reindexed_results = store.search(
        collection_name,
        model.embed_one(reindexed_query),
        limit=3,
        metadata_filter={"version": 2},
    )
    reindexed_metrics = evaluate_ranking(
        [result.id for result in reindexed_results], {"retry-guide"}, k=1
    )
    reindexed_version = reindexed_results[0].payload["version"]
    if isinstance(reindexed_version, bool) or not isinstance(reindexed_version, int):
        raise RuntimeError("reindexed point must have an integer version")

    return ReindexLifecycleReport(
        initial_ranked_ids=tuple(result.id for result in initial_results),
        ranked_ids_after_delete=tuple(result.id for result in results_after_delete),
        reindexed_ranked_ids=tuple(result.id for result in reindexed_results),
        initial_metrics=initial_metrics,
        reindexed_metrics=reindexed_metrics,
        deleted_count=deleted_count,
        collection_size_after_delete=collection_size_after_delete,
        collection_size=store.collection_size(collection_name),
        reindexed_version=reindexed_version,
    )
