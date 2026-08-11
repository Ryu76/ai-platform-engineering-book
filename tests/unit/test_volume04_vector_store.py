"""Volume 04의 결정적 in-memory vector store 계약 테스트."""
from __future__ import annotations

import pytest

from ai_platform.embeddings import (
    CollectionNotFoundError,
    DeterministicEmbeddingModel,
    InMemoryVectorStore,
    VectorDimensionError,
    VectorPoint,
    VectorStoreError,
)


@pytest.fixture
def populated_store() -> tuple[InMemoryVectorStore, DeterministicEmbeddingModel]:
    """서로 다른 metadata를 갖는 결정적 교육용 collection을 준비한다."""
    model = DeterministicEmbeddingModel(dimensions=64)
    store = InMemoryVectorStore()
    store.create_collection("platform_docs", vector_size=64)
    store.upsert(
        "platform_docs",
        [
            VectorPoint(
                id="retry-guide",
                vector=model.embed_one("Python API 오류 처리와 재시도 전략"),
                payload={"topic": "api", "version": 1},
            ),
            VectorPoint(
                id="vector-guide",
                vector=model.embed_one("벡터 데이터베이스에서 문서를 검색하는 방법"),
                payload={"topic": "vector", "version": 1},
            ),
            VectorPoint(
                id="docker-guide",
                vector=model.embed_one("Docker 컨테이너의 포트 설정"),
                payload={"topic": "infra", "version": 1},
            ),
        ],
    )
    return store, model


def test_search_ranks_related_document_and_returns_its_payload(
    populated_store: tuple[InMemoryVectorStore, DeterministicEmbeddingModel],
) -> None:
    """같은 mock embedding 공간의 관련 문서는 가장 높은 score와 metadata를 반환한다."""
    store, model = populated_store

    results = store.search("platform_docs", model.embed_one("Python API 오류 처리 방법"), limit=2)

    assert [result.id for result in results][0] == "retry-guide"
    assert results[0].payload == {"topic": "api", "version": 1}
    assert results[0].score > results[1].score


def test_search_applies_metadata_filter(
    populated_store: tuple[InMemoryVectorStore, DeterministicEmbeddingModel],
) -> None:
    """payload filter는 vector score를 계산하기 전 후보를 좁혀야 한다."""
    store, model = populated_store

    results = store.search(
        "platform_docs",
        model.embed_one("문서 검색"),
        metadata_filter={"topic": "vector"},
    )

    assert [result.id for result in results] == ["vector-guide"]


def test_metadata_filter_requires_an_existing_key_and_matching_scalar_type() -> None:
    """Python의 bool/int 동치나 누락 key가 filter 후보를 넓히면 안 된다."""
    store = InMemoryVectorStore()
    store.create_collection("typed_payloads", vector_size=2)
    store.upsert(
        "typed_payloads",
        [
            VectorPoint(id="integer", vector=[1.0, 0.0], payload={"version": 1}),
            VectorPoint(id="boolean", vector=[0.0, 1.0], payload={"published": True}),
            VectorPoint(id="null", vector=[-1.0, 0.0], payload={"deleted_at": None}),
        ],
    )

    boolean_version_results = store.search(
        "typed_payloads", [1.0, 0.0], metadata_filter={"version": True}
    )
    null_results = store.search(
        "typed_payloads", [1.0, 0.0], metadata_filter={"deleted_at": None}
    )

    assert boolean_version_results == []
    assert [result.id for result in null_results] == ["null"]


def test_upsert_replaces_same_id_and_keeps_collection_size(
    populated_store: tuple[InMemoryVectorStore, DeterministicEmbeddingModel],
) -> None:
    """upsert는 동일 id를 새 vector와 payload로 원자적으로 교체해야 한다."""
    store, model = populated_store

    store.upsert(
        "platform_docs",
        [
            VectorPoint(
                id="retry-guide",
                vector=model.embed_one("업데이트된 Python 오류 처리 문서"),
                payload={"topic": "api", "version": 2},
            )
        ],
    )

    results = store.search(
        "platform_docs",
        model.embed_one("업데이트된 Python 오류 처리"),
        metadata_filter={"version": 2},
    )
    assert store.collection_size("platform_docs") == 3
    assert [(result.id, result.payload["version"]) for result in results] == [("retry-guide", 2)]


