from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from types import ModuleType

import pytest

from ai_platform.rag import (
    FASTAPI_RAG_QUERY_PATH,
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
    InMemoryVectorStore,
    LocalMarkdownLoader,
    LocalPdfLoader,
    LocalRagApi,
    LocalRagIndex,
    LocalRetrievalEvaluationReportStore,
    LocalRetrievalEvaluationSetLoader,
    LocalRetrievalRegressionBaselineLoader,
    PdfLoadingConfig,
    QueryTransformationConfig,
    QueryTransformingIndex,
    RagConfigurationError,
    RagPipeline,
    RagQueryRequest,
    RerankingConfig,
    RerankingIndex,
    RerankResult,
    RetrievalEvaluationAuditMetadata,
    RetrievalEvaluationAuditRequirement,
    RetrievalEvaluationBaseline,
    RetrievalEvaluationBaselineCase,
    RetrievalEvaluationCase,
    RetrievalEvaluationConfig,
    RetrievalEvaluationReportFileConfig,
    RetrievalEvaluationSetLoadingConfig,
    RetrievalEvaluator,
    RetrievalRegressionBaselineAuditMetadata,
    RetrievalRegressionBaselineLoadingConfig,
    RetrievalRegressionChecker,
    RetrievalRegressionPolicy,
    SearchHit,
    SourceDocument,
    VectorRagIndex,
    VectorRagIndexConfig,
    VectorRecord,
    VectorSearchResult,
    create_fastapi_rag_app,
    retrieval_regression_baseline_content_id,
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


class RecordingEmbedder:
    """텍스트별 고정 벡터만 반환하는 로컬/Mock 임베딩 제공자다."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]] | object) -> None:
        self.vectors_by_text = vectors_by_text
        self.calls: list[tuple[str, ...]] = []

    def embed(self, *, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        self.calls.append(texts)
        if not isinstance(self.vectors_by_text, dict):
            return self.vectors_by_text  # type: ignore[return-value]
        return tuple(self.vectors_by_text[text] for text in texts)


class RecordingVectorStore:
    """원문 없이 VectorRecord와 검색 결과만 기록하는 주입 저장소 Mock이다."""

    def __init__(self, results: tuple[VectorSearchResult, ...] | object = ()) -> None:
        self.results = results
        self.replaced_records: list[tuple[VectorRecord, ...]] = []
        self.calls: list[tuple[tuple[float, ...], int]] = []

    def replace(self, *, records: tuple[VectorRecord, ...]) -> None:
        self.replaced_records.append(records)

    def search(
        self, *, query_vector: tuple[float, ...], top_k: int
    ) -> tuple[VectorSearchResult, ...]:
        self.calls.append((query_vector, top_k))
        return self.results  # type: ignore[return-value]


class RecordingJsonResponse:
    """FastAPI 어댑터가 반환할 상태 코드와 JSON 본문을 기록하는 로컬 응답 Mock이다."""

    def __init__(self, *, status_code: int, content: dict[str, object]) -> None:
        self.status_code = status_code
        self.content = content


class RecordingBody:
    """FastAPI의 필수 JSON 본문 마커를 기록하는 프레임워크 Mock이다."""

    def __init__(self, default: object) -> None:
        self.default = default


class RecordingFastApi:
    """서버·네트워크 없이 FastAPI 팩토리의 라우트 연결을 검증하는 프레임워크 Mock이다."""

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.routes: list[tuple[str, dict[str, object], Callable[..., object]]] = []
        self.exception_handlers: list[tuple[object, Callable[..., object]]] = []

    def post(
        self, path: str, **kwargs: object
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        def register(handler: Callable[..., object]) -> Callable[..., object]:
            self.routes.append((path, kwargs, handler))
            return handler

        return register

    def exception_handler(
        self, error_type: object
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        def register(handler: Callable[..., object]) -> Callable[..., object]:
            self.exception_handlers.append((error_type, handler))
            return handler

        return register


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


def _baseline_audit(
    baseline: RetrievalEvaluationBaseline | None = None,
    policy: RetrievalRegressionPolicy | None = None,
) -> RetrievalRegressionBaselineAuditMetadata:
    baseline = baseline or RetrievalEvaluationBaseline(
        top_k=1,
        cases=(RetrievalEvaluationBaselineCase("shipping", "배송", ("shipping#1",)),),
        recall_at_k=1.0,
        hit_rate=1.0,
        mean_reciprocal_rank=1.0,
    )
    policy = policy or RetrievalRegressionPolicy()
    return RetrievalRegressionBaselineAuditMetadata(
        baseline_id="volume05-retrieval-baseline-001",
        approval_reference="baseline-approval-001",
        content_id=retrieval_regression_baseline_content_id(baseline, policy),
        approved_on=date(2026, 8, 11),
        retained_until=date(2030, 1, 1),
    )


def _approved_audit() -> RetrievalEvaluationAuditMetadata:
    return RetrievalEvaluationAuditMetadata(
        record_id="volume05-fixed-report-001",
        comparison_target_id="volume05-retrieval-baseline-001",
        comparison_approval_reference="baseline-approval-001",
        comparison_content_id=_baseline_audit().content_id,
        approval_state="approved",
        retained_until=date(2030, 1, 1),
        approval_reference="local-approval-001",
        approved_on=date(2026, 8, 11),
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


def _vector_embedder(index: LocalRagIndex, *, query_vector: tuple[float, ...]) -> RecordingEmbedder:
    vectors_by_text = {
        index.chunks[0].text: (1.0, 0.0),
        index.chunks[1].text: (0.0, 1.0),
        "언제 도착하나요?": query_vector,
    }
    return RecordingEmbedder(vectors_by_text)


def test_vector_index_uses_injected_mock_embeddings_and_store_without_raw_text() -> None:
    source_index = _index()
    embedder = _vector_embedder(source_index, query_vector=(1.0, 0.0))
    store = RecordingVectorStore(
        (
            VectorSearchResult("shipping#1", 1.0),
            VectorSearchResult("returns#1", 0.5),
        )
    )
    index = VectorRagIndex(
        source_index=source_index,
        embedder=embedder,
        vector_store=store,
    )

    hits = index.search("언제 도착하나요?", top_k=2)

    assert [hit.chunk.chunk_id for hit in hits] == ["shipping#1", "returns#1"]
    assert [hit.score for hit in hits] == [1.0, 0.5]
    assert all(hit.matched_terms == () for hit in hits)
    assert hits[0].citation(label=1).source_uri == "local://handbook/shipping"
    assert embedder.calls == [
        tuple(chunk.text for chunk in source_index.chunks),
        ("언제 도착하나요?",),
    ]
    assert [record.chunk_id for record in store.replaced_records[0]] == ["shipping#1", "returns#1"]
    assert [record.values for record in store.replaced_records[0]] == [(1.0, 0.0), (0.0, 1.0)]
    assert store.calls == [((1.0, 0.0), 2)]


def test_in_memory_vector_store_ranks_normalized_cosine_similarity_deterministically() -> None:
    store = InMemoryVectorStore()
    store.replace(
        records=(
            VectorRecord("second", (0.0, 1.0)),
            VectorRecord("first", (1.0, 0.0)),
            VectorRecord("tie", (1.0, 0.0)),
        )
    )

    results = store.search(query_vector=(1.0, 0.0), top_k=3)

    assert [(result.chunk_id, result.similarity) for result in results] == [
        ("first", 1.0),
        ("tie", 1.0),
        ("second", 0.5),
    ]


@pytest.mark.parametrize(
    "vectors, message",
    [
        ([(1.0, 0.0), (0.0, 1.0)], "one tuple vector"),
        (((1.0, 0.0),), "one tuple vector per index text"),
        (((0.0, 0.0), (0.0, 1.0)), "must not be a zero vector"),
        (((1.0, 0.0), (0.0, float("nan"))), "must contain finite numbers"),
        (((1.0, 0.0), (0.0, 1.0, 2.0)), "same dimensions"),
    ],
)
def test_vector_index_rejects_untrusted_mock_embedding_output(
    vectors: object, message: str
) -> None:
    with pytest.raises(RagConfigurationError, match=message):
        VectorRagIndex(
            source_index=_index(),
            embedder=RecordingEmbedder(vectors),
            vector_store=InMemoryVectorStore(),
        )


@pytest.mark.parametrize(
    "results, message",
    [
        ([VectorSearchResult("shipping#1", 1.0)], "tuple of VectorSearchResult"),
        ((VectorSearchResult("unknown#1", 1.0),), "indexed local chunk"),
        (
            (VectorSearchResult("shipping#1", 1.0), VectorSearchResult("shipping#1", 0.9)),
            "duplicate chunk IDs",
        ),
        (
            (VectorSearchResult("shipping#1", 0.8), VectorSearchResult("returns#1", 0.9)),
            "sorted by descending similarity",
        ),
    ],
)
def test_vector_index_rejects_untrusted_store_results(results: object, message: str) -> None:
    source_index = _index()
    with pytest.raises(RagConfigurationError, match=message):
        VectorRagIndex(
            source_index=source_index,
            embedder=_vector_embedder(source_index, query_vector=(1.0, 0.0)),
            vector_store=RecordingVectorStore(results),
        ).search("언제 도착하나요?", top_k=2)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: VectorRecord("record", ()),
        lambda: VectorSearchResult("result", 1.1),
        lambda: VectorRagIndexConfig(max_embedding_dimensions=0),
        lambda: VectorRagIndexConfig(max_indexed_chunks=True),
        lambda: InMemoryVectorStore().replace(
            records=(VectorRecord("same", (1.0,)), VectorRecord("same", (1.0,)))
        ),
    ],
)
def test_vector_contract_rejects_invalid_records_configuration_and_store_state(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(RagConfigurationError):
        factory()


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


def test_local_rag_api_returns_stable_cited_json_for_mocked_generation() -> None:
    generator = RecordingGenerator(response="배송 안내를 확인하세요.")
    api = LocalRagApi(pipeline=RagPipeline(index=_index(), generator=generator))

    response = api.handle({"query": "배송 상태는 어떻게 확인하나요?", "top_k": 1})

    assert response.status_code == 200
    assert response.to_payload() == {
        "answer": "배송 안내를 확인하세요.",
        "no_answer": False,
        "citations": [
            {
                "label": 1,
                "chunk_id": "shipping#1",
                "title": "배송 안내",
                "source_uri": "local://handbook/shipping",
                "start_offset": 0,
                "end_offset": 54,
            }
        ],
    }
    assert [query for query, _ in generator.calls] == ["배송 상태는 어떻게 확인하나요?"]
    assert len(generator.calls[0][1]) == 1


def test_local_rag_api_preserves_no_answer_without_calling_mock_generator() -> None:
    generator = RecordingGenerator()
    api = LocalRagApi(pipeline=RagPipeline(index=_index(), generator=generator))

    response = api.handle({"query": "주차장 할인 정책이 있나요?"})

    assert response.status_code == 200
    assert response.to_payload() == {
        "answer": RagPipeline.NO_ANSWER_TEXT,
        "no_answer": True,
        "citations": [],
    }
    assert generator.calls == []


@pytest.mark.parametrize(
    "payload, message",
    [
        (None, "request payload must be an object"),
        ({}, "request payload must include query"),
        ({"query": " "}, "query must be a non-empty string"),
        ({"query": "배송", "top_k": True}, "top_k must be an integer between 1 and 20"),
        ({"query": "배송", "top_k": 21}, "top_k must be an integer between 1 and 20"),
        (
            {"query": "배송", "unknown": "value"},
            "request payload contains unsupported fields: unknown",
        ),
    ],
)
def test_local_rag_api_returns_public_400_for_invalid_payload(
    payload: object, message: str
) -> None:
    generator = RecordingGenerator()
    api = LocalRagApi(pipeline=RagPipeline(index=_index(), generator=generator))

    response = api.handle(payload)

    assert response.status_code == 400
    assert response.to_payload() == {"error": {"code": "invalid_request", "message": message}}
    assert generator.calls == []


def test_local_rag_api_accepts_a_prevalidated_request_object() -> None:
    generator = RecordingGenerator()
    api = LocalRagApi(pipeline=RagPipeline(index=_index(), generator=generator))

    response = api.answer(RagQueryRequest(query="배송", top_k=1))

    assert response.no_answer is False
    assert response.citations[0].chunk_id == "shipping#1"
    assert generator.calls[0][0] == "배송"


def test_fastapi_adapter_wires_mocked_pipeline_to_stable_json_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fastapi_module = ModuleType("fastapi")
    fastapi_module.FastAPI = RecordingFastApi  # type: ignore[attr-defined]
    fastapi_module.Body = RecordingBody  # type: ignore[attr-defined]
    responses_module = ModuleType("fastapi.responses")
    responses_module.JSONResponse = RecordingJsonResponse  # type: ignore[attr-defined]
    exceptions_module = ModuleType("fastapi.exceptions")
    request_validation_error = type("RequestValidationError", (Exception,), {})
    exceptions_module.RequestValidationError = request_validation_error  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fastapi", fastapi_module)
    monkeypatch.setitem(sys.modules, "fastapi.responses", responses_module)
    monkeypatch.setitem(sys.modules, "fastapi.exceptions", exceptions_module)
    generator = RecordingGenerator(response="배송 안내를 확인하세요.")

    app = create_fastapi_rag_app(pipeline=RagPipeline(index=_index(), generator=generator))

    assert isinstance(app, RecordingFastApi)
    assert app.kwargs == {
        "title": "Volume 05 Local RAG API",
        "version": "1.0.0",
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }
    assert len(app.routes) == 1
    path, route_kwargs, handler = app.routes[0]
    assert path == FASTAPI_RAG_QUERY_PATH
    assert route_kwargs == {"response_model": None}
    assert handler.__defaults__ is not None
    assert len(handler.__defaults__) == 1
    required_body = handler.__defaults__[0]
    assert isinstance(required_body, RecordingBody)
    assert required_body.default is Ellipsis
    response = handler({"query": "배송 상태는 어떻게 확인하나요?", "top_k": 1})
    assert isinstance(response, RecordingJsonResponse)
    assert response.status_code == 200
    assert response.content["no_answer"] is False
    assert response.content["citations"] == [
        {
            "label": 1,
            "chunk_id": "shipping#1",
            "title": "배송 안내",
            "source_uri": "local://handbook/shipping",
            "start_offset": 0,
            "end_offset": 54,
        }
    ]
    invalid_response = handler({"query": "배송", "unsupported": True})
    assert isinstance(invalid_response, RecordingJsonResponse)
    assert invalid_response.status_code == 400
    assert invalid_response.content == {
        "error": {
            "code": "invalid_request",
            "message": "request payload contains unsupported fields: unsupported",
        }
    }
    assert len(app.exception_handlers) == 1
    registered_error, invalid_json_handler = app.exception_handlers[0]
    assert registered_error is request_validation_error
    json_error_response = asyncio.run(invalid_json_handler(object(), request_validation_error()))
    assert isinstance(json_error_response, RecordingJsonResponse)
    assert json_error_response.status_code == 400
    assert json_error_response.content == {
        "error": {"code": "invalid_request", "message": "request payload must be valid JSON"}
    }


def test_fastapi_adapter_explains_missing_optional_framework(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_fastapi(_: str) -> object:
        raise ModuleNotFoundError("No module named 'fastapi'", name="fastapi")

    monkeypatch.setattr("ai_platform.rag.fastapi_adapter.import_module", missing_fastapi)

    with pytest.raises(RagConfigurationError, match="FastAPI is required"):
        create_fastapi_rag_app(pipeline=RagPipeline(index=_index(), generator=RecordingGenerator()))


def test_retrieval_evaluator_reports_deterministic_fixed_query_metrics_without_generation() -> None:
    source = RecordingSearchIndex(
        (
            _hit(chunk_id="shipping#1", document_id="shipping", text="shipping evidence"),
            _hit(chunk_id="returns#1", document_id="returns", text="return evidence"),
        )
    )
    evaluator = RetrievalEvaluator(index=source, config=RetrievalEvaluationConfig(top_k=2))

    report = evaluator.evaluate(
        (
            RetrievalEvaluationCase(
                case_id="shipping", query="배송", expected_chunk_ids=("shipping#1", "exchange#1")
            ),
            RetrievalEvaluationCase(
                case_id="exchange", query="교환", expected_chunk_ids=("exchange#1",)
            ),
        )
    )

    assert source.calls == [("배송", 2), ("교환", 2)]
    assert report.top_k == 2
    assert report.evaluated_cases == 2
    assert report.recall_at_k == pytest.approx(1 / 3)
    assert report.hit_rate == pytest.approx(0.5)
    assert report.mean_reciprocal_rank == pytest.approx(0.5)
    assert report.results[0].first_relevant_rank == 1
    assert report.results[0].recall_at_k == pytest.approx(0.5)
    assert report.results[0].reciprocal_rank == pytest.approx(1.0)
    assert report.results[1].passed is False
    assert report.results[1].first_relevant_rank is None
    assert report.results[1].recall_at_k == pytest.approx(0.0)
    assert report.results[1].reciprocal_rank == pytest.approx(0.0)
    assert report.to_payload() == {
        "top_k": 2,
        "evaluated_cases": 2,
        "recall_at_k": pytest.approx(1 / 3),
        "hit_rate": pytest.approx(0.5),
        "mean_reciprocal_rank": pytest.approx(0.5),
        "results": [
            {
                "case_id": "shipping",
                "expected_chunk_ids": ["shipping#1", "exchange#1"],
                "retrieved_chunk_ids": ["shipping#1", "returns#1"],
                "first_relevant_rank": 1,
                "passed": True,
                "recall_at_k": pytest.approx(0.5),
                "reciprocal_rank": pytest.approx(1.0),
            },
            {
                "case_id": "exchange",
                "expected_chunk_ids": ["exchange#1"],
                "retrieved_chunk_ids": ["shipping#1", "returns#1"],
                "first_relevant_rank": None,
                "passed": False,
                "recall_at_k": pytest.approx(0.0),
                "reciprocal_rank": pytest.approx(0.0),
            },
        ],
    }


@pytest.mark.parametrize(
    "cases, config, message",
    [
        ((), None, "at least one evaluation case"),
        (
            (
                RetrievalEvaluationCase("same", "배송", ("shipping#1",)),
                RetrievalEvaluationCase("same", "반품", ("returns#1",)),
            ),
            None,
            "case_id values must be unique",
        ),
        (("not a case",), None, "RetrievalEvaluationCase values"),
        (
            (
                RetrievalEvaluationCase("shipping", "배송", ("shipping#1",)),
                RetrievalEvaluationCase("returns", "반품", ("returns#1",)),
            ),
            RetrievalEvaluationConfig(max_cases=1),
            "more cases than configured",
        ),
    ],
)
def test_retrieval_evaluator_rejects_invalid_fixed_case_sets(
    cases: tuple[RetrievalEvaluationCase, ...] | tuple[str, ...],
    config: RetrievalEvaluationConfig | None,
    message: str,
) -> None:
    with pytest.raises(RagConfigurationError, match=message):
        RetrievalEvaluator(index=RecordingSearchIndex(()), config=config).evaluate(cases)


@pytest.mark.parametrize(
    "hits, config, message",
    [
        (
            [_hit(chunk_id="shipping#1", document_id="shipping", text="evidence")],
            RetrievalEvaluationConfig(top_k=1),
            "tuple",
        ),
        (
            (
                _hit(chunk_id="shipping#1", document_id="shipping", text="first"),
                _hit(chunk_id="shipping#1", document_id="shipping", text="second"),
            ),
            RetrievalEvaluationConfig(top_k=2),
            "duplicate hit",
        ),
        (
            (
                _hit(chunk_id="shipping#1", document_id="shipping", text="first"),
                _hit(chunk_id="returns#1", document_id="returns", text="second"),
            ),
            RetrievalEvaluationConfig(top_k=1),
            "more hits than requested",
        ),
    ],
)
def test_retrieval_evaluator_rejects_untrusted_search_results(
    hits: tuple[SearchHit, ...] | list[SearchHit],
    config: RetrievalEvaluationConfig,
    message: str,
) -> None:
    with pytest.raises(RagConfigurationError, match=message):
        RetrievalEvaluator(index=RecordingSearchIndex(hits), config=config).evaluate(
            (RetrievalEvaluationCase("shipping", "배송", ("shipping#1",)),)
        )


def test_local_evaluation_set_loader_reads_explicit_utf8_json_cases_in_file_order(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evaluation"
    root.mkdir()
    (root / "fixed-cases.json").write_text(
        """{
  "cases": [
    {
      "case_id": "delivery",
      "query": "배송은 언제 도착하나요?",
      "expected_chunk_ids": ["shipping#1"]
    },
    {
      "case_id": "return",
      "query": "반품은 어떻게 하나요?",
      "expected_chunk_ids": ["returns#1", "returns#2"]
    }
  ]
}""",
        encoding="utf-8",
    )

    cases = LocalRetrievalEvaluationSetLoader(root=root).load(Path("fixed-cases.json"))

    assert cases == (
        RetrievalEvaluationCase("delivery", "배송은 언제 도착하나요?", ("shipping#1",)),
        RetrievalEvaluationCase("return", "반품은 어떻게 하나요?", ("returns#1", "returns#2")),
    )


@pytest.mark.parametrize(
    "relative_path, content, config, message",
    [
        (Path("notes.txt"), b"{}", None, "only JSON evaluation set files"),
        (Path("../outside.json"), b"", None, "must stay within root"),
        (Path("empty.json"), b"", None, "must not be empty"),
        (
            Path("large.json"),
            b'{"cases":[]}',
            RetrievalEvaluationSetLoadingConfig(max_file_bytes=1),
            "size limit",
        ),
        (Path("legacy.json"), b"\xff", None, "UTF-8"),
        (Path("malformed.json"), b"{", None, "valid JSON"),
        (
            Path("duplicate-key.json"),
            b'{"cases":[],"cases":[]}',
            None,
            "valid JSON",
        ),
    ],
)
def test_local_evaluation_set_loader_rejects_unsafe_or_invalid_files(
    tmp_path: Path,
    relative_path: Path,
    content: bytes,
    config: RetrievalEvaluationSetLoadingConfig | None,
    message: str,
) -> None:
    root = tmp_path / "evaluation"
    root.mkdir()
    if relative_path.parts[0] != "..":
        (root / relative_path).write_bytes(content)

    with pytest.raises(RagConfigurationError, match=message):
        LocalRetrievalEvaluationSetLoader(root=root, config=config).load(relative_path)


@pytest.mark.parametrize(
    "content, message",
    [
        (b"[]", "root must be an object"),
        (b'{"unexpected":[]}', "root must contain only cases"),
        (b'{"cases":{}}', "cases must be an array"),
        (b'{"cases":[]}', "at least one case"),
        (b'{"cases":["not an object"]}', "cases must be objects"),
        (
            b'{"cases":[{"case_id":"delivery","query":"delivery","expected_chunk_ids":[],"extra":1}]}',
            "must contain only case_id",
        ),
        (
            b'{"cases":[{"case_id":1,"query":"delivery","expected_chunk_ids":[]}]}',
            "case_id and query must be strings",
        ),
        (
            b'{"cases":[{"case_id":"delivery","query":"delivery","expected_chunk_ids":"shipping#1"}]}',
            "expected_chunk_ids must be an array",
        ),
        (
            b'{"cases":[{"case_id":"delivery","query":"delivery","expected_chunk_ids":[1]}]}',
            "expected_chunk_ids must contain strings",
        ),
    ],
)
def test_local_evaluation_set_loader_rejects_invalid_json_schema(
    tmp_path: Path, content: bytes, message: str
) -> None:
    root = tmp_path / "evaluation"
    root.mkdir()
    (root / "fixed-cases.json").write_bytes(content)

    with pytest.raises(RagConfigurationError, match=message):
        LocalRetrievalEvaluationSetLoader(root=root).load(Path("fixed-cases.json"))


def test_local_evaluation_set_loader_rejects_duplicate_or_excess_cases(tmp_path: Path) -> None:
    root = tmp_path / "evaluation"
    root.mkdir()
    (root / "duplicate-cases.json").write_text(
        """{
  "cases": [
    {"case_id":"same","query":"배송","expected_chunk_ids":["shipping#1"]},
    {"case_id":"same","query":"반품","expected_chunk_ids":["returns#1"]}
  ]
}""",
        encoding="utf-8",
    )
    (root / "two-cases.json").write_text(
        """{
  "cases": [
    {"case_id":"shipping","query":"배송","expected_chunk_ids":["shipping#1"]},
    {"case_id":"returns","query":"반품","expected_chunk_ids":["returns#1"]}
  ]
}""",
        encoding="utf-8",
    )

    with pytest.raises(RagConfigurationError, match="case_id values must be unique"):
        LocalRetrievalEvaluationSetLoader(root=root).load(Path("duplicate-cases.json"))
    with pytest.raises(RagConfigurationError, match="more cases than configured"):
        LocalRetrievalEvaluationSetLoader(
            root=root, config=RetrievalEvaluationSetLoadingConfig(max_cases=1)
        ).load(Path("two-cases.json"))


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RetrievalEvaluationCase("", "배송", ("shipping#1",)),
        lambda: RetrievalEvaluationCase("shipping", " ", ("shipping#1",)),
        lambda: RetrievalEvaluationCase("shipping", "배송", ()),
        lambda: RetrievalEvaluationCase("shipping", "배송", ("shipping#1", "shipping#1")),
        lambda: RetrievalEvaluationConfig(top_k=0),
        lambda: RetrievalEvaluationConfig(max_cases=True),
        lambda: RetrievalEvaluationSetLoadingConfig(max_file_bytes=0),
        lambda: RetrievalEvaluationSetLoadingConfig(max_cases=True),
        lambda: RetrievalRegressionBaselineLoadingConfig(max_file_bytes=0),
        lambda: RetrievalRegressionBaselineLoadingConfig(max_cases=True),
    ],
)
def test_retrieval_evaluation_rejects_invalid_contract_values(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(RagConfigurationError):
        factory()


def test_local_regression_baseline_loader_reads_explicit_baseline_and_policy(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evaluation"
    root.mkdir()
    (root / "baseline.json").write_text(
        """{
  "baseline": {
    "top_k": 1,
    "cases": [
      {"case_id":"shipping","query":"배송","expected_chunk_ids":["shipping#1"]}
    ],
    "recall_at_k": 1.0,
    "hit_rate": 1.0,
    "mean_reciprocal_rank": 1.0
  },
  "policy": {
    "maximum_recall_at_k_drop": 0.1,
    "maximum_hit_rate_drop": 0.2,
    "maximum_mean_reciprocal_rank_drop": 0.3
  },
  "audit": {
    "baseline_id": "volume05-retrieval-baseline-001",
    "approval_reference": "baseline-approval-001",
    "content_id": "sha256:1c14cbfc8593f1b10a0863e38c5f57dee2ddb24d3b900457ae88bae2239ae921",
    "approved_on": "2026-08-11",
    "retained_until": "2030-01-01"
  }
}""",
        encoding="utf-8",
    )

    loaded = LocalRetrievalRegressionBaselineLoader(root=root).load(Path("baseline.json"))
    report = RetrievalEvaluator(
        index=RecordingSearchIndex(
            (_hit(chunk_id="shipping#1", document_id="shipping", text="shipping evidence"),)
        ),
        config=RetrievalEvaluationConfig(top_k=1),
    ).evaluate((RetrievalEvaluationCase("shipping", "배송", ("shipping#1",)),))

    assert loaded.baseline.cases == (
        RetrievalEvaluationBaselineCase("shipping", "배송", ("shipping#1",)),
    )
    assert loaded.policy.maximum_recall_at_k_drop == 0.1
    assert loaded.policy.maximum_hit_rate_drop == 0.2
    assert loaded.policy.maximum_mean_reciprocal_rank_drop == 0.3
    assert loaded.audit == _baseline_audit(loaded.baseline, loaded.policy)
    assert (
        RetrievalRegressionChecker(baseline=loaded.baseline, policy=loaded.policy)
        .evaluate(report)
        .passed
        is True
    )


def test_local_regression_baseline_loader_rejects_content_changed_without_new_content_id(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evaluation"
    root.mkdir()
    (root / "baseline.json").write_text(
        """{
  "baseline": {
    "top_k": 1,
    "cases": [{"case_id":"shipping","query":"배송","expected_chunk_ids":["shipping#1"]}],
    "recall_at_k": 1.0,
    "hit_rate": 0.9,
    "mean_reciprocal_rank": 1.0
  },
  "policy": {
    "maximum_recall_at_k_drop": 0.1,
    "maximum_hit_rate_drop": 0.2,
    "maximum_mean_reciprocal_rank_drop": 0.3
  },
  "audit": {
    "baseline_id": "volume05-retrieval-baseline-001",
    "approval_reference": "baseline-approval-001",
    "content_id": "sha256:1c14cbfc8593f1b10a0863e38c5f57dee2ddb24d3b900457ae88bae2239ae921",
    "approved_on": "2026-08-11",
    "retained_until": "2030-01-01"
  }
}""",
        encoding="utf-8",
    )

    with pytest.raises(
        RagConfigurationError, match="content_id must match baseline and policy content"
    ):
        LocalRetrievalRegressionBaselineLoader(root=root).load(Path("baseline.json"))


@pytest.mark.parametrize(
    "relative_path, content, config, message",
    [
        (Path("notes.txt"), b"{}", None, "only JSON regression baseline files"),
        (Path("../outside.json"), b"", None, "must stay within root"),
        (Path("empty.json"), b"", None, "must not be empty"),
        (
            Path("large.json"),
            b"{}",
            RetrievalRegressionBaselineLoadingConfig(max_file_bytes=1),
            "size limit",
        ),
        (Path("legacy.json"), b"\xff", None, "UTF-8"),
        (Path("duplicate.json"), b'{"baseline":{},"baseline":{},"policy":{}}', None, "valid JSON"),
    ],
)
def test_local_regression_baseline_loader_rejects_unsafe_or_invalid_files(
    tmp_path: Path,
    relative_path: Path,
    content: bytes,
    config: RetrievalRegressionBaselineLoadingConfig | None,
    message: str,
) -> None:
    root = tmp_path / "evaluation"
    root.mkdir()
    if relative_path.parts[0] != "..":
        (root / relative_path).write_bytes(content)

    with pytest.raises(RagConfigurationError, match=message):
        LocalRetrievalRegressionBaselineLoader(root=root, config=config).load(relative_path)


@pytest.mark.parametrize(
    "content, config, message",
    [
        (b"[]", None, "root must be an object"),
        (b'{"baseline":{}}', None, "only baseline, policy, and audit"),
        (
            b'{"baseline":{"top_k":1,"cases":[],"recall_at_k":1.0,"hit_rate":1.0,"mean_reciprocal_rank":1.0},"policy":{"maximum_recall_at_k_drop":0.0,"maximum_hit_rate_drop":0.0,"maximum_mean_reciprocal_rank_drop":0.0}}',
            None,
            "cases must be a non-empty array",
        ),
        (
            b'{"baseline":{"top_k":1,"cases":[{"case_id":"shipping","expected_chunk_ids":["shipping#1"]}],"recall_at_k":1.0,"hit_rate":1.0,"mean_reciprocal_rank":1.0},"policy":{"maximum_recall_at_k_drop":0.0,"maximum_hit_rate_drop":0.0,"maximum_mean_reciprocal_rank_drop":0.0}}',
            None,
            "cases must contain only",
        ),
        (
            b'{"baseline":{"top_k":1,"cases":[{"case_id":"shipping","query":"shipping","expected_chunk_ids":["shipping#1"]}],"recall_at_k":1.0,"hit_rate":1.0,"mean_reciprocal_rank":1.0},"policy":{"maximum_recall_at_k_drop":1.1,"maximum_hit_rate_drop":0.0,"maximum_mean_reciprocal_rank_drop":0.0}}',
            None,
            "maximum_recall_at_k_drop",
        ),
        (
            b'{"baseline":{"top_k":1,"cases":[{"case_id":"shipping","query":"shipping","expected_chunk_ids":["shipping#1"]},{"case_id":"returns","query":"returns","expected_chunk_ids":["returns#1"]}],"recall_at_k":1.0,"hit_rate":1.0,"mean_reciprocal_rank":1.0},"policy":{"maximum_recall_at_k_drop":0.0,"maximum_hit_rate_drop":0.0,"maximum_mean_reciprocal_rank_drop":0.0}}',
            RetrievalRegressionBaselineLoadingConfig(max_cases=1),
            "more cases than configured",
        ),
    ],
)
def test_local_regression_baseline_loader_rejects_invalid_json_schema(
    tmp_path: Path,
    content: bytes,
    config: RetrievalRegressionBaselineLoadingConfig | None,
    message: str,
) -> None:
    root = tmp_path / "evaluation"
    root.mkdir()
    (root / "baseline.json").write_bytes(content)

    with pytest.raises(RagConfigurationError, match=message):
        LocalRetrievalRegressionBaselineLoader(root=root, config=config).load(Path("baseline.json"))


def test_retrieval_regression_checker_compares_compatible_reports_with_metric_budgets() -> None:
    cases = (
        RetrievalEvaluationCase("shipping", "배송", ("shipping#1",)),
        RetrievalEvaluationCase("returns", "반품", ("returns#1",)),
    )
    baseline_report = RetrievalEvaluator(
        index=RecordingSearchIndex(
            (
                _hit(chunk_id="shipping#1", document_id="shipping", text="shipping evidence"),
                _hit(chunk_id="returns#1", document_id="returns", text="return evidence"),
            )
        ),
        config=RetrievalEvaluationConfig(top_k=2),
    ).evaluate(cases)
    current_report = RetrievalEvaluator(
        index=RecordingSearchIndex(
            (_hit(chunk_id="shipping#1", document_id="shipping", text="shipping evidence"),)
        ),
        config=RetrievalEvaluationConfig(top_k=2),
    ).evaluate(cases)

    baseline = RetrievalEvaluationBaseline.from_report(baseline_report)
    decision = RetrievalRegressionChecker(
        baseline=baseline,
        policy=RetrievalRegressionPolicy(
            maximum_recall_at_k_drop=0.5,
            maximum_hit_rate_drop=0.5,
            maximum_mean_reciprocal_rank_drop=0.25,
        ),
    ).evaluate(current_report)

    assert baseline.to_payload() == {
        "top_k": 2,
        "cases": [
            {"case_id": "shipping", "expected_chunk_ids": ["shipping#1"]},
            {"case_id": "returns", "expected_chunk_ids": ["returns#1"]},
        ],
        "recall_at_k": 1.0,
        "hit_rate": 1.0,
        "mean_reciprocal_rank": 0.75,
    }
    assert decision.passed is True
    assert decision.to_payload() == {
        "top_k": 2,
        "evaluated_cases": 2,
        "passed": True,
        "metrics": [
            {
                "name": "recall_at_k",
                "baseline_score": 1.0,
                "current_score": 0.5,
                "drop": 0.5,
                "maximum_drop": 0.5,
                "passed": True,
            },
            {
                "name": "hit_rate",
                "baseline_score": 1.0,
                "current_score": 0.5,
                "drop": 0.5,
                "maximum_drop": 0.5,
                "passed": True,
            },
            {
                "name": "mean_reciprocal_rank",
                "baseline_score": 0.75,
                "current_score": 0.5,
                "drop": 0.25,
                "maximum_drop": 0.25,
                "passed": True,
            },
        ],
    }


def test_retrieval_regression_checker_reports_failure_without_hiding_metric_values() -> None:
    cases = (RetrievalEvaluationCase("shipping", "배송", ("shipping#1",)),)
    baseline_report = RetrievalEvaluator(
        index=RecordingSearchIndex(
            (_hit(chunk_id="shipping#1", document_id="shipping", text="shipping evidence"),)
        ),
        config=RetrievalEvaluationConfig(top_k=1),
    ).evaluate(cases)
    current_report = RetrievalEvaluator(
        index=RecordingSearchIndex(()), config=RetrievalEvaluationConfig(top_k=1)
    ).evaluate(cases)

    decision = RetrievalRegressionChecker(
        baseline=RetrievalEvaluationBaseline.from_report(baseline_report)
    ).evaluate(current_report)

    assert decision.passed is False
    assert [(metric.name, metric.drop, metric.passed) for metric in decision.metrics] == [
        ("recall_at_k", 1.0, False),
        ("hit_rate", 1.0, False),
        ("mean_reciprocal_rank", 1.0, False),
    ]


@pytest.mark.parametrize(
    "baseline_top_k, current_case, message",
    [
        (2, RetrievalEvaluationCase("shipping", "배송", ("shipping#1",)), "top_k must match"),
        (
            1,
            RetrievalEvaluationCase("shipping", "다른 배송 질문", ("shipping#1",)),
            "cases must match",
        ),
        (
            1,
            RetrievalEvaluationCase("shipping", "배송", ("different#1",)),
            "cases must match",
        ),
    ],
)
def test_retrieval_regression_checker_rejects_incompatible_baseline_comparisons(
    baseline_top_k: int, current_case: RetrievalEvaluationCase, message: str
) -> None:
    baseline_cases = (RetrievalEvaluationCase("shipping", "배송", ("shipping#1",)),)
    baseline_report = RetrievalEvaluator(
        index=RecordingSearchIndex(
            (_hit(chunk_id="shipping#1", document_id="shipping", text="shipping evidence"),)
        ),
        config=RetrievalEvaluationConfig(top_k=baseline_top_k),
    ).evaluate(baseline_cases)
    current_report = RetrievalEvaluator(
        index=RecordingSearchIndex(
            (_hit(chunk_id="shipping#1", document_id="shipping", text="shipping evidence"),)
        ),
        config=RetrievalEvaluationConfig(top_k=1),
    ).evaluate((current_case,))

    with pytest.raises(RagConfigurationError, match=message):
        RetrievalRegressionChecker(
            baseline=RetrievalEvaluationBaseline.from_report(baseline_report)
        ).evaluate(current_report)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RetrievalEvaluationBaseline(
            top_k=True,
            cases=(RetrievalEvaluationBaselineCase("shipping", "배송", ("shipping#1",)),),
            recall_at_k=1.0,
            hit_rate=1.0,
            mean_reciprocal_rank=1.0,
        ),
        lambda: RetrievalEvaluationBaseline(
            top_k=1,
            cases=(RetrievalEvaluationBaselineCase("shipping", "배송", ("shipping#1",)),),
            recall_at_k=float("nan"),
            hit_rate=1.0,
            mean_reciprocal_rank=1.0,
        ),
        lambda: RetrievalEvaluationBaselineCase("shipping", "배송", ("shipping#1", "shipping#1")),
        lambda: RetrievalRegressionPolicy(maximum_hit_rate_drop=True),
        lambda: RetrievalRegressionPolicy(maximum_recall_at_k_drop=1.1),
    ],
)
def test_retrieval_regression_contract_rejects_invalid_baseline_and_policy_values(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(RagConfigurationError):
        factory()


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


def test_local_evaluation_report_store_round_trips_a_fixed_report_for_baseline_comparison(
    tmp_path: Path,
) -> None:
    report = RetrievalEvaluator(
        index=RecordingSearchIndex(
            (_hit(chunk_id="shipping#1", document_id="shipping", text="shipping evidence"),)
        ),
        config=RetrievalEvaluationConfig(top_k=1),
    ).evaluate((RetrievalEvaluationCase("shipping", "배송", ("shipping#1",)),))
    baseline = RetrievalEvaluationBaseline.from_report(report)
    audit = _approved_audit()
    store = LocalRetrievalEvaluationReportStore(root=tmp_path)

    stored_path = store.record(Path("fixed-report.json"), report, audit=audit)
    reloaded_record = store.load_record(Path("fixed-report.json"))

    assert stored_path == tmp_path / "fixed-report.json"
    assert store.load(Path("fixed-report.json")) == report
    assert reloaded_record.report == report
    assert reloaded_record.audit == audit
    assert '"query": "배송"' in stored_path.read_text(encoding="utf-8")
    assert (
        RetrievalRegressionChecker(baseline=baseline, baseline_audit=_baseline_audit())
        .evaluate_record(
            reloaded_record,
            audit_requirement=RetrievalEvaluationAuditRequirement(
                comparison_target_id="volume05-retrieval-baseline-001",
                comparison_approval_reference="baseline-approval-001",
                comparison_content_id=_baseline_audit().content_id,
                as_of_date=date(2026, 8, 11),
            ),
        )
        .passed
        is True
    )
    with pytest.raises(RagConfigurationError, match="must not overwrite"):
        store.record(Path("fixed-report.json"), report, audit=audit)


def test_audited_regression_comparison_rejects_pending_expired_or_retargeted_records(
    tmp_path: Path,
) -> None:
    report = RetrievalEvaluator(
        index=RecordingSearchIndex(
            (_hit(chunk_id="shipping#1", document_id="shipping", text="shipping evidence"),)
        ),
        config=RetrievalEvaluationConfig(top_k=1),
    ).evaluate((RetrievalEvaluationCase("shipping", "배송", ("shipping#1",)),))
    checker = RetrievalRegressionChecker(
        baseline=RetrievalEvaluationBaseline.from_report(report), baseline_audit=_baseline_audit()
    )
    store = LocalRetrievalEvaluationReportStore(root=tmp_path)
    pending_audit = RetrievalEvaluationAuditMetadata(
        record_id="pending-report",
        comparison_target_id="volume05-retrieval-baseline-001",
        comparison_approval_reference="baseline-approval-001",
        comparison_content_id=_baseline_audit().content_id,
        approval_state="pending",
        retained_until=date(2030, 1, 1),
    )
    store.record(Path("pending.json"), report, audit=pending_audit)
    pending_record = store.load_record(Path("pending.json"))

    with pytest.raises(RagConfigurationError, match="must be approved"):
        checker.evaluate_record(
            pending_record,
            audit_requirement=RetrievalEvaluationAuditRequirement(
                comparison_target_id="volume05-retrieval-baseline-001",
                comparison_approval_reference="baseline-approval-001",
                comparison_content_id=_baseline_audit().content_id,
                as_of_date=date(2026, 8, 11),
            ),
        )

    approved_record = type(pending_record)(
        report=report,
        audit=RetrievalEvaluationAuditMetadata(
            record_id="approved-report",
            comparison_target_id="volume05-retrieval-baseline-001",
            comparison_approval_reference="baseline-approval-001",
            comparison_content_id=_baseline_audit().content_id,
            approval_state="approved",
            retained_until=date(2026, 8, 11),
            approval_reference="local-approval-002",
            approved_on=date(2026, 8, 11),
        ),
    )
    with pytest.raises(RagConfigurationError, match="must match the requested target"):
        checker.evaluate_record(
            approved_record,
            audit_requirement=RetrievalEvaluationAuditRequirement(
                comparison_target_id="volume05-retrieval-baseline-002",
                comparison_approval_reference="baseline-approval-001",
                comparison_content_id=_baseline_audit().content_id,
                as_of_date=date(2026, 8, 11),
            ),
        )
    with pytest.raises(RagConfigurationError, match="approval_reference must match"):
        checker.evaluate_record(
            approved_record,
            audit_requirement=RetrievalEvaluationAuditRequirement(
                comparison_target_id="volume05-retrieval-baseline-001",
                comparison_approval_reference="different-baseline-approval",
                comparison_content_id=_baseline_audit().content_id,
                as_of_date=date(2026, 8, 11),
            ),
        )
    with pytest.raises(RagConfigurationError, match="comparison_content_id must match"):
        checker.evaluate_record(
            type(approved_record)(
                report=report,
                audit=RetrievalEvaluationAuditMetadata(
                    record_id="wrong-content-report",
                    comparison_target_id="volume05-retrieval-baseline-001",
                    comparison_approval_reference="baseline-approval-001",
                    comparison_content_id="sha256:0000000000000000000000000000000000000000000000000000000000000000",
                    approval_state="approved",
                    retained_until=date(2030, 1, 1),
                    approval_reference="local-approval-003",
                    approved_on=date(2026, 8, 11),
                ),
            ),
            audit_requirement=RetrievalEvaluationAuditRequirement(
                comparison_target_id="volume05-retrieval-baseline-001",
                comparison_approval_reference="baseline-approval-001",
                comparison_content_id=_baseline_audit().content_id,
                as_of_date=date(2026, 8, 11),
            ),
        )
    with pytest.raises(RagConfigurationError, match="retention has expired"):
        checker.evaluate_record(
            approved_record,
            audit_requirement=RetrievalEvaluationAuditRequirement(
                comparison_target_id="volume05-retrieval-baseline-001",
                comparison_approval_reference="baseline-approval-001",
                comparison_content_id=_baseline_audit().content_id,
                as_of_date=date(2026, 8, 12),
            ),
        )


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"approval_state": "unknown"}, "approval_state is not supported"),
        (
            {"approval_state": "approved"},
            "approved audit metadata requires approval details",
        ),
        (
            {
                "approval_state": "superseded",
                "approval_reference": "approval-1",
                "approved_on": date(2026, 8, 11),
            },
            "superseded audit metadata requires approval details",
        ),
        (
            {
                "approval_state": "approved",
                "approval_reference": "approval-1",
                "approved_on": date(2030, 1, 2),
                "retained_until": date(2030, 1, 1),
            },
            "approved_on must not be after retained_until",
        ),
        (
            {"approval_reference": "approval-1"},
            "pending audit metadata must not contain approval details",
        ),
    ],
)
def test_audit_metadata_rejects_invalid_lifecycle_combinations(
    kwargs: dict[str, object], message: str
) -> None:
    fields: dict[str, object] = {
        "record_id": "record-1",
        "comparison_target_id": "target-1",
        "comparison_approval_reference": "target-approval-1",
        "comparison_content_id": _baseline_audit().content_id,
        "approval_state": "pending",
        "retained_until": date(2030, 1, 1),
    }
    with pytest.raises(RagConfigurationError, match=message):
        RetrievalEvaluationAuditMetadata(**(fields | kwargs))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "relative_path, content, message",
    [
        (Path("../outside.json"), "", "must stay within root"),
        (Path("notes.txt"), "", "only JSON evaluation report files"),
        (Path("empty.json"), "", "must not be empty"),
        (Path("legacy.json"), "", "UTF-8"),
        (Path("duplicate.json"), '{"top_k":1,"top_k":1}', "valid JSON"),
        (
            Path("mismatched-count.json"),
            """{
  "top_k": 1,
  "evaluated_cases": 2,
  "recall_at_k": 1.0,
  "hit_rate": 1.0,
  "mean_reciprocal_rank": 1.0,
  "results": [{
    "case_id": "shipping",
    "query": "배송",
    "expected_chunk_ids": ["shipping#1"],
    "retrieved_chunk_ids": ["shipping#1"],
    "first_relevant_rank": 1,
    "passed": true,
    "recall_at_k": 1.0,
    "reciprocal_rank": 1.0
  }]
}""",
            "evaluated_cases must match results",
        ),
        (
            Path("forged-metric.json"),
            """{
  "top_k": 1,
  "evaluated_cases": 1,
  "recall_at_k": 1.0,
  "hit_rate": 1.0,
  "mean_reciprocal_rank": 1.0,
  "results": [{
    "case_id": "shipping",
    "query": "배송",
    "expected_chunk_ids": ["shipping#1"],
    "retrieved_chunk_ids": [],
    "first_relevant_rank": null,
    "passed": false,
    "recall_at_k": 1.0,
    "reciprocal_rank": 0.0
  }]
}""",
            "recall_at_k must match retrieved chunk IDs",
        ),
    ],
)
def test_local_evaluation_report_store_rejects_unsafe_or_forged_records(
    tmp_path: Path, relative_path: Path, content: str, message: str
) -> None:
    if relative_path.parts[0] != ".." and relative_path.suffix == ".json":
        path = tmp_path / relative_path
        if relative_path.name == "legacy.json":
            path.write_bytes(b"\xff")
        else:
            if relative_path.name in {"mismatched-count.json", "forged-metric.json"}:
                content = content.replace(
                    '"results":',
                    '"audit": {"record_id": "record-1", '
                    '"comparison_target_id": "target-1", '
                    '"comparison_approval_reference": "target-approval-1", '
                    '"comparison_content_id": "sha256:'
                    '0000000000000000000000000000000000000000000000000000000000000000", '
                    '"approval_state": "pending", '
                    '"retained_until": "2030-01-01", "approval_reference": null, '
                    '"approved_on": null, "superseded_by": null}, "results":',
                )
            path.write_text(content, encoding="utf-8")

    with pytest.raises(RagConfigurationError, match=message):
        LocalRetrievalEvaluationReportStore(root=tmp_path).load(relative_path)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RetrievalEvaluationReportFileConfig(max_file_bytes=0),
        lambda: RetrievalEvaluationReportFileConfig(max_cases=True),
    ],
)
def test_evaluation_report_file_config_rejects_invalid_limits(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(RagConfigurationError):
        factory()
