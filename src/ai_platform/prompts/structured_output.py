"""역할 Prompt와 구조화된 JSON 응답을 오프라인으로 계약·검증한다."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_platform.prompts.prompt_templates import (
    PromptConfigurationError,
    PromptSections,
    _require_text,
)


class StructuredOutputError(PromptConfigurationError):
    """모델 응답이 이 장의 JSON 출력 계약을 만족하지 않을 때 발생한다."""


class SupportClassification(BaseModel):
    """고객 문의 분류 응답의 허용된 JSON 스키마다."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: Literal["billing", "technical", "unknown"]
    reason: str = Field(min_length=1, max_length=240)


@dataclass(frozen=True, slots=True)
class RolePrompt:
    """서비스가 소유한 역할과 Prompt 구성 요소를 분리해 렌더링한다.

    ``role``은 사용자 입력이 아니라 배포·검토 대상 설정이다. 이 클래스는 모델을
    호출하지 않으며, 역할 선언이 유효한 JSON을 보장한다고 주장하지 않는다.
    """

    role: str
    sections: PromptSections

    def __post_init__(self) -> None:
        """역할과 재사용 템플릿을 모델 호출 전에 검증한다."""
        _require_text("role", self.role)
        if not isinstance(self.sections, PromptSections):
            raise PromptConfigurationError("sections must be a PromptSections instance")

    def render(self, user_input: str) -> str:
        """역할을 서비스 규칙 앞에, 사용자 입력을 마지막 데이터 영역에 둔다."""
        return f"[ROLE]\n{self.role.strip()}\n\n{self.sections.render(user_input)}"


def validate_classification_json(raw_response: str) -> SupportClassification:
    """응답 문자열을 JSON으로 파싱하고 허용 필드·값·길이를 검증한다.

    실제 호출 계층은 이 함수가 성공한 객체만 후속 처리에 전달해야 한다. 검증 실패 시
    원문을 보정하거나 추측하지 않고 ``StructuredOutputError``로 중단한다.
    """
    raw_json = _require_text("raw_response", raw_response)
    try:
        return SupportClassification.model_validate_json(raw_json)
    except ValidationError as error:
        message = "response must match the SupportClassification JSON schema"
        raise StructuredOutputError(message) from error
