"""네트워크·API 키 없이 샘플 문서에서 근거와 인용을 반환하는 Volume 05 예제다."""

from __future__ import annotations

from pathlib import Path

from ai_platform.rag import LocalRagIndex, RagPipeline, SearchHit, SourceDocument


class SampleOnlyGenerator:
    """실습용 Mock 생성기: 실제 제공자 호출 대신 첫 번째 근거를 그대로 요약한다."""

    def generate(self, *, query: str, contexts: tuple[SearchHit, ...]) -> str:
        del query
        return f"문서 근거: {contexts[0].chunk.text}"


def main() -> None:
    """저장소의 샘플 텍스트만 인덱싱하고 두 질문의 결과를 출력한다."""
    sample_path = Path(__file__).with_name("sample_data") / "handbook.txt"
    index = LocalRagIndex(
        [
            SourceDocument(
                document_id="customer-handbook",
                title="고객 안내서",
                source_uri="local://examples/volume05/handbook.txt",
                content=sample_path.read_text(encoding="utf-8"),
            )
        ]
    )
    pipeline = RagPipeline(index=index, generator=SampleOnlyGenerator())

    for query in ("배송 상태는 어떻게 확인하나요?", "주차장 할인 정책이 있나요?"):
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
