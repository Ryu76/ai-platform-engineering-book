"""로컬 문서만으로 동작하는 결정론적 RAG 검색·인용 경계다.

이 모듈은 임베딩 서비스나 LLM을 직접 호출하지 않는다. 생성기는 Protocol로
주입하므로 단위 테스트와 예제는 항상 Mock 생성기로 실행할 수 있다.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


class RagConfigurationError(ValueError):
    """RAG 입력·청크·검색 설정이 안전한 계약을 벗어날 때 발생한다."""


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """로컬에서 읽은 하나의 출처 문서다."""

    document_id: str
    title: str
    source_uri: str
    content: str

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise RagConfigurationError("document_id must not be empty")
        if not self.title.strip():
            raise RagConfigurationError("title must not be empty")
        if not self.source_uri.strip():
            raise RagConfigurationError("source_uri must not be empty")
        if not self.content.strip():
            raise RagConfigurationError("document content must not be empty")


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """문자 수 기준의 재현 가능한 로컬 청킹 설정이다."""

    chunk_size: int = 240
    overlap: int = 40

    def __post_init__(self) -> None:
        if (
            isinstance(self.chunk_size, bool)
            or not isinstance(self.chunk_size, int)
            or self.chunk_size < 40
        ):
            raise RagConfigurationError("chunk_size must be an integer of at least 40")
        if isinstance(self.overlap, bool) or not isinstance(self.overlap, int) or self.overlap < 0:
            raise RagConfigurationError("overlap must be a nonnegative integer")
        if self.overlap >= self.chunk_size:
            raise RagConfigurationError("overlap must be smaller than chunk_size")


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """출처와 원래 문자 범위를 보존한 검색 단위다."""

    chunk_id: str
    document_id: str
    title: str
    source_uri: str
    text: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True, slots=True)
class Citation:
    """답변이 의존한 원문 조각을 사용자가 추적할 수 있게 하는 인용이다."""

    label: int
    chunk_id: str
    title: str
    source_uri: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True, slots=True)
class SearchHit:
    """쿼리 토큰과 겹치는 로컬 문서 조각 및 결정론적 점수다."""

    chunk: DocumentChunk
    score: int
    matched_terms: tuple[str, ...]

    def citation(self, *, label: int) -> Citation:
        """답변에 표시할 순번 인용을 만든다."""
        return Citation(
            label=label,
            chunk_id=self.chunk.chunk_id,
            title=self.chunk.title,
            source_uri=self.chunk.source_uri,
            start_offset=self.chunk.start_offset,
            end_offset=self.chunk.end_offset,
        )


@dataclass(frozen=True, slots=True)
class RagAnswer:
    """생성 결과 또는 안전한 No-answer와 그 근거 인용이다."""

    text: str
    citations: tuple[Citation, ...]
    no_answer: bool


class ContextualGenerator(Protocol):
    """검색된 근거만 받는 생성기 경계다. 구현체는 외부 호출을 강제하지 않는다."""

    def generate(self, *, query: str, contexts: tuple[SearchHit, ...]) -> str:
        """질문과 인용 가능한 검색 근거로 답변 텍스트를 생성한다."""


class LocalRagIndex:
    """외부 인프라 없이 문서 청킹과 어휘 검색을 제공하는 교육용 인덱스다."""

    def __init__(
        self, documents: Iterable[SourceDocument], *, chunking: ChunkingConfig | None = None
    ) -> None:
        """문서를 한 번 청크로 변환한다. 문서 내용은 이 시점에 외부로 전송되지 않는다."""
        self._chunking = chunking or ChunkingConfig()
        document_list = tuple(documents)
        if not document_list:
            raise RagConfigurationError("at least one source document is required")
        identifiers = [document.document_id for document in document_list]
        if len(set(identifiers)) != len(identifiers):
            raise RagConfigurationError("document_id values must be unique")
        self._chunks = tuple(
            chunk
            for document in document_list
            for chunk in _chunk_document(document, self._chunking)
        )

    @property
    def chunks(self) -> tuple[DocumentChunk, ...]:
        """검증·디버깅을 위해 불변 청크 목록을 노출한다."""
        return self._chunks

    def search(self, query: str, *, top_k: int = 3) -> tuple[SearchHit, ...]:
        """중복을 제거한 쿼리 용어의 출현 수로 상위 근거를 결정론적으로 반환한다."""
        if not query.strip():
            raise RagConfigurationError("query must not be empty")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 20:
            raise RagConfigurationError("top_k must be an integer between 1 and 20")

        query_terms = set(_terms(query))
        if not query_terms:
            return ()

        hits: list[SearchHit] = []
        for chunk in self._chunks:
            term_counts = Counter(_terms(chunk.text))
            matches = {term: _count_term_matches(term, term_counts) for term in query_terms}
            matched_terms = tuple(sorted(term for term, count in matches.items() if count > 0))
            if matched_terms:
                score = sum(matches[term] for term in matched_terms)
                hits.append(SearchHit(chunk=chunk, score=score, matched_terms=matched_terms))

        hits.sort(key=lambda hit: (-hit.score, hit.chunk.document_id, hit.chunk.start_offset))
        return tuple(hits[:top_k])


class RagPipeline:
    """검색 근거가 없으면 생성기를 호출하지 않는 최소 RAG 오케스트레이터다."""

    NO_ANSWER_TEXT = (
        "관련 문서를 찾지 못했습니다. 질문을 더 구체적으로 작성하거나 문서를 추가하세요."
    )

    def __init__(self, *, index: LocalRagIndex, generator: ContextualGenerator) -> None:
        self._index = index
        self._generator = generator

    def answer(self, query: str, *, top_k: int = 3) -> RagAnswer:
        """검색된 조각만 생성기에 전달하고, 모든 근거에 인용을 부여한다."""
        hits = self._index.search(query, top_k=top_k)
        if not hits:
            return RagAnswer(text=self.NO_ANSWER_TEXT, citations=(), no_answer=True)

        text = self._generator.generate(query=query, contexts=hits).strip()
        if not text:
            raise RagConfigurationError("generator returned an empty answer")
        citations = tuple(
            hit.citation(label=position) for position, hit in enumerate(hits, start=1)
        )
        return RagAnswer(text=text, citations=citations, no_answer=False)


def _chunk_document(document: SourceDocument, config: ChunkingConfig) -> tuple[DocumentChunk, ...]:
    """공백 경계를 우선하되 진행을 보장하면서 원래 오프셋을 보존해 청크를 만든다."""
    text = document.content
    chunks: list[DocumentChunk] = []
    start = 0
    chunk_number = 1
    while start < len(text):
        end = min(start + config.chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + 1, end + 1)
            if boundary > start:
                end = boundary
        raw_text = text[start:end]
        left_trim = len(raw_text) - len(raw_text.lstrip())
        right_trimmed = raw_text.rstrip()
        chunk_text = right_trimmed.lstrip()
        if chunk_text:
            chunk_start = start + left_trim
            chunk_end = chunk_start + len(chunk_text)
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{document.document_id}#{chunk_number}",
                    document_id=document.document_id,
                    title=document.title,
                    source_uri=document.source_uri,
                    text=chunk_text,
                    start_offset=chunk_start,
                    end_offset=chunk_end,
                )
            )
            chunk_number += 1
        if end == len(text):
            break
        start = max(end - config.overlap, start + 1)
    return tuple(chunks)


def _terms(text: str) -> tuple[str, ...]:
    """한글·라틴 문자·숫자 토큰으로 제한해 구두점 차이를 검색에서 제거한다."""
    return tuple(token.casefold() for token in re.findall(r"[0-9A-Za-z가-힣_]+", text))


def _count_term_matches(query_term: str, term_counts: Counter[str]) -> int:
    """정확 일치와 한글 조사·활용어의 접두 일치를 안전하게 센다.

    공백 토큰화만 하면 ``배송`` 질의가 ``배송은``을, ``확인`` 질의가
    ``확인합니다``를 찾지 못한다. 외부 형태소 분석기 없이도 로컬 예제에서
    이 흔한 경우를 다루되, 라틴 문자와 숫자는 의도치 않은 부분 일치를 막기
    위해 정확 일치만 허용한다.
    """
    if re.fullmatch(r"[가-힣]+", query_term):
        return sum(count for token, count in term_counts.items() if token.startswith(query_term))
    return term_counts[query_term]
