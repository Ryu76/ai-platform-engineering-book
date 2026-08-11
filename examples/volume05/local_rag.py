"""네트워크·API 키 없이 샘플 문서에서 근거와 인용을 반환하는 Volume 05 예제다."""

from __future__ import annotations

from pathlib import Path

from ai_platform.rag import (
    ConfidenceThresholdConfig,
    ConfidenceThresholdIndex,
    ContextBudgetConfig,
    ContextBudgetIndex,
    DenseCandidate,
    DocumentChunk,
    DocumentDiversityConfig,
    DocumentDiversityIndex,
    HybridRagIndex,
    LocalMarkdownLoader,
    LocalPdfLoader,
    LocalRagIndex,
    QueryTransformingIndex,
    RagPipeline,
    RerankingIndex,
    RerankResult,
    SearchHit,
)


class SamplePdfTextExtractor:
    """실제 PDF 엔진 대신 로컬 고정 샘플 페이지를 반환하는 파서 Mock이다."""

    def extract_pages(self, *, pdf_bytes: bytes) -> tuple[str, ...]:
        if not pdf_bytes.startswith(b"%PDF-"):
            raise ValueError("sample PDF fixture has no PDF header")
        return ("교환은 미사용 상품에 한해 수령 뒤 7일 안에 신청할 수 있습니다.",)


class SampleDenseRanker:
    """외부 모델 대신 질문별 로컬 샘플 청크만 돌려주는 dense Mock이다."""

    _CANDIDATES_BY_QUERY = {
        "언제 도착하나요?": "local:handbook.md#1",
        "반품 요청은 어떻게 접수하나요?": "local:returns.md#1",
    }

    def rank(
        self, *, query: str, chunks: tuple[DocumentChunk, ...], top_k: int
    ) -> tuple[DenseCandidate, ...]:
        allowed_chunk_ids = {chunk.chunk_id for chunk in chunks}
        candidate_id = self._CANDIDATES_BY_QUERY.get(query)
        if candidate_id not in allowed_chunk_ids:
            return ()
        return (DenseCandidate(candidate_id),)[:top_k]


class SampleQueryTransformer:
    """외부 모델 없이 원 질문을 보존한 로컬 검색 확장 Mock이다."""

    _QUERIES_BY_QUERY = {
        "언제 도착하나요?": ("언제 도착하나요?", "배송 도착"),
        "반품 요청은 어떻게 접수하나요?": ("반품 요청은 어떻게 접수하나요?", "반품 접수"),
    }

    def transform(self, *, query: str) -> tuple[str, ...]:
        return self._QUERIES_BY_QUERY.get(query, (query,))


class SampleEvidenceReranker:
    """외부 모델 없이 현재 로컬 후보만 점수화하는 재순위화 Mock이다."""

    def rerank(
        self, *, query: str, candidates: tuple[SearchHit, ...], top_k: int
    ) -> tuple[RerankResult, ...]:
        del query
        return tuple(
            RerankResult(hit.chunk.chunk_id, 1.0 - (position * 0.1))
            for position, hit in enumerate(candidates[:top_k])
        )


class SampleOnlyGenerator:
    """실습용 Mock 생성기: 실제 제공자 호출 대신 첫 번째 근거를 그대로 요약한다."""

    def generate(self, *, query: str, contexts: tuple[SearchHit, ...]) -> str:
        del query
        return f"문서 근거: {contexts[0].chunk.text}"


def main() -> None:
    """명시한 샘플 Markdown·PDF 문서만 인덱싱하고 네 질문의 결과를 출력한다."""
    sample_root = Path(__file__).with_name("sample_data")
    loader = LocalMarkdownLoader(root=sample_root)
    pdf_loader = LocalPdfLoader(root=sample_root, extractor=SamplePdfTextExtractor())
    documents = (
        *loader.load_many((Path("handbook.md"), Path("returns.md"))),
        *pdf_loader.load(Path("exchange-notice.pdf")),
    )
    sparse_index = LocalRagIndex(documents)
    hybrid_index = HybridRagIndex(sparse_index=sparse_index, dense_ranker=SampleDenseRanker())
    transformed_index = QueryTransformingIndex(
        index=hybrid_index, transformer=SampleQueryTransformer()
    )
    reranked_index = RerankingIndex(index=transformed_index, reranker=SampleEvidenceReranker())
    diverse_index = DocumentDiversityIndex(
        index=reranked_index,
        config=DocumentDiversityConfig(candidate_count=3, max_chunks_per_document=1),
    )
    budgeted_index = ContextBudgetIndex(
        index=diverse_index,
        config=ContextBudgetConfig(candidate_count=3, max_context_characters=600),
    )
    index = ConfidenceThresholdIndex(
        index=budgeted_index,
        config=ConfidenceThresholdConfig(candidate_count=3, minimum_confidence=0.8),
    )
    pipeline = RagPipeline(index=index, generator=SampleOnlyGenerator())

    for query in (
        "언제 도착하나요?",
        "반품 요청은 어떻게 접수하나요?",
        "교환은 언제 신청하나요?",
        "주차장 할인 정책이 있나요?",
    ):
        answer = pipeline.answer(query)
        print(f"질문: {query}")
        print(f"답변: {answer.text}")
        if answer.no_answer:
            print("인용: 없음 (No-answer)")
        else:
            for citation in answer.citations:
                print(f"인용 [{citation.label}]: {citation.title} — {citation.source_uri}")
        print()


if __name__ == "__main__":
    main()
