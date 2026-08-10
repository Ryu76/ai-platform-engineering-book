"""Print reviewed Prompt test fixtures; no API key, model, or network is used."""
from ai_platform.prompts import PromptTestCase, PromptTestDataset


def build_dataset() -> PromptTestDataset:
    """Create an educational fixture set for every Prompt-version comparison."""
    return PromptTestDataset(
        name="customer-support-v1",
        cases=(
            PromptTestCase(
                case_id="billing-receipt",
                user_input="영수증을 다시 받고 싶어요.",
                expected_category="billing",
                purpose="명확한 청구 문의를 분류한다.",
                tags=("happy-path", "billing"),
            ),
            PromptTestCase(
                case_id="technical-reset",
                user_input="비밀번호를 재설정할 수 없어요.",
                expected_category="technical",
                purpose="명확한 기술 문의를 분류한다.",
                tags=("happy-path", "technical"),
            ),
            PromptTestCase(
                case_id="unknown-ambiguous",
                user_input="무엇을 해야 할지 모르겠어요.",
                expected_category="unknown",
                purpose="근거 없는 추측 대신 unknown을 선택한다.",
                tags=("edge-case", "unknown"),
            ),
        ),
    )


def main() -> None:
    """Show the stable test-data fields and the comparison projection."""
    dataset = build_dataset()
    print(f"[PROMPT TEST DATA] {dataset.name}")
    for case in dataset.cases:
        print(
            f"{case.case_id}: expected={case.expected_category}, "
            f"tags={','.join(case.tags)}, purpose={case.purpose}"
        )
    print("\n[COMPARISON CASE IDS]")
    for case in dataset.comparison_cases():
        print(case.case_id)


if __name__ == "__main__":
    main()
