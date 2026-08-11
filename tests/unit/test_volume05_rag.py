from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ai_platform.rag import (
    ChunkingConfig,
    ConfidenceThresholdConfig,
    ConfidenceThresholdIndex,
    ContextBudgetConfig,
    ContextBudgetIndex,
    DenseCandidate,
    DocumentChunk,
    DocumentDiversityConfig,
    DocumentDiversityIndex,
    HybridRagIndex,
    HybridSearchConfig,
    LocalMarkdownLoader,
    LocalPdfLoader,
    LocalRagIndex,
    PdfLoadingConfig,
    QueryTransformationConfig,
    QueryTransformingIndex,
    RagConfigurationError,
    RagPipeline,
    RerankingConfig,
    RerankingIndex,
    RerankResult,
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


class RecordingPdfTextExtractor:
    """실제 PDF 엔진 없이 바이트와 페이지 출력 계약을 기록하는 Mock이다."""

    def __init__(self, pages: tuple[str, ...] | object) -> None:
        self.pages = pages
        self.calls: list[bytes] = []

    def extract_pages(self, *, pdf_bytes: bytes) -> tuple[str, ...]:
        self.calls.append(pdf_bytes)
        return self.pages  # type: ignore[return-value]


class RecordingGenerator:
    """외부 제공자를 호출하지 않고 받은 검색 근거를 기록하는 Mock 생성기다."""

    def __init__(self, response: str = "배송 정책은 영업일 기준으로 적용됩니다.") -> None:
        self.response = response
        self.calls: list[tuple[str, tuple[SearchHit, ...]]] = []

    def generate(self, *, query: str, contexts: tuple[SearchHit, ...]) -> str:
        self.calls.append((query, contexts))
        return self.response


class RecordingQueryTransformer:
    """질의 변형 호출을 기록하고 외부 모델 없이 고정 결과를 반환한다."""

    def __init__(self, queries: tuple[str, ...] | object) -> None:
        self.queries = queries
        self.calls: list[str] = []

    def transform(self, *, query: str) -> tuple[str, ...]:
        self.calls.append(query)
        return self.queries  # type: ignore[return-value]


class RecordingReranker:
    """후보·제한 인자를 기록하고 고정된 재순위 결과를 반환하는 로컬 Mock이다."""

    def __init__(self, results: tuple[RerankResult, ...] | object) -> None:
        self.results = results
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def rerank(
        self, *, query: str, candidates: tuple[SearchHit, ...], top_k: int
    ) -> tuple[RerankResult, ...]:
        self.calls.append((query, tuple(hit.chunk.chunk_id for hit in candidates), top_k))
        return self.results  # type: ignore[return-value]


class RecordingSearchIndex:
    """검색 후보와 요청 제한을 기록하는 로컬 인덱스 Mock이다."""

    def __init__(self, hits: tuple[SearchHit, ...] | object) -> None:
        self.hits = hits
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, *, top_k: int = 3) -> tuple[SearchHit, ...]:
        self.calls.append((query, top_k))
        return self.hits  # type: ignore[return-value]


def _hit(*, chunk_id: str, document_id: str, text: str, score: float = 1.0) -> SearchHit:
    return SearchHit(
        chunk=DocumentChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            title=f"{document_id} title",
            source_uri=f"local://{document_id}",
            text=text,
            start_offset=0,
            end_offset=len(text),
        ),
        score=score,
        matched_terms=("근거",),
    )


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