def test_upsert_defensively_copies_caller_owned_vector_and_payload() -> None:
    """색인 뒤 caller가 입력 객체를 바꿔도 저장된 point가 바뀌면 안 된다."""
    store = InMemoryVectorStore()
    store.create_collection("copy_boundary", vector_size=2)
    vector = [1.0, 0.0]
    payload = {"topic": "api", "version": 1}

    store.upsert(
        "copy_boundary",
        [VectorPoint(id="retry-guide", vector=vector, payload=payload)],
    )
    vector[0] = 0.0
    vector[1] = 1.0
    payload["topic"] = "mutated"
    payload["version"] = 2

    results = store.search("copy_boundary", [1.0, 0.0])

    assert [(result.id, result.score, dict(result.payload)) for result in results] == [
        ("retry-guide", 1.0, {"topic": "api", "version": 1})
    ]
    with pytest.raises(TypeError):
        results[0].payload["topic"] = "changed"  # type: ignore[index]


def test_upsert_is_atomic_when_a_batch_contains_an_invalid_vector(
    populated_store: tuple[InMemoryVectorStore, DeterministicEmbeddingModel],
) -> None:
    """batch 중 하나가 틀리면 앞의 유효 point도 저장되면 안 된다."""
    store, model = populated_store

    with pytest.raises(VectorDimensionError, match="dimension 64"):
        store.upsert(
            "platform_docs",
            [
                VectorPoint(id="valid", vector=model.embed_one("유효한 문서"), payload={}),
                VectorPoint(id="invalid", vector=[1.0, 2.0], payload={}),
            ],
        )

    assert store.collection_size("platform_docs") == 3
    assert store.search("platform_docs", model.embed_one("유효한 문서"))[0].id != "valid"


@pytest.mark.parametrize("points", [[], (), "retry-guide", b"retry-guide", None])
def test_upsert_rejects_empty_or_non_batch_point_inputs(points: object) -> None:
    """upsert는 빈 batch나 문자열을 point 목록으로 해석하면 안 된다."""
    store = InMemoryVectorStore()
    store.create_collection("docs", vector_size=2)

    with pytest.raises(VectorStoreError, match="non-empty sequence of VectorPoint instances"):
        store.upsert("docs", points)  # type: ignore[arg-type]


def test_delete_reports_actual_count_and_removes_points(
    populated_store: tuple[InMemoryVectorStore, DeterministicEmbeddingModel],
) -> None:
    """이미 없는 id는 무시하되 실제 삭제한 point 수만 반환해야 한다."""
    store, model = populated_store

    assert store.delete("platform_docs", ["docker-guide", "missing", "docker-guide"]) == 1
    assert store.collection_size("platform_docs") == 2
    assert all(
        result.id != "docker-guide"
        for result in store.search("platform_docs", model.embed_one("Docker 포트"))
    )


@pytest.mark.parametrize("point_ids", [[], (), "docker-guide", b"docker-guide", None])
def test_delete_rejects_empty_or_non_batch_id_inputs(point_ids: object) -> None:
    """삭제는 의도하지 않은 no-op나 단일 문자열을 ID batch로 해석하면 안 된다."""
    store = InMemoryVectorStore()
    store.create_collection("docs", vector_size=2)

    with pytest.raises(VectorStoreError, match="non-empty sequence of strings"):
        store.delete("docs", point_ids)  # type: ignore[arg-type]


def test_collection_and_point_contract_errors_are_explicit() -> None:
    """존재하지 않는 collection과 잘못된 설정은 조용히 통과하면 안 된다."""
    store = InMemoryVectorStore()

    with pytest.raises(CollectionNotFoundError, match="not found"):
        store.collection_size("missing")
    with pytest.raises(VectorStoreError, match="positive"):
        store.create_collection("invalid", vector_size=0)

    store.create_collection("docs", vector_size=2)
    with pytest.raises(VectorStoreError, match="zero vector"):
        store.upsert("docs", [VectorPoint(id="zero", vector=[0.0, 0.0], payload={})])
    with pytest.raises(VectorStoreError, match="positive"):
        store.search("docs", [1.0, 0.0], limit=0)


def test_equal_scores_are_sorted_by_id_for_deterministic_results() -> None:
    """동점 결과는 point id 순서로 정렬해 예제와 테스트를 재현 가능하게 만든다."""
    store = InMemoryVectorStore()
    store.create_collection("ties", vector_size=2)
    store.upsert(
        "ties",
        [
            VectorPoint(id="z-last", vector=[1.0, 0.0], payload={}),
            VectorPoint(id="a-first", vector=[1.0, 0.0], payload={}),
        ],
    )

    assert [result.id for result in store.search("ties", [1.0, 0.0])] == ["a-first", "z-last"]
