"""허용된 Tool 요청에 위험도와 사람 승인을 추가하는 교육용 실행 경계."""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from ai_platform.tools.execution import ToolExecutionPolicy, execute_with_policy
from ai_platform.tools.registry import ToolRegistry, ToolRegistryError, ToolResult


class ToolRisk(StrEnum):
    """예제 Tool의 선언적 위험도; 위험도 자체가 권한을 부여하지는 않는다."""

    LOW = "low"
    HIGH = "high"


class ToolAuthorizationError(ToolRegistryError):
    """위험도 정책 또는 승인 기록이 요청을 허용하지 않을 때 발생한다."""


class ToolApprovalRequiredError(ToolAuthorizationError):
    """고위험 Tool에 신뢰된 승인 기록이 없을 때 발생한다."""


class ToolApprovalMismatchError(ToolAuthorizationError):
    """승인 기록이 현재 Tool 요청 전체와 일치하지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class ToolAuthorizationPolicy:
    """각 allowlisted Tool에 명시적으로 부여할 위험도다."""

    tool_risks: Mapping[str, ToolRisk]

    def __post_init__(self) -> None:
        """누락되거나 문자열로 위장한 위험도 정책을 거부한다."""
        if not self.tool_risks:
            raise ToolAuthorizationError("tool_risks must not be empty")
        for tool_name, risk in self.tool_risks.items():
            if not tool_name or not isinstance(tool_name, str):
                raise ToolAuthorizationError("tool risk names must be non-empty strings")
            if not isinstance(risk, ToolRisk):
                raise ToolAuthorizationError("tool risks must use ToolRisk values")

    def risk_for(self, tool_name: str) -> ToolRisk:
        """정책에 명시되지 않은 Tool은 거부하고, 기본 위험도를 추정하지 않는다."""
        try:
            return self.tool_risks[tool_name]
        except KeyError as error:
            raise ToolAuthorizationError(
                f"tool has no authorization policy: {tool_name}"
            ) from error

    def requires_approval(self, tool_name: str) -> bool:
        """이 예제에서는 HIGH Tool에만 사람 승인을 요구한다."""
        return self.risk_for(tool_name) is ToolRisk.HIGH


@dataclass(frozen=True, slots=True)
class ApprovalGrant:
    """신뢰된 승인 워크플로가 발행했다고 가정하는 변경 불가 요청 바인딩 기록이다."""

    approval_id: str
    request_id: str
    tool_name: str
    arguments_json: str

    @classmethod
    def for_request(
        cls,
        *,
        approval_id: str,
        request_id: str,
        tool_name: str,
        arguments: Mapping[str, object],
    ) -> ApprovalGrant:
        """승인 시점의 Tool 이름과 JSON 인자를 안정된 표현으로 묶는다."""
        _validate_identifiers(approval_id=approval_id, request_id=request_id, tool_name=tool_name)
        return cls(
            approval_id=approval_id,
            request_id=request_id,
            tool_name=tool_name,
            arguments_json=_canonical_arguments(arguments),
        )

    def __post_init__(self) -> None:
        """직접 생성한 기록도 빈 식별자와 빈 요청 바인딩을 허용하지 않는다."""
        _validate_identifiers(
            approval_id=self.approval_id,
            request_id=self.request_id,
            tool_name=self.tool_name,
        )
        if not self.arguments_json:
            raise ToolAuthorizationError("approval arguments_json must not be empty")

    def matches(
        self,
        *,
        request_id: str,
        tool_name: str,
        arguments: Mapping[str, object],
    ) -> bool:
        """승인 뒤 Tool 이름, 요청 ID, 인자 중 하나라도 바뀌면 불일치로 처리한다."""
        return (
            self.request_id == request_id
            and self.tool_name == tool_name
            and self.arguments_json == _canonical_arguments(arguments)
        )


def execute_authorized(
    registry: ToolRegistry,
    *,
    request_id: str,
    tool_name: str,
    arguments: Mapping[str, object],
    policy: ToolAuthorizationPolicy,
    approval: ApprovalGrant | None = None,
) -> ToolResult:
    """Schema·allowlist 검증 후 승인된 위험 Tool만 기존 registry 경계로 실행한다."""
    authorize_request(
        registry,
        request_id=request_id,
        tool_name=tool_name,
        arguments=arguments,
        policy=policy,
        approval=approval,
    )
    # 기존 실행 경계로 다시 진입하므로 승인 기록이 handler를 직접 호출할 수 없다.
    return registry.execute(tool_name=tool_name, arguments=arguments)


def authorize_request(
    registry: ToolRegistry,
    *,
    request_id: str,
    tool_name: str,
    arguments: Mapping[str, object],
    policy: ToolAuthorizationPolicy,
    approval: ApprovalGrant | None = None,
) -> None:
    """실행 없이 allowlist·Schema·위험도·승인 전체를 확인하는 재사용 가능한 경계다."""
    if not request_id.strip():
        raise ToolAuthorizationError("request_id must not be empty")

    # 승인은 실행 권한이 아니다. 먼저 registry의 allowlist와 Schema를 항상 검증한다.
    registry.validate_request(tool_name=tool_name, arguments=arguments)
    if policy.requires_approval(tool_name):
        if approval is None:
            raise ToolApprovalRequiredError(f"human approval is required for tool: {tool_name}")
        if not approval.matches(
            request_id=request_id,
            tool_name=tool_name,
            arguments=arguments,
        ):
            raise ToolApprovalMismatchError("approval grant does not match the tool request")


def execute_authorized_with_policy(
    registry: ToolRegistry,
    *,
    request_id: str,
    tool_name: str,
    arguments: Mapping[str, object],
    authorization_policy: ToolAuthorizationPolicy,
    execution_policy: ToolExecutionPolicy,
    approval: ApprovalGrant | None = None,
) -> ToolResult:
    """승인을 통과한 요청을 매 시도 registry 검증을 거치는 제한된 실행 정책으로 보낸다."""
    authorize_request(
        registry,
        request_id=request_id,
        tool_name=tool_name,
        arguments=arguments,
        policy=authorization_policy,
        approval=approval,
    )
    return execute_with_policy(
        registry,
        tool_name=tool_name,
        arguments=arguments,
        policy=execution_policy,
    )


def _validate_identifiers(*, approval_id: str, request_id: str, tool_name: str) -> None:
    """로그·감사 상관관계에 필요한 최소 식별자 형태를 확인한다."""
    if not approval_id.strip():
        raise ToolAuthorizationError("approval_id must not be empty")
    if not request_id.strip():
        raise ToolAuthorizationError("request_id must not be empty")
    if not tool_name.strip():
        raise ToolAuthorizationError("tool_name must not be empty")


def _canonical_arguments(arguments: Mapping[str, object]) -> str:
    """순수 JSON 인자를 순서와 공백에 독립적인 승인 바인딩 문자열로 만든다."""
    try:
        return json.dumps(
            arguments,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ToolAuthorizationError("approval arguments must be finite JSON values") from error