def test_pdf_loader_reads_mocked_local_pages_with_cleaned_citations(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    pdf_bytes = b"%PDF-1.7\n% local test fixture\n"
    (root / "guides").mkdir()
    (root / "guides" / "shipping policy.pdf").write_bytes(pdf_bytes)
    extractor = RecordingPdfTextExtractor(
        ("\ufeff배송\t안내\r\n\r\n\r\n영업일 기준 2일입니다.", "반품은 7일 안에 신청합니다.")
    )

    documents = LocalPdfLoader(root=root, extractor=extractor).load(
        Path("guides/shipping policy.pdf")
    )

    assert [document.document_id for document in documents] == [
        "local:guides/shipping policy.pdf#page=1",
        "local:guides/shipping policy.pdf#page=2",
    ]
    assert [document.title for document in documents] == [
        "shipping policy — page 1",
        "shipping policy — page 2",
    ]
    assert documents[0].source_uri == "local://volume05/guides/shipping%20policy.pdf#page=1"
    assert documents[0].content == "배송 안내\n\n영업일 기준 2일입니다."
    assert extractor.calls == [pdf_bytes]


@pytest.mark.parametrize(
    "relative_path, content, config, message",
    [
        (Path("notes.txt"), b"not a PDF", None, "only PDF"),
        (Path("broken.pdf"), b"not a PDF", None, "PDF header"),
        (Path("empty.pdf"), b"", None, "must not be empty"),
        (Path("large.pdf"), b"%PDF-1.7\nabc", PdfLoadingConfig(max_file_bytes=8), "size limit"),
        (Path("../outside.pdf"), b"", None, "stay within root"),
    ],
)
def test_pdf_loader_rejects_unsafe_or_invalid_local_files(
    tmp_path: Path,
    relative_path: Path,
    content: bytes,
    config: PdfLoadingConfig | None,
    message: str,
) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    if relative_path.parts[0] != "..":
        (root / relative_path).write_bytes(content)

    with pytest.raises(RagConfigurationError, match=message):
        LocalPdfLoader(
            root=root, extractor=RecordingPdfTextExtractor(("valid page",)), config=config
        ).load(relative_path)


@pytest.mark.parametrize(
    "pages, config, message",
    [
        ((), None, "returned no pages"),
        (["valid page"], None, "tuple of page strings"),
        ((" ",), None, "empty page"),
        ((42,), None, "page strings"),
        (("first", "second"), PdfLoadingConfig(max_pages=1), "more pages than configured"),
        (("too long",), PdfLoadingConfig(max_page_characters=7), "character limit"),
    ],
)
def test_pdf_loader_rejects_untrusted_mock_extractor_output(
    tmp_path: Path,
    pages: tuple[str, ...] | list[str] | tuple[int, ...],
    config: PdfLoadingConfig | None,
    message: str,
) -> None:
    root = tmp_path / "knowledge"
    root.mkdir()
    (root / "guide.pdf").write_bytes(b"%PDF-1.7\nfixture")

    with pytest.raises(RagConfigurationError, match=message):
        LocalPdfLoader(root=root, extractor=RecordingPdfTextExtractor(pages), config=config).load(
            Path("guide.pdf")
        )


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


def test_reranking_index_rescores_only_limited_local_candidates_and_preserves_citations() -> None:
    reranker = RecordingReranker((RerankResult("shipping#1", 0.2), RerankResult("returns#1", 0.9)))
    index = RerankingIndex(
        index=_index(), reranker=reranker, config=RerankingConfig(candidate_count=2)
    )

    hits = index.search("배송 상태", top_k=2)

    assert [hit.chunk.chunk_id for hit in hits] == ["returns#1", "shipping#1"]
    assert [hit.score for hit in hits] == [0.9, 0.2]
    assert hits[0].matched_terms == ("배송", "상태")
    assert hits[0].citation(label=1).source_uri == "local://handbook/returns"
    assert reranker.calls == [("배송 상태", ("shipping#1", "returns#1"), 2)]


def test_reranking_index_applies_minimum_score_and_keeps_base_rank_for_ties() -> None:
    reranker = RecordingReranker((RerankResult("returns#1", 0.5), RerankResult("shipping#1", 0.5)))
    index = RerankingIndex(
        index=_index(),
        reranker=reranker,
        config=RerankingConfig(candidate_count=2, minimum_relevance_score=0.5),
    )

    hits = index.search("배송 상태", top_k=2)

    assert [hit.chunk.chunk_id for hit in hits] == ["shipping#1", "returns#1"]


@pytest.mark.parametrize(
    "results, message",
    [
        ([RerankResult("shipping#1", 0.8)], "tuple of RerankResult"),
        ((RerankResult("unknown#1", 0.8),), "supplied candidate"),
        (
            (RerankResult("shipping#1", 0.8), RerankResult("shipping#1", 0.7)),
            "duplicate chunk IDs",
        ),
        (
            (
                RerankResult("shipping#1", 0.8),
                RerankResult("returns#1", 0.7),
                RerankResult("extra#1", 0.6),
            ),
            "more results than supplied",
        ),
    ],
)
def test_reranking_index_rejects_untrusted_mock_results(
    results: tuple[RerankResult, ...] | list[RerankResult], message: str
) -> None:
    index = RerankingIndex(index=_index(), reranker=RecordingReranker(results))

    with pytest.raises(RagConfigurationError, match=message):
        index.search("배송 상태")


@pytest.mark.parametrize("score", (-0.1, 1.1, float("nan"), float("inf"), True))
def test_rerank_result_rejects_scores_outside_the_normalized_contract(score: float | bool) -> None:
    with pytest.raises(RagConfigurationError, match="relevance_score"):
        RerankResult("shipping#1", score)


def test_context_budget_index_selects_whole_ranked_chunks_within_a_fixed_budget() -> None:
    source = RecordingSearchIndex(
        (
            _hit(chunk_id="first#1", document_id="first", text="a" * 40, score=0.9),
            _hit(chunk_id="second#1", document_id="second", text="b" * 30, score=0.8),
            _hit(chunk_id="third#1", document_id="third", text="c" * 20, score=0.7),
        )
    )
    index = ContextBudgetIndex(
        index=source,
        config=ContextBudgetConfig(candidate_count=3, max_context_characters=60),
    )

    hits = index.search("근거", top_k=3)

    assert [hit.chunk.chunk_id for hit in hits] == ["first#1", "third#1"]
    assert [hit.score for hit in hits] == [0.9, 0.7]
    assert sum(len(hit.chunk.text) for hit in hits) == 60
    assert hits[1].citation(label=2).source_uri == "local://third"
    assert source.calls == [("근거", 3)]


def test_context_budget_index_returns_no_answer_without_truncating_an_oversized_chunk() -> None:
    source = RecordingSearchIndex((_hit(chunk_id="large#1", document_id="large", text="a" * 61),))
    generator = RecordingGenerator()
    pipeline = RagPipeline(
        index=ContextBudgetIndex(
            index=source,
            config=ContextBudgetConfig(candidate_count=1, max_context_characters=60),
        ),
        generator=generator,
    )

    answer = pipeline.answer("근거")

    assert answer.no_answer is True
    assert answer.citations == ()
    assert generator.calls == []


def test_confidence_threshold_index_filters_normalized_evidence_and_preserves_citations() -> None:
    source = RecordingSearchIndex(
        (
            _hit(
                chunk_id="shipping#1", document_id="shipping", text="shipping evidence", score=0.95
            ),
            _hit(chunk_id="returns#1", document_id="returns", text="return evidence", score=0.8),
            _hit(
                chunk_id="exchange#1", document_id="exchange", text="exchange evidence", score=0.79
            ),
        )
    )
    index = ConfidenceThresholdIndex(
        index=source,
        config=ConfidenceThresholdConfig(candidate_count=3, minimum_confidence=0.8),
    )

    hits = index.search("근거", top_k=3)

    assert [hit.chunk.chunk_id for hit in hits] == ["shipping#1", "returns#1"]
    assert [hit.score for hit in hits] == [0.95, 0.8]
    assert hits[1].citation(label=2).source_uri == "local://returns"
    assert source.calls == [("근거", 3)]


def test_confidence_threshold_index_returns_no_answer_without_calling_generator() -> None:
    source = RecordingSearchIndex(
        (_hit(chunk_id="shipping#1", document_id="shipping", text="weak evidence", score=0.79),)
    )
    generator = RecordingGenerator()
    pipeline = RagPipeline(
        index=ConfidenceThresholdIndex(
            index=source,
            config=ConfidenceThresholdConfig(candidate_count=1, minimum_confidence=0.8),
        ),
        generator=generator,
    )

    answer = pipeline.answer("근거")

    assert answer.no_answer is True
    assert answer.citations == ()
    assert generator.calls == []


@pytest.mark.parametrize(
    "hits, config, message",
    [
        ([_hit(chunk_id="first#1", document_id="first", text="evidence")], None, "tuple"),
        (
            (
                _hit(chunk_id="same#1", document_id="first", text="first"),
                _hit(chunk_id="same#1", document_id="second", text="second"),
            ),
            None,
            "duplicate candidate",
        ),
        (
            (
                _hit(chunk_id="first#1", document_id="first", text="first"),
                _hit(chunk_id="second#1", document_id="second", text="second"),
            ),
            ConfidenceThresholdConfig(candidate_count=1),
            "more candidates than requested",
        ),
        (
            (_hit(chunk_id="first#1", document_id="first", text="first", score=1.1),),
            None,
            "confidence scores",
        ),
    ],
)
def test_confidence_threshold_index_rejects_untrusted_search_candidates(
    hits: tuple[SearchHit, ...] | list[SearchHit],
    config: ConfidenceThresholdConfig | None,
    message: str,
) -> None:
    index = ConfidenceThresholdIndex(index=RecordingSearchIndex(hits), config=config)

    with pytest.raises(RagConfigurationError, match=message):
        index.search("근거")


def test_document_diversity_index_limits_ranked_contexts_per_document_and_preserves_citations() -> (
    None
):
    source = RecordingSearchIndex(
        (
            _hit(chunk_id="shipping#1", document_id="shipping", text="first shipping", score=0.9),
            _hit(chunk_id="shipping#2", document_id="shipping", text="second shipping", score=0.8),
            _hit(chunk_id="returns#1", document_id="returns", text="return evidence", score=0.7),
        )
    )
    index = DocumentDiversityIndex(
        index=source,
        config=DocumentDiversityConfig(candidate_count=3, max_chunks_per_document=1),
    )

    hits = index.search("근거", top_k=2)

    assert [hit.chunk.chunk_id for hit in hits] == ["shipping#1", "returns#1"]
    assert [hit.score for hit in hits] == [0.9, 0.7]
    assert hits[1].citation(label=2).source_uri == "local://returns"
    assert source.calls == [("근거", 3)]


def test_document_diversity_index_allows_configured_multiple_chunks_without_reordering() -> None:
    source = RecordingSearchIndex(
        (
            _hit(chunk_id="shipping#1", document_id="shipping", text="first", score=0.9),
            _hit(chunk_id="shipping#2", document_id="shipping", text="second", score=0.8),
            _hit(chunk_id="returns#1", document_id="returns", text="return", score=0.7),
        )
    )
    index = DocumentDiversityIndex(
        index=source,
        config=DocumentDiversityConfig(candidate_count=3, max_chunks_per_document=2),
    )

    hits = index.search("근거", top_k=3)

    assert [hit.chunk.chunk_id for hit in hits] == ["shipping#1", "shipping#2", "returns#1"]


@pytest.mark.parametrize(
    "hits, config, message",
    [
        ([_hit(chunk_id="first#1", document_id="first", text="evidence")], None, "tuple"),
        (
            (
                _hit(chunk_id="same#1", document_id="first", text="first"),
                _hit(chunk_id="same#1", document_id="second", text="second"),
            ),
            None,
            "duplicate candidate",
        ),
        (
            (
                _hit(chunk_id="first#1", document_id="first", text="first"),
                _hit(chunk_id="second#1", document_id="second", text="second"),
            ),
            DocumentDiversityConfig(candidate_count=1),
            "more candidates than requested",
        ),
    ],
)
def test_document_diversity_index_rejects_untrusted_search_candidates(
    hits: tuple[SearchHit, ...] | list[SearchHit],
    config: DocumentDiversityConfig | None,
    message: str,
) -> None:
    index = DocumentDiversityIndex(index=RecordingSearchIndex(hits), config=config)

    with pytest.raises(RagConfigurationError, match=message):
        index.search("근거")


@pytest.mark.parametrize(
    "hits, config, message",
    [
        ([_hit(chunk_id="first#1", document_id="first", text="evidence")], None, "tuple"),
        (
            (
                _hit(chunk_id="same#1", document_id="first", text="first"),
                _hit(chunk_id="same#1", document_id="second", text="second"),
            ),
            None,
            "duplicate candidate",
        ),
        (
            (
                _hit(chunk_id="first#1", document_id="first", text="first"),
                _hit(chunk_id="second#1", document_id="second", text="second"),
            ),
            ContextBudgetConfig(candidate_count=1),
            "more candidates than requested",
        ),
    ],
)
def test_context_budget_index_rejects_untrusted_search_candidates(
    hits: tuple[SearchHit, ...] | list[SearchHit],
    config: ContextBudgetConfig | None,
    message: str,
) -> None:
    index = ContextBudgetIndex(index=RecordingSearchIndex(hits), config=config)

    with pytest.raises(RagConfigurationError, match=message):
        index.search("근거")


def test_query_transforming_index_fuses_original_and_mock_expansion_with_rrf() -> None:
    transformer = RecordingQueryTransformer(("배송 상태", "반품 신청"))
    index = QueryTransformingIndex(
        index=_index(),
        transformer=transformer,
        config=QueryTransformationConfig(max_queries=2, reciprocal_rank_k=10),
    )

    hits = index.search("배송 상태", top_k=2)

    assert [hit.chunk.document_id for hit in hits] == ["returns", "shipping"]
    assert [hit.score for hit in hits] == [
        pytest.approx(1 / 11 + 1 / 12),
        pytest.approx(1 / 11),
    ]
    assert hits[0].matched_terms == ("반품", "배송", "상태", "신청")
    assert transformer.calls == ["배송 상태"]


def test_query_transforming_index_preserves_original_user_question_for_generation() -> None:
    transformer = RecordingQueryTransformer(("언제 도착해요?", "배송"))
    generator = RecordingGenerator()
    pipeline = RagPipeline(
        index=QueryTransformingIndex(index=_index(), transformer=transformer), generator=generator
    )

    answer = pipeline.answer("언제 도착해요?", top_k=1)

    assert answer.no_answer is False
    assert answer.citations[0].chunk_id == "shipping#1"
    assert generator.calls[0][0] == "언제 도착해요?"


@pytest.mark.parametrize(
    "queries, message",
    [
        ((), "at least the original"),
        (("다른 질문",), "preserve the original"),
        (("배송", " 배송 "), "duplicate queries"),
        (("배송", ""), "non-empty string"),
        (("배송", "상태", "반품"), "more queries than configured"),
        (["배송"], "tuple of strings"),
    ],
)
def test_query_transforming_index_rejects_untrusted_transformer_output(
    queries: tuple[str, ...] | list[str], message: str
) -> None:
    index = QueryTransformingIndex(
        index=_index(),
        transformer=RecordingQueryTransformer(queries),
        config=QueryTransformationConfig(max_queries=2),
    )

    with pytest.raises(RagConfigurationError, match=message):
        index.search("배송")


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
        lambda: PdfLoadingConfig(max_file_bytes=0),
        lambda: PdfLoadingConfig(max_pages=True),
        lambda: PdfLoadingConfig(max_page_characters=500_001),
        lambda: QueryTransformationConfig(max_queries=0),
        lambda: QueryTransformationConfig(reciprocal_rank_k=False),
        lambda: RerankingConfig(candidate_count=0),
        lambda: RerankingConfig(minimum_relevance_score=1.1),
        lambda: ConfidenceThresholdConfig(candidate_count=0),
        lambda: ConfidenceThresholdConfig(minimum_confidence=float("nan")),
        lambda: ContextBudgetConfig(candidate_count=21),
        lambda: ContextBudgetConfig(max_context_characters=True),
        lambda: ContextBudgetConfig(max_context_characters=20_001),
        lambda: DocumentDiversityConfig(candidate_count=0),
        lambda: DocumentDiversityConfig(max_chunks_per_document=True),
        lambda: DocumentDiversityConfig(max_chunks_per_document=21),
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
