"""ReAct 개념을 설명하되 내부 Chain of Thought를 출력 계약에 넣지 않는다."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ai_platform.prompts.prompt_templates import (
    PromptConfigurationError,
    PromptSections,
    _require_text,
)


class StructuredReasoningError(PromptConfigurationError):
    """구조적 추론 응답이 공개 출력 계약을 만족하지 않을 때 발생한다."""


class ReasoningResult(BaseModel):
    """내부 추론 대신 최종 답과 검토 가능한 근거 요약만 담는 응답 계약이다."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["complete", "needs_clarification", "cannot_answer"]
    answer: str = Field(min_length=1, max_length=500)
    evidence_summary: tuple[str, ...] = Field(min_length=1, max_length=3)

    @field_validator("evidence_summary")
    @classmethod
    def validate_evidence_summary(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """관찰 가능한 근거 요약만 짧게 받아 비어 있는 항목을 막는다."""
        if any(not item.strip() or len(item) > 180 for item in values):
            raise ValueError("evidence_summary items must be 1 to 180 non-whitespace characters")
        return values


@dataclass(frozen=True, slots=True)
class ReActPrompt:
    """서비스 소유 ReAct 작업 절차와 공개 결과 계약을 렌더링한다.

    이 클래스는 모델 호출, Tool 실행, 내부 Chain of Thought 수집을 하지 않는다.
    ``approved_actions``는 사람이 승인한 행동 이름을 설명하는 메타데이터일 뿐이며,
    문자열을 렌더링했다고 실행 권한이 생기지는 않는다.
    """

    objective: str
    sections: PromptSections
    approved_actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """서비스가 검토할 목적·템플릿·행동 목록을 호출 전에 검증한다."""
        _require_text("objective", self.objective)
        if not isinstance(self.sections, PromptSections):
            raise PromptConfigurationError("sections must be a PromptSections instance")
        if not isinstance(self.approved_actions, tuple):
            raise PromptConfigurationError("approved_actions must be a tuple of non-empty strings")
        for action in self.approved_actions:
            _require_text("approved_action", action)

    def render(self, user_input: str) -> str:
        """작업 절차·승인 행동·공개 JSON 계약을 사용자 입력보다 앞에 둔다."""
        base_prompt = self.sections.render(user_input)
        prefix, input_section = base_prompt.split("[UNTRUSTED USER INPUT]", maxsplit=1)
        return "\n\n".join(
            (
                prefix.rstrip(),
                self._render_workflow(),
                "[UNTRUSTED USER INPUT]" + input_section,
            )
        )

    def _render_workflow(self) -> str:
        """ReAct의 관찰-행동 순서를 노출 가능한 결과 계약과 분리해 표시한다."""
        actions = "\n".join(f"- {action.strip()}" for action in self.approved_actions)
        if not actions:
            actions = "- 없음: 이 오프라인 Prompt는 외부 Tool 실행을 승인하지 않습니다."
        return "\n".join(
            (
                "[REACT WORKFLOW]",
                f"목표: {self.objective.strip()}",
                "필요한 사실을 확인하고, 승인된 행동이 필요하면 분리된 실행 계층에 요청한 뒤,",
                "관찰 결과를 반영해 최종 답을 만드세요.",
                "내부 추론의 단계별 기록이나 Chain of Thought를 출력하지 마세요.",
                "",
                "[APPROVED ACTIONS]",
                actions,
                "",
                "[PUBLIC OUTPUT CONTRACT]",
                "JSON 객체만 반환하세요. 정확히 status, answer, evidence_summary 키만 사용하세요.",
                "status는 complete, needs_clarification, cannot_answer 중 하나입니다.",
                "answer는 최종 사용자용 답변입니다. evidence_summary는 관찰 가능한 사실의",
                "짧은 요약 1~3개입니다.",
                "reasoning, chain_of_thought, analysis 같은 내부 추론 필드를 추가하지 마세요.",
            )
        )


def validate_reasoning_json(raw_response: str) -> ReasoningResult:
    """공개 JSON 결과만 파싱하며 내부 추론 필드·잘못된 값은 실패 닫힘 처리한다."""
    raw_json = _require_text("raw_response", raw_response)
    try:
        return ReasoningResult.model_validate_json(raw_json)
    except ValidationError as error:
        message = "response must match the ReasoningResult JSON schema"
        raise StructuredReasoningError(message) from error
