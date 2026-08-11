"""결정적 local mock으로 삭제와 재색인을 검증하는 Volume 04 미니 프로젝트."""

from __future__ import annotations

from dataclasses import dataclass

from ai_platform.embeddings.embedding_service import DeterministicEmbeddingModel
from ai_platform.embeddings.retrieval_evaluation import RetrievalMetrics, evaluate_ranking
from ai_platform.embeddings.vector_store import InMemoryVectorStore, VectorPoint


class ReindexLifecycleError(ValueError):
    """재색인 lifecycle 보고서 계약이 유효하지 않을 때 발생한다."""


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

    def __post_init__(self) -> None:
        """공개 보고서가 불변 lifecycle 상태만 노출하도록 검증한다."""
        _require_ranked_ids(self.initial_ranked_ids, name="initial_ranked_ids")
        _require_ranked_ids(self.ranked_ids_after_delete, name="ranked_ids_after_delete")
        _require_ranked_ids(self.reindexed_ranked_ids, name="reindexed_ranked_ids")
        if not isinstance(self.initial_metrics, RetrievalMetrics):
            raise ReindexLifecycleError("initial_metrics must be a RetrievalMetrics instance")
        if not isinstance(self.reindexed_metrics, RetrievalMetrics):
            raise ReindexLifecycleError("reindexed_metrics must be a RetrievalMetrics instance")
        _require_nonnegative_integer(self.deleted_count, name="deleted_count")
        _require_nonnegative_integer(
            self.collection_size_after_delete, name="collection_size_after_delete"
        )
        _require_nonnegative_integer(self.collection_size, name="collection_size")
        if (
            isinstance(self.reindexed_version, bool)
            or not isinstance(self.reindexed_version, int)
            or self.reindexed_version < 1
        ):
            raise ReindexLifecycleError("reindexed_version must be a positive integer")


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


def _require_ranked_ids(ranked_ids: tuple[str, ...], *, name: str) -> None:
    """보고서 순위가 caller가 바꿀 수 없는 유효한 tuple인지 검증한다."""
    if not isinstance(ranked_ids, tuple):
        raise ReindexLifecycleError(f"{name} must be a tuple of non-empty strings")
    if any(not isinstance(point_id, str) or not point_id.strip() for point_id in ranked_ids):
        raise ReindexLifecycleError(f"{name} must contain non-empty strings")
    if len(set(ranked_ids)) != len(ranked_ids):
        raise ReindexLifecycleError(f"{name} must not contain duplicates")


def _require_nonnegative_integer(value: int, *, name: str) -> None:
    """삭제 수와 collection 크기가 bool이 아닌 0 이상의 정수인지 검증한다."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReindexLifecycleError(f"{name} must be a non-negative integer")
