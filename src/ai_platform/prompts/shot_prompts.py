"""Zero-shot, one-shot, few-shot Prompt를 외부 호출 없이 구성한다."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_platform.prompts.prompt_templates import (
    PromptConfigurationError,
    PromptSections,
    _require_text,
)


class ShotMode(StrEnum):
    """예시 수에 따라 구분하는 Prompt 학습 방식."""

    ZERO = "zero-shot"
    ONE = "one-shot"
    FEW = "few-shot"


@dataclass(frozen=True, slots=True)
class PromptExample:
    """서비스가 검토해 둔 입력과 기대 출력의 한 쌍이다."""

    input_data: str
    expected_output: str

    def __post_init__(self) -> None:
        """예시는 빈 값이 아닌 고정된 서비스 데이터만 받는다."""
        _require_text("example input_data", self.input_data)
        _require_text("example expected_output", self.expected_output)


@dataclass(frozen=True, slots=True)
class ShotPrompt:
    """예시 수 계약을 지키며 ``PromptSections``에 시연 데이터를 추가한다.

    이 클래스는 모델을 실행하거나 예시에서 새 답을 추론하지 않는다. 렌더링된 문자열은
    사람이 검토하거나 이후의 분리된 LLM 호출 계층에 전달할 수 있는 Prompt 자산이다.
    """

    sections: PromptSections
    mode: ShotMode
    examples: tuple[PromptExample, ...] = ()

    def __post_init__(self) -> None:
        """모드와 예시 수를 명시적으로 맞춰 실수로 학습 방식을 바꾸지 않게 한다."""
        if not isinstance(self.sections, PromptSections):
            raise PromptConfigurationError("sections must be a PromptSections instance")
        if not isinstance(self.mode, ShotMode):
            raise PromptConfigurationError("mode must be a ShotMode")
        if not isinstance(self.examples, tuple) or not all(
            isinstance(example, PromptExample) for example in self.examples
        ):
            raise PromptConfigurationError("examples must be a tuple of PromptExample values")
        expected_counts = {
            ShotMode.ZERO: lambda count: count == 0,
            ShotMode.ONE: lambda count: count == 1,
            ShotMode.FEW: lambda count: count >= 2,
        }
        if not expected_counts[self.mode](len(self.examples)):
            raise PromptConfigurationError(_example_count_message(self.mode))

    def render(self, user_input: str) -> str:
        """시연 예시와 새 사용자 입력을 서로 다른 데이터 경계에 넣는다."""
        base_prompt = self.sections.render(user_input)
        prefix, input_section = base_prompt.split("[UNTRUSTED USER INPUT]", maxsplit=1)
        demonstrations = f"[DEMONSTRATIONS]\n{self._render_examples()}"
        return f"{prefix}{demonstrations}\n\n[UNTRUSTED USER INPUT]{input_section}"

    def _render_examples(self) -> str:
        """예시가 없는 zero-shot도 검토 가능한 명시적 섹션으로 표시한다."""
        if not self.examples:
            return "- 제공하지 않음 (zero-shot)"
        return "\n\n".join(
            "\n".join(
                (
                    f"[EXAMPLE {index}]",
                    "<example_input>",
                    example.input_data.strip(),
                    "</example_input>",
                    "<expected_output>",
                    example.expected_output.strip(),
                    "</expected_output>",
                )
            )
            for index, example in enumerate(self.examples, start=1)
        )


def _example_count_message(mode: ShotMode) -> str:
    """예시 수 계약 오류를 행동 가능한 메시지로 만든다."""
    messages = {
        ShotMode.ZERO: "zero-shot requires exactly zero examples",
        ShotMode.ONE: "one-shot requires exactly one example",
        ShotMode.FEW: "few-shot requires at least two examples",
    }
    return messages[mode]
