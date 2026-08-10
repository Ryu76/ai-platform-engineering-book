"""결정적 로컬 mock 검색의 top-k 품질과 no-answer gate를 확인한다."""
from __future__ import annotations

from ai_platform.embeddings import (
    DeterministicEmbeddingModel,
    InMemoryVectorStore,
    VectorPoint,
    evaluate_ranking,
    meets_score_threshold,
)


def main() -> None:
    """외부 서비스 없이 정답 ID 기준 검색 품질을 출력한다."""
    model = DeterministicEmbeddingModel(dimensions=256)
    store = InMemoryVectorStore()
    store.create_collection("platform_docs", vector_size=256)
    store.upsert(
        "platform_docs",
        [
            VectorPoint(
                id="retry-guide",
                vector=model.embed_one("Python API 오류 처리와 재시도 전략"),
                payload={"topic": "api"},
            ),
            VectorPoint(
                id="vector-guide",
                vector=model.embed_one("벡터 데이터베이스에서 문서를 검색하는 방법"),
                payload={"topic": "vector"},
            ),
            VectorPoint(
                id="docker-guide",
                vector=model.embed_one("Docker 컨테이너의 포트 설정"),
                payload={"topic": "infra"},
            ),
        ],
    )

    results = store.search(
        "platform_docs", model.embed_one("Python API 오류 처리 방법"), limit=2
    )
    metrics = evaluate_ranking([result.id for result in results], {"retry-guide"}, k=1)
    top_score = results[0].score

    print("ranked_ids=" + ",".join(result.id for result in results))
    print(
        "precision_at_1="
        f"{metrics.precision_at_k:.1f}; recall_at_1={metrics.recall_at_k:.1f}; "
        f"mrr={metrics.reciprocal_rank:.1f}; hit_at_1={metrics.hit_at_k}"
    )
    print(
        f"top_score={top_score:.3f}; minimum_score=0.500; "
        f"answerable={meets_score_threshold(top_score, minimum_score=0.5)}"
    )


if __name__ == "__main__":
    main()
