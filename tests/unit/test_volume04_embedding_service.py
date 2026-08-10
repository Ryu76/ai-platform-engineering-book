"""Volume 04의 결정적 로컬 임베딩 및 벡터 수학 단위 테스트."""
from __future__ import annotations

import math

import pytest

from ai_platform.embeddings import (
    DeterministicEmbeddingModel,
    EmbeddingConfigurationError,
    VectorDimensionError,
    cosine_similarity,
    dot_product,
    euclidean_distance,
)


def test_deterministic_model_returns_same_normalized_vector_for_same_text() -> None:
    """로컬 모델은 실행과 인스턴스가 바뀌어도 동일한 dense vector를 만들어야 한다."""
    first = DeterministicEmbeddingModel(dimensions=32).embed_one("Python API 오류 처리")
    second = DeterministicEmbeddingModel(dimensions=32).embed_one("Python API 오류 처리")

    assert first == second
    assert len(first) == 32
    assert math.isclose(sum(value * value for value in first), 1.0)


def test_document_and_query_with_shared_tokens_rank_above_unrelated_document() -> None:
    """같은 토큰을 가진 문서는 고정 mock 공간에서 관련 없는 문서보다 가까워야 한다."""
    model = DeterministicEmbeddingModel(dimensions=256)
    query = model.embed_one("Python API 오류 처리")
    related = model.embed_one("Python API 오류 처리와 재시도")
    unrelated = model.embed_one("Docker 컨테이너 포트 네트워크")

    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


def test_vector_operations_return_expected_values() -> None:
    """dot product, cosine similarity, Euclidean distance의 기준값을 검증한다."""
    left = [1.0, 0.0]
    right = [0.0, 1.0]

    assert dot_product(left, right) == 0.0
    assert cosine_similarity(left, right) == 0.0
    assert euclidean_distance(left, right) == pytest.approx(math.sqrt(2))


@pytest.mark.parametrize("dimensions", [True, 7, 4097])
def test_model_rejects_invalid_dimensions(dimensions: int | bool) -> None:
    """잘못된 차원은 데이터가 생성되기 전에 거부해야 한다."""
    with pytest.raises(EmbeddingConfigurationError, match="dimensions"):
        DeterministicEmbeddingModel(dimensions=dimensions)


@pytest.mark.parametrize("text", ["", "   ", "!!!", None])
def test_model_rejects_empty_or_tokenless_text(text: str | None) -> None:
    """빈 문서나 단어가 없는 문서는 명시적으로 실패해야 한다."""
    with pytest.raises(EmbeddingConfigurationError):
        DeterministicEmbeddingModel().embed_one(text)  # type: ignore[arg-type]


def test_vector_operations_reject_mismatched_and_zero_vectors() -> None:
    """잘못된 차원과 zero vector는 조용히 잘못된 점수를 만들면 안 된다."""
    with pytest.raises(VectorDimensionError, match="same dimension"):
        dot_product([1.0], [1.0, 2.0])
    with pytest.raises(VectorDimensionError, match="zero vector"):
        cosine_similarity([0.0, 0.0], [1.0, 0.0])
