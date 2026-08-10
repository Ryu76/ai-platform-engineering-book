"""알려진 토큰 수를 사용해 컨텍스트 예산을 오프라인으로 점검하는 예제."""
from ai_platform.llm import ContextBudget


def main() -> None:
    """두 요청 계획이 출력 예약량을 포함해 들어가는지 비교한다."""
    budget = ContextBudget(context_window_tokens=2048, reserved_output_tokens=400)

    for label, input_tokens in (("요약 요청", 1500), ("긴 검색 문맥 요청", 1800)):
        assessment = budget.assess(input_tokens)
        status = "가능" if assessment.fits else "초과"
        summary = (
            f"{label}: 입력={assessment.input_tokens}, "
            f"출력 예약={assessment.reserved_output_tokens}, "
            f"계획 합계={assessment.total_planned_tokens}, "
            f"남은 예산={assessment.remaining_tokens}, 판정={status}"
        )
        print(summary)


if __name__ == "__main__":
    main()
