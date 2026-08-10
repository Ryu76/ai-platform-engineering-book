"""Volume 02 Prompt 구성 요소를 네트워크 없이 확인하는 실행 예제."""
from ai_platform.prompts import PromptSections


def main() -> None:
    """고정 템플릿에 사용자 데이터를 넣은 결과만 콘솔에 표시한다."""
    template = PromptSections(
        instruction="고객 문의를 한 문장으로 분류하세요.",
        context="분류값은 billing, technical, account 중 하나입니다.",
        output_format='JSON 객체: {"category": "...", "reason": "..."}',
        constraints=(
            "근거가 부족하면 category에 unknown을 사용하세요.",
            "추측한 사실을 추가하지 마세요.",
        ),
    )
    print(template.render("영수증을 다시 받을 수 있나요?"))


if __name__ == "__main__":
    main()
