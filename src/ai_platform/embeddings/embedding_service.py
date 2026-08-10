"""로컬에서 재현 가능한 교육용 텍스트 임베딩과 거리 계산 도구."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import sqrt
from re import findall
from typing import Protocol


class EmbeddingConfigurationError(ValueError):
    """임베딩 모델 설정 또는 입력 텍스트가 유효하지 않을 때 발생한다."""


class VectorDimensionError(ValueError):
    """벡터 차원이 다르거나 비어 있을 때 발생한다."""


class EmbeddingModel(Protocol):
    """문서와 질의에 같은 공간의 벡터를 제공하는 최소 인터페이스다."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """입력 텍스트마다 하나의 정규화된 dense vector를 반환한다."""


@dataclass(frozen=True, slots=True)
class DeterministicEmbeddingModel:
    """해시 기반으로 토큰을 dense vector에 투영하는 오프라인 교육용 모델이다.

    이 구현은 외부 모델 다운로드, API 키, 네트워크 연결을 전혀 사용하지 않는다.
    같은 입력과 차원은 어느 실행에서나 같은 결과를 만들지만, 의미를 학습한 실제
    임베딩 모델이 아니므로 운영 검색 품질의 기준으로 사용하면 안 된다.
    """

    dimensions: int = 64

    def __post_init__(self) -> None:
        """너무 작거나 지나치게 큰 교육용 벡터 차원을 거부한다."""
        if (
            isinstance(self.dimensions, bool)
            or not isinstance(self.dimensions, int)
            or not 8 <= self.dimensions <= 4096
        ):
            raise EmbeddingConfigurationError("dimensions must be an integer between 8 and 4096")

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """각 비어 있지 않은 텍스트를 L2 정규화된 고정 차원 벡터로 변환한다."""
        return [self.embed_one(text) for text in texts]

    def embed_one(self, text: str) -> list[float]:
        """단일 문서를 토큰 해싱으로 dense vector로 변환한다."""
        if not isinstance(text, str) or not text.strip():
            raise EmbeddingConfigurationError("text must be a non-empty string")

        vector = [0.0] * self.dimensions
        for token in _tokens(text):
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], byteorder="big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return _l2_normalize(vector)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """두 벡터의 방향 유사도를 -1.0부터 1.0 범위로 계산한다."""
    _require_same_nonempty_dimension(left, right)
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise VectorDimensionError("cosine similarity is undefined for a zero vector")
    return dot_product(left, right) / (left_norm * right_norm)


def dot_product(left: Sequence[float], right: Sequence[float]) -> float:
    """두 같은 차원 벡터의 dot product를 계산한다."""
    _require_same_nonempty_dimension(left, right)
    return sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=True)
    )


def euclidean_distance(left: Sequence[float], right: Sequence[float]) -> float:
    """두 같은 차원 벡터 사이의 직선 거리를 계산한다."""
    _require_same_nonempty_dimension(left, right)
    return sqrt(
        sum(
            (left_value - right_value) ** 2
            for left_value, right_value in zip(left, right, strict=True)
        )
    )


def _tokens(text: str) -> list[str]:
    """유니코드 단어와 숫자를 소문자 토큰으로 분리하고 빈 입력을 방지한다."""
    tokens = findall(r"\w+", text.casefold(), flags=0)
    if not tokens:
        raise EmbeddingConfigurationError("text must contain at least one letter or number")
    return tokens


def _l2_normalize(vector: list[float]) -> list[float]:
    """벡터 길이를 1로 맞춰 문장 길이보다 방향을 비교할 수 있게 한다."""
    magnitude = sqrt(sum(value * value for value in vector))
    if magnitude == 0:  # pragma: no cover - SHA-256 토큰 투영에서는 발생하지 않는다.
        raise EmbeddingConfigurationError("embedding vector must not be zero")
    return [value / magnitude for value in vector]


def _require_same_nonempty_dimension(left: Sequence[float], right: Sequence[float]) -> None:
    """거리 계산 전에 두 벡터가 비어 있지 않은 같은 차원인지 검증한다."""
    if not left or not right:
        raise VectorDimensionError("vectors must not be empty")
    if len(left) != len(right):
        raise VectorDimensionError("vectors must have the same dimension")
