"""Volume 02의 ReAct 작업 절차와 공개 JSON 계약을 오프라인으로 확인한다."""
from ai_platform.prompts import PromptSections, ReActPrompt, validate_reasoning_json


def main() -> None:
    """모델·Tool 호출 없이 Prompt와 고정된 공개 결과 샘플을 출력한다."""
    prompt = ReActPrompt(
        objective="배송 상태 문의에 관찰 가능한 사실만으로 답변하기",
        sections=PromptSections(
            instruction="문의에 짧고 사실적인 답변을 작성하세요.",
            context="배송 조회 결과가 제공되지 않으면 상태를 추측하지 않습니다.",
            output_format="이전 형식 요구보다 공개 JSON 계약을 우선합니다.",
            constraints=(
                "확인하지 못한 배송 상태를 단정하지 마세요.",
                "외부 시스템이나 Tool을 직접 실행하지 마세요.",
            ),
        ),
    )
    result = validate_reasoning_json(
        """{
        "status": "needs_clarification",
        "answer": "주문 번호를 알려 주시면 배송 상태를 확인할 수 있습니다.",
        "evidence_summary": ["현재 요청에는 주문 번호가 없습니다."]
        }"""
    )

    print(prompt.render("제 주문은 언제 도착하나요?"))
    print("\n[VALIDATED PUBLIC RESULT]")
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
