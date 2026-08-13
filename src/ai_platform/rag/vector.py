"""주입 가능한 로컬/Mock 임베딩과 메모리 벡터 저장소를 위한 RAG 경계다.

이 모듈은 임베딩 SDK, 벡터 DB, 네트워크 클라이언트를 직접 만들지 않는다. 호출자가
주입한 ``TextEmbedder``는 명시한 로컬 청크와 질의만 벡터로 바꾸며, ``VectorStore``는
청크 ID와 수치 벡터만 받는다. 따라서 원문·출처 URI·문자 범위는 저장소에 복사되지 않고
검색 결과를 이미 검증된 ``LocalRagIndex`` 청크에 다시 연결해 인용 경계를 보존한다.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Protocol

from ai_platform.rag.retrieval import (
    DocumentChunk,
    LocalRagIndex,
    RagConfigurationError,
    SearchHit,
    _validate_search_input,
)


@dataclass(frozen=True, slots=True)
class VectorRecord:
    """원문 없이 로컬 청크 식별자와 검증된 임베딩만 보관하는 저장 단위다."""

    chunk_id: str
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.chunk_id, str) or not self.chunk_id.strip():
            raise RagConfigurationError("vector record chunk_id must be a non-empty string")
        _validate_embedding_vector(self.values, field_name="vector record values")


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    """벡터 저장소가 반환하는 청크 ID와 0~1 정규화 유사도다."""

    chunk_id: str
    similarity: float

    def __post_init__(self) -> None:
        if not isinstance(self.chunk_id, str) or not self.chunk_id.strip():
            raise RagConfigurationError("vector search result chunk_id must be a non-empty string")
        if (
            isinstance(self.similarity, bool)
            or not isinstance(self.similarity, (int, float))
            or not math.isfinite(self.similarity)
            or not 0.0 <= self.similarity <= 1.0
        ):
            raise RagConfigurationError(
                "vector search result similarity must be a finite number between 0 and 1"
            )


class TextEmbedder(Protocol):
    """로컬/Mock 구현으로 교체 가능한 텍스트 임베딩 경계다."""

    def embed(self, *, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """입력 순서와 같은 수의 유한한 비영 벡터를 반환한다."""


class VectorStore(Protocol):
    """청크 ID와 수치 벡터만 보관·검색하는 주입 가능한 저장소 경계다."""

    def replace(self, *, records: tuple[VectorRecord, ...]) -> None:
        """명시한 전체 레코드로 저장소 내용을 원자적으로 교체한다."""

    def search(
        self, *, query_vector: tuple[float, ...], top_k: int
    ) -> tuple[VectorSearchResult, ...]:
        """질의 벡터와 가장 가까운 명시 레코드를 유사도 순으로 반환한다."""


@dataclass(frozen=True, slots=True)
class QdrantPoint:
    """Qdrant 호환 컬렉션 경계에 전달하는 최소 point 표현이다.

    원문·제목·출처 URI·오프셋 같은 payload는 이 계약에 없다. 호출자는 이미 검증한
    ``chunk_id``와 수치 벡터만 전달할 수 있어 기존 로컬 인용 경계를 보존한다.
    """

    point_id: str
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.point_id, str) or not self.point_id.strip():
            raise RagConfigurationError("Qdrant point_id must be a non-empty string")
        _validate_embedding_vector(self.vector, field_name="Qdrant point vector")


@dataclass(frozen=True, slots=True)
class QdrantScoredPoint:
    """Qdrant cosine 점수와 point ID를 좁은 로컬 경계로 표현한다."""

    point_id: str
    score: float

    def __post_init__(self) -> None:
        if not isinstance(self.point_id, str) or not self.point_id.strip():
            raise RagConfigurationError("Qdrant scored point point_id must be a non-empty string")
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not math.isfinite(self.score)
            or not -1.0 <= self.score <= 1.0
        ):
            raise RagConfigurationError(
                "Qdrant cosine score must be a finite number between -1 and 1"
            )


class QdrantCollection(Protocol):
    """Qdrant SDK를 직접 의존하지 않는 좁은 컬렉션 어댑터 경계다.

    실제 SDK를 쓸 경우 호출자가 SDK 버전에 맞는 작은 구현체를 주입한다. 예제와
    테스트는 동일한 메서드를 구현한 in-memory Mock만 사용한다. 이 Protocol은
    컬렉션 생성·네트워크·인증·환경 변수 로드를 수행하지 않는다.
    """

    def replace_points(self, *, collection_name: str, points: tuple[QdrantPoint, ...]) -> None:
        """명시 컬렉션의 point를 주어진 전체 point로 교체한다."""

    def search_points(
        self, *, collection_name: str, query_vector: tuple[float, ...], limit: int
    ) -> tuple[QdrantScoredPoint, ...]:
        """내림차순 cosine 점수의 명시 point만 반환한다."""


class QdrantVectorStore:
    """주입된 Qdrant 호환 컬렉션을 ``VectorStore`` 계약으로 제한한다.

    이 어댑터는 ``qdrant-client``를 import하거나 컬렉션·네트워크 연결을 만들지 않는다.
    로컬/Mock 또는 호출자가 만든 SDK 어댑터에 전체 point 교체와 검색을 위임한다. Qdrant의
    cosine ``[-1, 1]`` 점수는 기존 RAG 경계가 요구하는 ``[0, 1]`` 유사도로 정규화하며,
    정렬·중복·차원·알 수 없는 point는 상위 ``VectorRagIndex``가 인용에 연결하기 전에
    계속 검증한다.
    """

    def __init__(self, *, collection: QdrantCollection, collection_name: str) -> None:
        if not hasattr(collection, "replace_points") or not hasattr(collection, "search_points"):
            raise RagConfigurationError(
                "Qdrant collection must provide replace_points and search_points methods"
            )
        if not isinstance(collection_name, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", collection_name
        ):
            raise RagConfigurationError(
                "Qdrant collection_name must contain 1 to 64 letters, digits, "
                "underscores, or hyphens"
            )
        self._collection = collection
        self._collection_name = collection_name
        self._dimensions: int | None = None

    def replace(self, *, records: tuple[VectorRecord, ...]) -> None:
        """검증된 ID·벡터만 명시한 Qdrant 호환 컬렉션에 전달한다."""
        if not isinstance(records, tuple) or not records:
            raise RagConfigurationError("Qdrant vector store records must be a non-empty tuple")
        if any(not isinstance(record, VectorRecord) for record in records):
            raise RagConfigurationError(
                "Qdrant vector store records must contain VectorRecord values"
            )
        point_ids = [record.chunk_id for record in records]
        if len(set(point_ids)) != len(point_ids):
            raise RagConfigurationError(
                "Qdrant vector store records must not contain duplicate chunk IDs"
            )
        dimensions = len(records[0].values)
        if any(len(record.values) != dimensions for record in records):
            raise RagConfigurationError("Qdrant vector store records must have the same dimensions")
        self._collection.replace_points(
            collection_name=self._collection_name,
            points=tuple(
                QdrantPoint(point_id=record.chunk_id, vector=record.values) for record in records
            ),
        )
        self._dimensions = dimensions

    def search(
        self, *, query_vector: tuple[float, ...], top_k: int
    ) -> tuple[VectorSearchResult, ...]:
        """Qdrant cosine 결과를 검증된 0~1 유사도 검색 결과로 변환한다."""
        _validate_search_limit(top_k)
        if self._dimensions is None:
            raise RagConfigurationError(
                "Qdrant vector store must be initialized with records before search"
            )
        _validate_embedding_vector(query_vector, field_name="Qdrant vector store query_vector")
        if len(query_vector) != self._dimensions:
            raise RagConfigurationError(
                "Qdrant vector store query_vector dimensions must match stored records"
            )
        results = self._collection.search_points(
            collection_name=self._collection_name, query_vector=query_vector, limit=top_k
        )
        if not isinstance(results, tuple):
            raise RagConfigurationError(
                "Qdrant collection must return a tuple of QdrantScoredPoint values"
            )
        if len(results) > top_k:
            raise RagConfigurationError("Qdrant collection returned more results than requested")
        point_ids: set[str] = set()
        for result in results:
            if not isinstance(result, QdrantScoredPoint):
                raise RagConfigurationError(
                    "Qdrant collection must return QdrantScoredPoint values"
                )
            if result.point_id in point_ids:
                raise RagConfigurationError("Qdrant collection must not return duplicate point IDs")
            point_ids.add(result.point_id)
        if tuple(sorted(results, key=lambda result: (-result.score, result.point_id))) != results:
            raise RagConfigurationError(
                "Qdrant collection results must be sorted by descending cosine score"
            )
        return tuple(
            VectorSearchResult(
                chunk_id=result.point_id,
                similarity=(float(result.score) + 1.0) / 2.0,
            )
            for result in results
        )


class InMemoryVectorStore:
    """테스트와 로컬 예제용 결정론적 메모리 벡터 저장소다.

    저장소는 문서 원문이나 출처 메타데이터를 받지 않는다. 같은 차원의 ``VectorRecord``
    tuple 하나만 명시적으로 교체하며, cosine 유사도를 0~1 범위로 정규화한다. 외부 벡터
    DB, 파일, 네트워크, 제공자 SDK는 사용하지 않는다.
    """

    def __init__(self) -> None:
        self._records: tuple[VectorRecord, ...] = ()
        self._dimensions: int | None = None

    def replace(self, *, records: tuple[VectorRecord, ...]) -> None:
        """중복 없는 동일 차원 레코드만 새 메모리 상태로 교체한다."""
        if not isinstance(records, tuple) or not records:
            raise RagConfigurationError("vector store records must be a non-empty tuple")
        if any(not isinstance(record, VectorRecord) for record in records):
            raise RagConfigurationError("vector store records must contain VectorRecord values")
        chunk_ids = [record.chunk_id for record in records]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise RagConfigurationError("vector store records must not contain duplicate chunk IDs")
        dimensions = len(records[0].values)
        if any(len(record.values) != dimensions for record in records):
            raise RagConfigurationError("vector store records must have the same dimensions")
        self._records = records
        self._dimensions = dimensions

    def search(
        self, *, query_vector: tuple[float, ...], top_k: int
    ) -> tuple[VectorSearchResult, ...]:
        """정규화 cosine 유사도와 청크 ID로 결정론적으로 정렬한다."""
        _validate_search_limit(top_k)
        if not self._records or self._dimensions is None:
            raise RagConfigurationError(
                "vector store must be initialized with records before search"
            )
        _validate_embedding_vector(query_vector, field_name="vector store query_vector")
        if len(query_vector) != self._dimensions:
            raise RagConfigurationError(
                "vector store query_vector dimensions must match stored records"
            )
        query_norm = math.sqrt(sum(value * value for value in query_vector))
        results = [
            VectorSearchResult(
                chunk_id=record.chunk_id,
                similarity=(
                    1.0
                    + sum(
                        query * value
                        for query, value in zip(query_vector, record.values, strict=True)
                    )
                    / (query_norm * math.sqrt(sum(value * value for value in record.values)))
                )
                / 2.0,
            )
            for record in self._records
        ]
        results.sort(key=lambda result: (-result.similarity, result.chunk_id))
        return tuple(results[:top_k])


@dataclass(frozen=True, slots=True)
class VectorRagIndexConfig:
    """주입된 임베딩·저장소 경계의 차원 및 청크 상한이다."""

    max_embedding_dimensions: int = 1_024
    max_indexed_chunks: int = 1_000

    def __post_init__(self) -> None:
        for field_name, value, maximum in (
            ("max_embedding_dimensions", self.max_embedding_dimensions, 4_096),
            ("max_indexed_chunks", self.max_indexed_chunks, 10_000),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise RagConfigurationError(
                    f"{field_name} must be an integer between 1 and {maximum}"
                )


class VectorRagIndex:
    """검증된 로컬 청크를 주입된 임베딩과 저장소로 의미 기반 검색한다.

    생성 시 ``LocalRagIndex``가 이미 만든 청크 텍스트만 한 번 임베딩하고, 저장소에는
    청크 ID·벡터만 전달한다. 검색 시 저장소가 돌려준 ID는 같은 로컬 청크에만 다시
    연결한다. 따라서 Mock 제공자나 메모리 저장소가 알 수 없는 ID, 중복 결과, 잘못된
    타입/점수를 반환하면 인용 또는 생성 전에 즉시 거부한다.
    """

    def __init__(
        self,
        *,
        source_index: LocalRagIndex,
        embedder: TextEmbedder,
        vector_store: VectorStore,
        config: VectorRagIndexConfig | None = None,
    ) -> None:
        if not isinstance(source_index, LocalRagIndex):
            raise RagConfigurationError("source_index must be a LocalRagIndex")
        if not hasattr(embedder, "embed"):
            raise RagConfigurationError("embedder must provide an embed method")
        if not hasattr(vector_store, "replace") or not hasattr(vector_store, "search"):
            raise RagConfigurationError("vector_store must provide replace and search methods")
        self._source_index = source_index
        self._embedder = embedder
        self._vector_store = vector_store
        self._config = config or VectorRagIndexConfig()
        chunks = source_index.chunks
        if len(chunks) > self._config.max_indexed_chunks:
            raise RagConfigurationError("source index has more chunks than configured")
        self._chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        vectors = self._embed_texts(tuple(chunk.text for chunk in chunks), operation="index")
        self._dimensions = len(vectors[0])
        vector_store.replace(
            records=tuple(
                VectorRecord(chunk_id=chunk.chunk_id, values=vector)
                for chunk, vector in zip(chunks, vectors, strict=True)
            )
        )

    @property
    def chunks(self) -> tuple[DocumentChunk, ...]:
        """원래 로컬 청크를 노출하되 저장소에는 원문을 전달하지 않는다."""
        return self._source_index.chunks

    def search(self, query: str, *, top_k: int = 3) -> tuple[SearchHit, ...]:
        """질의를 임베딩해 검증된 로컬 청크 인용 가능 근거로 되돌린다."""
        _validate_search_input(query=query, top_k=top_k)
        query_vector = self._embed_texts((query,), operation="query")[0]
        if len(query_vector) != self._dimensions:
            raise RagConfigurationError("query embedding dimensions must match indexed embeddings")
        results = self._validated_results(
            self._vector_store.search(query_vector=query_vector, top_k=top_k), top_k=top_k
        )
        return tuple(
            SearchHit(
                chunk=self._chunks_by_id[result.chunk_id],
                score=float(result.similarity),
                matched_terms=(),
            )
            for result in results
        )

    def _embed_texts(
        self, texts: tuple[str, ...], *, operation: str
    ) -> tuple[tuple[float, ...], ...]:
        vectors = self._embedder.embed(texts=texts)
        if not isinstance(vectors, tuple) or len(vectors) != len(texts):
            raise RagConfigurationError(
                f"embedder must return one tuple vector per {operation} text"
            )
        for vector in vectors:
            _validate_embedding_vector(vector, field_name=f"{operation} embedding")
            if len(vector) > self._config.max_embedding_dimensions:
                raise RagConfigurationError("embedding dimensions exceed the configured limit")
        dimensions = len(vectors[0])
        if any(len(vector) != dimensions for vector in vectors):
            raise RagConfigurationError("embedder must return vectors with the same dimensions")
        return vectors

    def _validated_results(
        self, results: tuple[VectorSearchResult, ...], *, top_k: int
    ) -> tuple[VectorSearchResult, ...]:
        if not isinstance(results, tuple):
            raise RagConfigurationError(
                "vector store must return a tuple of VectorSearchResult values"
            )
        if len(results) > top_k:
            raise RagConfigurationError("vector store returned more results than requested")
        result_ids: set[str] = set()
        for result in results:
            if not isinstance(result, VectorSearchResult):
                raise RagConfigurationError("vector store must return VectorSearchResult values")
            if result.chunk_id in result_ids:
                raise RagConfigurationError("vector store must not return duplicate chunk IDs")
            if result.chunk_id not in self._chunks_by_id:
                raise RagConfigurationError(
                    "vector store result must reference an indexed local chunk"
                )
            result_ids.add(result.chunk_id)
        if (
            tuple(sorted(results, key=lambda result: (-result.similarity, result.chunk_id)))
            != results
        ):
            raise RagConfigurationError(
                "vector store results must be sorted by descending similarity"
            )
        return results


def _validate_search_limit(top_k: int) -> None:
    """저장소 경계에도 공개 검색 결과 수 계약을 적용한다."""
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 20:
        raise RagConfigurationError("vector store top_k must be an integer between 1 and 20")


def _validate_embedding_vector(values: object, *, field_name: str) -> None:
    """cosine 유사도에 쓸 수 있는 유한한 비영 tuple 벡터인지 확인한다."""
    if not isinstance(values, tuple) or not values:
        raise RagConfigurationError(f"{field_name} must be a non-empty tuple of numbers")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
        for value in values
    ):
        raise RagConfigurationError(f"{field_name} must contain finite numbers")
    if not any(value != 0.0 for value in values):
        raise RagConfigurationError(f"{field_name} must not be a zero vector")
