from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ai_platform.rag import (
    ChunkingConfig,
    DenseCandidate,
    DocumentChunk,
    HybridRagIndex,
    HybridSearchConfig,
    LocalMarkdownLoader,
    LocalRagIndex,
    RagConfigurationError,
    RagPipeline,
    SearchHit,
    SourceDocument,
)


class RecordingDenseRanker:
    """로컬 청크 ID만 순위대로 반환하는 테스트 전용 dense Mock이다."""

    def __init__(self, candidate_ids: tuple[str, ...], *, ignore_top_k: bool = False) -> None:
        self.candidate_ids = candidate_ids
        self.ignore_top_k = ignore_top_k
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def rank(
        self, *, query: str, chunks: tuple[DocumentChunk, ...], top_k: int
    ) -> tuple[DenseCandidate, ...]:
        self.calls.append((query, tuple(chunk.chunk_id for chunk in chunks), top_k))
        candidate_ids = self.candidate_ids if self.ignore_top_k else self.candidate_ids[:top_k]
        return tuple(DenseCandidate(chunk_id) for chunk_id in candidate_ids)


class RecordingGenerator:
    """외부 제공자를 호출하지 않고 받은 검색 근거를 기록하는 Mock 생성기다."""

    def __init__(self, response: str = "배송 정책은 영업일 기준으로 적용됩니다.") -> None:
        self.response = response
        self.calls: list[tuple[str, tuple[SearchHit, ...]]] = []

    def generate(self, *, query: str, contexts: tuple[SearchHit, ...]) -> str:
        self.calls.append((query, contexts))
        return self.response


def test_markdown_loader_cleans_local_content_and_derives_safe_metadata(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    path = root / "guides" / "shipping policy.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\ufeff# 배송   안내 #\r\n\r\n배송\t상태는 주문 번호로 확인합니다.\r\n\r\n\r\n",
        encoding="utf-8",
    )

    document = LocalMarkdownLoader(root=root).load(Path("guides/shipping policy.md"))

    assert document.document_id == "local:guides/shipping policy.md"
    assert document.title == "배송 안내"
    assert document.source_uri == "local://volume05/guides/shipping%20policy.md"
    assert document.content == "# 배송 안내 #\n\n배송 상태는 주문 번호로 확인합니다."


def test_markdown_loader_uses_clean_filename_when_document_has_no_title(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "return_policy.markdown").write_text("반품 조건입니다.", encoding="utf-8")

    document = LocalMarkdownLoader(root=root).load(Path("return_policy.markdown"))

    assert document.title == "return policy"
    assert document.content == "반품 조건입니다."


def test_markdown_loader_loads_explicit_documents_in_deterministic_order(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    nested = root / "guides"
    nested.mkdir(parents=True)
    (root / "shipping.md").write_text("# 배송\n배송 상태를 확인합니다.", encoding="utf-8")
    (nested / "returns.md").write_text("# 반품\n반품을 접수합니다.", encoding="utf-8")

    documents = LocalMarkdownLoader(root=root).load_many(
        (Path("shipping.md"), Path("guides/returns.md"))
    )

    assert [document.document_id for document in documents] == [
        "local:guides/returns.md",
        "local:shipping.md",
    ]
    assert [document.title for document in documents] == ["반품", "배송"]


@pytest.mark.parametrize(
    "paths, message",
    [
        ((), "at least one Markdown path"),
        ((Path("guide.md"), Path("folder/../guide.md")), "must not resolve"),
    ],
)
def test_markdown_loader_rejects_empty_or_duplicate_document_batch(
    tmp_path: Path, paths: tuple[Path, ...], message: str
) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "guide.md").write_text("# 안내\n안전한 문서입니다.", encoding="utf-8")

    with pytest.raises(RagConfigurationError, match=message):
        LocalMarkdownLoader(root=root).load_many(paths)


@pytest.mark.parametrize(
    "relative_path, content, message",
    [
        (Path("../outside.md"), "outside", "stay within root"),
        (Path("notes.txt"), "not Markdown", "only Markdown"),
        (Path("empty.md"), " \r\n\t ", "no usable content"),
        (Path("unsafe.md"), "safe\x00unsafe", "NUL"),
    ],
)
def test_markdown_loader_rejects_unsafe_or_unusable_input(
    tmp_path: Path, relative_path: Path, content: str, message: str
) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    if relative_path.parts[0] != "..":
        (root / relative_path).write_text(content, encoding="utf-8")

    with pytest.raises(RagConfigurationError, match=message):
        LocalMarkdownLoader(root=root).load(relative_path)


def test_markdown_loader_rejects_non_utf8_file_and_invalid_root(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "legacy.md").write_bytes(b"\xff\xfe")

    with pytest.raises(RagConfigurationError, match="UTF-8"):
        LocalMarkdownLoader(root=root).load(Path("legacy.md"))
    with pytest.raises(RagConfigurationError, match="existing directory"):
        LocalMarkdownLoader(root=tmp_path / "missing")


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


def test_hybrid_search_fuses_sparse_and_mock_dense_candidates_with_rrf() -> None:
    ranker = RecordingDenseRanker(("returns#1",))
    index = HybridRagIndex(
        sparse_index=_index(),
        dense_ranker=ranker,
        config=HybridSearchConfig(
            sparse_candidate_count=2, dense_candidate_count=2, reciprocal_rank_k=10
        ),
    )

    hits = index.search("배송 상태", top_k=2)

    assert [hit.chunk.document_id for hit in hits] == ["returns", "shipping"]
    assert hits[0].matched_terms == ("배송", "상태")
    assert hits[0].score == pytest.approx(1 / 11 + 1 / 12)
    assert ranker.calls == [("배송 상태", ("shipping#1", "returns#1"), 2)]


def test_hybrid_search_can_use_mock_dense_evidence_without_sparse_term_overlap() -> None:
    ranker = RecordingDenseRanker(("shipping#1",))
    index = HybridRagIndex(sparse_index=_index(), dense_ranker=ranker)
    generator = RecordingGenerator(response="도착 예정 정보는 배송 안내를 확인하세요.")

    answer = RagPipeline(index=index, generator=generator).answer("언제 도착해요?", top_k=1)

    assert answer.no_answer is False
    assert answer.citations[0].chunk_id == "shipping#1"
    assert generator.calls[0][1][0].matched_terms == ()


@pytest.mark.parametrize(
    "candidate_ids, message",
    [
        (("unknown#1",), "local index chunk"),
        (("shipping#1", "shipping#1"), "duplicate chunk IDs"),
    ],
)
def test_hybrid_search_rejects_untrusted_mock_dense_candidates(
    candidate_ids: tuple[str, ...], message: str
) -> None:
    index = HybridRagIndex(sparse_index=_index(), dense_ranker=RecordingDenseRanker(candidate_ids))

    with pytest.raises(RagConfigurationError, match=message):
        index.search("배송")


def test_hybrid_search_rejects_mock_dense_result_larger_than_requested() -> None:
    index = HybridRagIndex(
        sparse_index=_index(),
        dense_ranker=RecordingDenseRanker(("shipping#1", "returns#1"), ignore_top_k=True),
        config=HybridSearchConfig(dense_candidate_count=1),
    )

    with pytest.raises(RagConfigurationError, match="more candidates than requested"):
        index.search("배송")


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
        lambda: HybridSearchConfig(sparse_candidate_count=0),
        lambda: HybridSearchConfig(dense_candidate_count=True),
        lambda: HybridSearchConfig(reciprocal_rank_k=0),
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
