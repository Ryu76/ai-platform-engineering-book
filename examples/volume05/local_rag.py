"""네트워크·API 키 없이 샘플 문서에서 근거와 인용을 반환하는 Volume 05 예제다."""

from __future__ import annotations

from pathlib import Path

from ai_platform.rag import LocalMarkdownLoader, LocalRagIndex, RagPipeline, SearchHit


class SampleOnlyGenerator:
    """실습용 Mock 생성기: 실제 제공자 호출 대신 첫 번째 근거를 그대로 요약한다."""

    def generate(self, *, query: str, contexts: tuple[SearchHit, ...]) -> str:
        del query
        return f"문서 근거: {contexts[0].chunk.text}"


def main() -> None:
    """명시한 샘플 Markdown 문서만 인덱싱하고 세 질문의 결과를 출력한다."""
    sample_root = Path(__file__).with_name("sample_data")
    loader = LocalMarkdownLoader(root=sample_root)
    documents = loader.load_many((Path("handbook.md"), Path("returns.md")))
    index = LocalRagIndex(documents)
    pipeline = RagPipeline(index=index, generator=SampleOnlyGenerator())

    for query in (
        "배송 상태는 어떻게 확인하나요?",
        "반품 요청은 어떻게 접수하나요?",
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
