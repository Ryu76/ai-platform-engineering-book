"""외부 호출 없이 LLM 요청의 컨텍스트 토큰 예산을 점검하는 도구."""
from __future__ import annotations

from dataclasses import dataclass


class ContextBudgetError(ValueError):
    """컨텍스트 윈도우 또는 토큰 수 입력이 유효하지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class ContextAssessment:
    """입력과 예약 출력이 컨텍스트 윈도우에 들어가는지 나타낸다."""

    context_window_tokens: int
    input_tokens: int
    reserved_output_tokens: int
    total_planned_tokens: int
    remaining_tokens: int

    @property
    def fits(self) -> bool:
        """계획한 입력과 예약 출력이 한 요청에 함께 들어가는지 반환한다."""
        return self.remaining_tokens >= 0


@dataclass(frozen=True, slots=True)
class ContextBudget:
    """모델별 컨텍스트 윈도우와 출력 예약량을 명시적으로 관리한다.

    이 클래스는 텍스트를 토큰화하지 않는다. 실제 토큰 수는 선택한 모델의
    토크나이저 또는 제공자가 반환한 사용량으로 확인한 뒤 ``assess``에 전달해야 한다.
    """

    context_window_tokens: int
    reserved_output_tokens: int

    def __post_init__(self) -> None:
        """음수, 불리언, 0인 윈도우와 출력 예약량을 요청 전에 거부한다."""
        _require_positive_int(self.context_window_tokens, "context_window_tokens")
        _require_nonnegative_int(self.reserved_output_tokens, "reserved_output_tokens")
        if self.reserved_output_tokens > self.context_window_tokens:
            raise ContextBudgetError(
                "reserved_output_tokens must not exceed context_window_tokens"
            )

    @property
    def available_input_tokens(self) -> int:
        """예약한 출력을 남긴 뒤 입력에 사용할 수 있는 최대 토큰 수를 반환한다."""
        return self.context_window_tokens - self.reserved_output_tokens

    def assess(self, input_tokens: int) -> ContextAssessment:
        """확인한 입력 토큰 수로 요청 계획의 적합 여부를 계산한다."""
        _require_nonnegative_int(input_tokens, "input_tokens")
        total_planned_tokens = input_tokens + self.reserved_output_tokens
        return ContextAssessment(
            context_window_tokens=self.context_window_tokens,
            input_tokens=input_tokens,
            reserved_output_tokens=self.reserved_output_tokens,
            total_planned_tokens=total_planned_tokens,
            remaining_tokens=self.context_window_tokens - total_planned_tokens,
        )

    def require_fits(self, input_tokens: int) -> ContextAssessment:
        """계획이 넘치면 원인과 가능한 입력 상한을 포함해 안전하게 실패한다."""
        assessment = self.assess(input_tokens)
        if not assessment.fits:
            raise ContextBudgetError(
                "planned input and reserved output exceed the context window; "
                f"input_tokens must be at most {self.available_input_tokens}"
            )
        return assessment


def _require_positive_int(value: int, name: str) -> None:
    """0보다 큰 정수인지 검증한다."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ContextBudgetError(f"{name} must be a positive integer")


def _require_nonnegative_int(value: int, name: str) -> None:
    """0 이상 정수인지 검증한다."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContextBudgetError(f"{name} must be a nonnegative integer")
