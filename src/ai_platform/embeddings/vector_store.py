"""결정적 로컬 테스트를 위한 in-memory vector collection 경계.

이 모듈은 Qdrant 서버의 대체품이 아니다. 네트워크, Docker, API 키 없이
collection, point, payload, upsert, 검색 및 삭제의 계약을 학습·검증하기 위한
작은 교육용 구현이다.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import TypeAlias

from ai_platform.embeddings.embedding_service import VectorDimensionError, cosine_similarity

# Python 3.11에서도 import 가능한 교육용 코드여야 하므로 3.12 `type` 문법을 쓰지 않는다.
PayloadValue: TypeAlias = str | int | float | bool | None  # noqa: UP040


class VectorStoreError(ValueError):
    """collection 또는 point 계약이 유효하지 않을 때 발생한다."""


class CollectionNotFoundError(VectorStoreError):
    """존재하지 않는 collection을 읽거나 변경할 때 발생한다."""


@dataclass(frozen=True, slots=True)
class VectorPoint:
    """collection에 저장할 point와 payload(metadata)다.

    `id`는 collection 안에서 고유해야 하며, `vector`의 길이는 collection의
    vector size와 같아야 한다. payload에는 JSON scalar에 해당하는 값만 둔다.
    """

    id: str
    vector: Sequence[float]
    payload: Mapping[str, PayloadValue]


@dataclass(frozen=True, slots=True)
class SearchResult:
    """유사도 검색에서 반환되는 불변의 point 요약이다."""

    id: str
    score: float
    payload: Mapping[str, PayloadValue]


@dataclass(slots=True)
class _Collection:
    """한 collection의 설정과 point를 보관하는 내부 자료구조다."""

    vector_size: int
    points: dict[str, VectorPoint]


class InMemoryVectorStore:
    """cosine similarity를 사용하는 결정적 로컬 vector store다.

    실제 Qdrant 연결 전, 애플리케이션이 의존하는 저장·검색 계약을 단위 테스트로
    확인하는 용도다. 프로세스가 끝나면 모든 데이터가 사라진다.
    """

    def __init__(self) -> None:
        """비어 있는 로컬 store를 만든다."""
        self._collections: dict[str, _Collection] = {}

    def create_collection(self, name: str, *, vector_size: int) -> None:
        """고정 vector size를 가진 빈 collection을 만든다."""
        _require_collection_name(name)
        _require_vector_size(vector_size)
        if name in self._collections:
            raise VectorStoreError(f"collection already exists: {name}")
        self._collections[name] = _Collection(vector_size=vector_size, points={})

    def upsert(self, collection_name: str, points: Sequence[VectorPoint]) -> None:
        """검증된 point를 새로 저장하거나 같은 id의 기존 point를 교체한다.

        전체 batch를 먼저 검증하므로 하나라도 잘못된 point가 있으면 collection은
        변경되지 않는다.
        """
        collection = self._get_collection(collection_name)
        prepared_points = _prepare_points(points, vector_size=collection.vector_size)
        collection.points.update(prepared_points)

    def search(
        self,
        collection_name: str,
        query_vector: Sequence[float],
        *,
        limit: int = 5,
        metadata_filter: Mapping[str, PayloadValue] | None = None,
    ) -> list[SearchResult]:
        """payload filter를 적용한 뒤 cosine score 내림차순으로 point를 반환한다.

        동일 score는 point id 오름차순으로 정렬해 반복 실행 결과를 결정적으로 만든다.
        """
        collection = self._get_collection(collection_name)
        _require_limit(limit)
        prepared_query = _prepare_vector(query_vector, vector_size=collection.vector_size)
        prepared_filter = _prepare_payload(metadata_filter) if metadata_filter is not None else None

        results = [
            SearchResult(
                id=point.id,
                score=cosine_similarity(prepared_query, point.vector),
                payload=point.payload,
            )
            for point in collection.points.values()
            if _matches_filter(point.payload, prepared_filter)
        ]
        return sorted(results, key=lambda result: (-result.score, result.id))[:limit]

    def delete(self, collection_name: str, point_ids: Sequence[str]) -> int:
        """지정한 id의 point를 삭제하고 실제 삭제 수를 반환한다."""
        collection = self._get_collection(collection_name)
        normalized_ids = _prepare_ids(point_ids)
        deleted = 0
        for point_id in normalized_ids:
            if point_id in collection.points:
                del collection.points[point_id]
                deleted += 1
        return deleted

    def collection_size(self, collection_name: str) -> int:
        """collection에 저장된 point 수를 반환한다."""
        return len(self._get_collection(collection_name).points)

    def _get_collection(self, name: str) -> _Collection:
        """이름을 검증한 뒤 존재하는 collection을 반환한다."""
        _require_collection_name(name)
        try:
            return self._collections[name]
        except KeyError as error:
            raise CollectionNotFoundError(f"collection not found: {name}") from error


def _prepare_points(points: Sequence[VectorPoint], *, vector_size: int) -> dict[str, VectorPoint]:
    """batch 전체를 검증하고 저장에 안전한 불변 point로 복사한다."""
    if not points:
        raise VectorStoreError("points must not be empty")

    prepared: dict[str, VectorPoint] = {}
    for point in points:
        if not isinstance(point, VectorPoint):
            raise VectorStoreError("points must contain VectorPoint instances")
        _require_point_id(point.id)
        if point.id in prepared:
            raise VectorStoreError(f"duplicate point id in batch: {point.id}")
        prepared[point.id] = VectorPoint(
            id=point.id,
            vector=tuple(_prepare_vector(point.vector, vector_size=vector_size)),
            payload=MappingProxyType(_prepare_payload(point.payload)),
        )
    return prepared


def _prepare_vector(vector: Sequence[float], *, vector_size: int) -> list[float]:
    """vector의 차원, 수치성, 유한성을 검증해 독립된 list로 복사한다."""
    if isinstance(vector, (str, bytes)) or not isinstance(vector, Sequence):
        raise VectorStoreError("vector must be a sequence of finite numbers")
    if len(vector) != vector_size:
        raise VectorDimensionError(f"vector must have dimension {vector_size}")

    prepared: list[float] = []
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise VectorStoreError("vector must contain only finite numbers")
        prepared.append(float(value))
    if not any(prepared):
        raise VectorStoreError("vector must not be a zero vector")
    return prepared


def _prepare_payload(payload: Mapping[str, PayloadValue]) -> dict[str, PayloadValue]:
    """metadata key와 JSON scalar payload value를 검증·복사한다."""
    if not isinstance(payload, Mapping):
        raise VectorStoreError("payload must be a mapping")

    prepared: dict[str, PayloadValue] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not key.strip():
            raise VectorStoreError("payload keys must be non-empty strings")
        if isinstance(value, float) and not isfinite(value):
            raise VectorStoreError("payload float values must be finite")
        if not isinstance(value, (str, int, float, bool, type(None))):
            raise VectorStoreError("payload values must be JSON scalar values")
        prepared[key] = value
    return prepared


def _matches_filter(
    payload: Mapping[str, PayloadValue], metadata_filter: Mapping[str, PayloadValue] | None
) -> bool:
    """filter의 모든 key/value가 payload에 같은 scalar type으로 있는지 판단한다."""
    return metadata_filter is None or all(
        key in payload and type(payload[key]) is type(value) and payload[key] == value
        for key, value in metadata_filter.items()
    )


def _prepare_ids(point_ids: Sequence[str]) -> list[str]:
    """삭제할 id 목록을 검증하고 중복 없이 보존한다."""
    if isinstance(point_ids, (str, bytes)) or not isinstance(point_ids, Sequence):
        raise VectorStoreError("point_ids must be a sequence of strings")
    normalized_ids: list[str] = []
    for point_id in point_ids:
        _require_point_id(point_id)
        if point_id not in normalized_ids:
            normalized_ids.append(point_id)
    return normalized_ids


def _require_collection_name(name: str) -> None:
    """collection 이름을 검증한다."""
    if not isinstance(name, str) or not name.strip():
        raise VectorStoreError("collection name must be a non-empty string")


def _require_point_id(point_id: str) -> None:
    """point id를 검증한다."""
    if not isinstance(point_id, str) or not point_id.strip():
        raise VectorStoreError("point id must be a non-empty string")


def _require_vector_size(vector_size: int) -> None:
    """collection의 vector size를 검증한다."""
    if isinstance(vector_size, bool) or not isinstance(vector_size, int) or vector_size < 1:
        raise VectorStoreError("vector_size must be a positive integer")


def _require_limit(limit: int) -> None:
    """검색 결과 개수를 검증한다."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise VectorStoreError("limit must be a positive integer")
