from __future__ import annotations

from collections.abc import Callable

import pytest

from ai_platform.rag import (
    ChunkingConfig,
    LocalRagIndex,
    RagConfigurationError,
    RagPipeline,
    SearchHit,
    SourceDocument,
)


class RecordingGenerator:
    """외부 제공자를 호출하지 않고 받은 검색 근거를 기록하는 Mock 생성기다."""

    def __init__(self, response: str = "배송 정책은 영업일 기준으로 적용됩니다.") -> None:
        self.response = response
        self.calls: list[tuple[str, tuple[SearchHit, ...]]] = []

    def generate(self, *, query: str, contexts: tuple[SearchHit, ...]) -> str:
        self.calls.append((query, contexts))
        return self.response


def _index() -> LocalRagIndex:
    return LocalRagIndex(
        [
            SourceDocument(
                document_id="shipping",
                title="배송 안내",
                source_uri="local://handbook/shipping",
                content=(
                    "국내 배송은 결제 완료 뒤 영업일 2일에서 3일이 걸립니다. "
                    "배송 상태는 주문 번호로 확인합니다."
                ),
            ),
            SourceDocument(
                document_id="returns",
                title="반품 안내",
                source_uri="local://handbook/returns",
                content=(
                    "반품은 상품 수령 뒤 7일 안에 신청할 수 있습니다. "
                    "배송비 정책은 상품 상태에 따라 다릅니다."
                ),
            ),
        ],
        chunking=ChunkingConfig(chunk_size=120, overlap=10),
    )


def test_index_chunks_local_document_with_bounded_ranges() -> None:
    document = SourceDocument(
        document_id="guide",
        title="운영 안내",
        source_uri="local://guide",
        content=(
            "첫 번째 문장은 충분히 긴 설명을 제공합니다. "
            "두 번째 문장도 청크 경계를 검증하기 위해 이어집니다."
        ),
    )
    index = LocalRagIndex([document], chunking=ChunkingConfig(chunk_size=40, overlap=8))

    assert len(index.chunks) >= 2
    assert index.chunks[0].start_offset == 0
    assert all(0 < len(chunk.text) <= 40 for chunk in index.chunks)
    assert all(
        chunk.text == document.content[chunk.start_offset : chunk.end_offset]
        for chunk in index.chunks
    )
    assert [chunk.chunk_id for chunk in index.chunks] == [
        f"guide#{number}" for number in range(1, len(index.chunks) + 1)
    ]


def test_search_ranks_matching_local_evidence_and_exposes_source() -> None:
    hits = _index().search("배송 상태 확인", top_k=2)

    assert hits[0].chunk.document_id == "shipping"
    assert hits[0].score > hits[1].score
    assert hits[0].matched_terms == ("배송", "상태", "확인")
    assert hits[0].chunk.source_uri == "local://handbook/shipping"


def test_search_matches_korean_particles_and_conjugations_without_provider() -> None:
    hits = _index().search("배송 상태 확인", top_k=2)

    assert [(hit.chunk.document_id, hit.score) for hit in hits] == [("shipping", 4), ("returns", 2)]
    assert hits[1].matched_terms == ("배송", "상태")


def test_pipeline_returns_citations_for_mocked_generation() -> None:
    generator = RecordingGenerator()
    pipeline = RagPipeline(index=_index(), generator=generator)

    answer = pipeline.answer("배송 상태는 어떻게 확인하나요?", top_k=1)

    assert answer.no_answer is False
    assert answer.text == "배송 정책은 영업일 기준으로 적용됩니다."
    assert len(generator.calls) == 1
    assert generator.calls[0][0] == "배송 상태는 어떻게 확인하나요?"
    assert answer.citations[0].label == 1
    assert answer.citations[0].title == "배송 안내"
    assert answer.citations[0].source_uri == "local://handbook/shipping"


def test_pipeline_returns_no_answer_without_calling_generator() -> None:
    generator = RecordingGenerator()
    pipeline = RagPipeline(index=_index(), generator=generator)

    answer = pipeline.answer("주차장 할인 정책이 있나요?")

    assert answer.no_answer is True
    assert answer.text == RagPipeline.NO_ANSWER_TEXT
    assert answer.citations == ()
    assert generator.calls == []


def test_chunking_config_accepts_minimum_safe_size() -> None:
    assert ChunkingConfig(chunk_size=40, overlap=0).chunk_size == 40


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ChunkingConfig(chunk_size=39),
        lambda: ChunkingConfig(chunk_size=True),
        lambda: ChunkingConfig(chunk_size=40, overlap=40),
        lambda: LocalRagIndex([]),
        lambda: LocalRagIndex(
            [
                SourceDocument("same", "A", "local://a", "내용"),
                SourceDocument("same", "B", "local://b", "다른 내용"),
            ]
        ),
        lambda: _index().search("   "),
        lambda: _index().search("배송", top_k=0),
    ],
)
def test_rag_rejects_invalid_configuration(factory: Callable[[], object]) -> None:
    with pytest.raises(RagConfigurationError):
        factory()


def test_pipeline_rejects_blank_mock_answer() -> None:
    pipeline = RagPipeline(index=_index(), generator=RecordingGenerator(response="  "))

    with pytest.raises(RagConfigurationError, match="empty answer"):
        pipeline.answer("배송")
