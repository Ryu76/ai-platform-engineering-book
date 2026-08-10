"""Compare fixed, offline Prompt-version artifacts without an API call."""
from ai_platform.prompts import (
    PromptComparisonCase,
    PromptSections,
    RecordedClassification,
    VersionedPrompt,
    compare_recorded_classifications,
)


def build_prompt(version: str, change_summary: str) -> VersionedPrompt:
    """Build a reviewed version of the same customer-support classification Prompt."""
    return VersionedPrompt(
        version=version,
        change_summary=change_summary,
        sections=PromptSections(
            instruction="고객 문의를 분류하세요.",
            context="허용 분류는 billing, technical, unknown입니다.",
            output_format='JSON 객체만 반환: {"category": "...", "reason": "..."}',
            constraints=("추측하지 말고 허용 분류만 사용하세요.",),
        ),
    )


def main() -> None:
    """Render one version and score deliberately fixed review records for two versions."""
    cases = (
        PromptComparisonCase("billing-receipt", "영수증을 다시 받고 싶어요.", "billing"),
        PromptComparisonCase("technical-reset", "비밀번호를 재설정할 수 없어요.", "technical"),
    )
    version_one = build_prompt("v1", "기본 분류와 JSON 형식을 추가했습니다.")
    version_two = build_prompt("v2", "허용 분류와 추측 금지 제약을 더 명확히 했습니다.")
    version_one_records = (
        RecordedClassification(
            "billing-receipt", '{"category": "billing", "reason": "영수증 요청"}'
        ),
        RecordedClassification("technical-reset", "technical"),
    )
    version_two_records = (
        RecordedClassification(
            "billing-receipt", '{"category": "billing", "reason": "영수증 요청"}'
        ),
        RecordedClassification(
            "technical-reset", '{"category": "technical", "reason": "재설정 문제"}'
        ),
    )

    print(version_two.render(cases[0].user_input))
    print("\n[RECORDED COMPARISON — no model was called]")
    for comparison in (
        compare_recorded_classifications(version_one, cases, version_one_records),
        compare_recorded_classifications(version_two, cases, version_two_records),
    ):
        print(
            f"{comparison.version}: "
            f"schema={comparison.schema_valid_count}/{comparison.total_cases}, "
            f"category_match={comparison.category_match_count}/{comparison.total_cases}"
        )


if __name__ == "__main__":
    main()
