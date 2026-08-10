"""Volume 02의 zero-shot, one-shot, few-shot Prompt를 오프라인으로 비교한다."""
from ai_platform.prompts import PromptExample, PromptSections, ShotMode, ShotPrompt


def template() -> PromptSections:
    """세 전략에서 공유하는 서비스 소유 Prompt 구성 요소를 만든다."""
    return PromptSections(
        instruction="고객 문의를 한 문장으로 분류하세요.",
        context="분류값은 billing, technical, account 중 하나입니다.",
        output_format='JSON 객체: {"category": "..."}',
        constraints=(
            "근거가 부족하면 category에 unknown을 사용하세요.",
            "추측한 사실을 추가하지 마세요.",
        ),
    )


def main() -> None:
    """세 전략이 렌더링하는 예시 수와 데이터 경계를 출력한다."""
    prompts = (
        ShotPrompt(template(), ShotMode.ZERO),
        ShotPrompt(
            template(),
            ShotMode.ONE,
            (PromptExample("영수증을 받고 싶어요.", '{"category": "billing"}'),),
        ),
        ShotPrompt(
            template(),
            ShotMode.FEW,
            (
                PromptExample("영수증을 받고 싶어요.", '{"category": "billing"}'),
                PromptExample("앱이 계속 멈춰요.", '{"category": "technical"}'),
            ),
        ),
    )
    for prompt in prompts:
        print(f"===== {prompt.mode} =====")
        print(prompt.render("비밀번호를 재설정할 수 없어요."))


if __name__ == "__main__":
    main()
