"""Volume 02 역할 Prompt와 JSON 응답 검증을 네트워크 없이 확인한다."""
from ai_platform.prompts import (
    PromptSections,
    RolePrompt,
    validate_classification_json,
)


def main() -> None:
    """Prompt 문자열과 검증된 고정 JSON 샘플만 출력한다."""
    prompt = RolePrompt(
        role="고객 지원 문의를 분류하는 담당자",
        sections=PromptSections(
            instruction="문의 유형을 분류하세요.",
            context="허용 분류는 billing, technical, unknown입니다.",
            output_format='JSON 객체만 반환하세요: {"category": "...", "reason": "..."}',
            constraints=(
                "category는 허용된 값 하나여야 합니다.",
                "설명이나 Markdown 코드 블록을 JSON 앞뒤에 추가하지 마세요.",
                "근거가 부족하면 unknown을 사용하세요.",
            ),
        ),
    )
    result = validate_classification_json(
        '{"category": "billing", "reason": "영수증 재발급 요청입니다."}'
    )

    print(prompt.render("영수증을 다시 받을 수 있나요?"))
    print("\n[VALIDATED JSON]")
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
