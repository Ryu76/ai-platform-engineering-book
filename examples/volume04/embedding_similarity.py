"""네트워크 없이 문장 임베딩과 유사도를 확인하는 Volume 04 예제."""
from __future__ import annotations

from ai_platform.embeddings import DeterministicEmbeddingModel, cosine_similarity


def main() -> None:
    """고정 입력을 로컬 mock 임베딩으로 비교해 재현 가능한 결과를 출력한다."""
    model = DeterministicEmbeddingModel(dimensions=64)
    query = "Python API 오류 처리 방법"
    documents = [
        "Python API 오류 처리와 재시도 전략",
        "벡터 데이터베이스에서 문서를 검색하는 방법",
        "Docker 컨테이너의 포트 설정",
    ]

    query_vector = model.embed_one(query)
    ranked = sorted(
        (
            (cosine_similarity(query_vector, model.embed_one(document)), document)
            for document in documents
        ),
        reverse=True,
    )

    print(f"query_dimensions={len(query_vector)}")
    for rank, (score, document) in enumerate(ranked, start=1):
        print(f"{rank}. score={score:.3f} document={document}")


if __name__ == "__main__":
    main()
