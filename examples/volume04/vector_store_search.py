"""결정적 로컬 mock으로 collection, payload, vector 검색을 실행한다."""
from __future__ import annotations

from ai_platform.embeddings import DeterministicEmbeddingModel, InMemoryVectorStore, VectorPoint


def main() -> None:
    """외부 서비스 없이 문서를 upsert하고 metadata filter 검색 결과를 출력한다."""
    model = DeterministicEmbeddingModel(dimensions=64)
    store = InMemoryVectorStore()
    store.create_collection("platform_docs", vector_size=64)

    documents = [
        ("retry-guide", "Python API 오류 처리와 재시도 전략", {"topic": "api", "version": 1}),
        (
            "vector-guide",
            "벡터 데이터베이스에서 문서를 검색하는 방법",
            {"topic": "vector", "version": 1},
        ),
        ("docker-guide", "Docker 컨테이너의 포트 설정", {"topic": "infra", "version": 1}),
    ]
    store.upsert(
        "platform_docs",
        [
            VectorPoint(id=document_id, vector=model.embed_one(text), payload=metadata)
            for document_id, text, metadata in documents
        ],
    )

    query_vector = model.embed_one("Python API 오류 처리 방법")
    results = store.search("platform_docs", query_vector, limit=2, metadata_filter={"topic": "api"})

    print(f"collection_size={store.collection_size('platform_docs')}")
    for rank, result in enumerate(results, start=1):
        print(f"{rank}. id={result.id} score={result.score:.3f} topic={result.payload['topic']}")


if __name__ == "__main__":
    main()
