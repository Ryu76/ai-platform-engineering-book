"""결정론적 PolicyRouter를 안전한 로컬 HTTP 계약으로 변환한다."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_platform.router.base import (
    NoEligibleRouteError,
    RouteDecision,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
)
from ai_platform.router.policy import PolicyRouter


class _RoutingRequirementsPayload(BaseModel):
    """POST body의 정책 제한을 JSON 원시 타입으로만 받는다."""

    model_config = ConfigDict(extra="forbid", strict=True)

    required_capabilities: list[str] = Field(default_factory=list)
    maximum_cost: str | None = None
    maximum_latency_ms: int | None = None
    permitted_target_names: list[str] | None = None


class _RoutingRequestPayload(BaseModel):
    """원문을 보관하지 않고 검증 직후 RoutingRequest로 변환할 입력 계약이다."""

    model_config = ConfigDict(extra="forbid", strict=True)

    request_id: str
    text: str
    requirements: _RoutingRequirementsPayload = Field(default_factory=_RoutingRequirementsPayload)


@dataclass(frozen=True, slots=True)
class RouterAPIResponse:
    """프레임워크 없이 테스트할 수 있는 HTTP 상태와 JSON 본문이다."""

    status_code: int
    body: dict[str, object]

    def __post_init__(self) -> None:
        """이 실습이 사용하는 성공·입력 오류·안전 실패 응답만 허용한다."""
        if self.status_code not in {200, 400, 422}:
            raise RoutingConfigurationError("router API status_code must be 200, 400, or 422")


class RouterAPI:
    """고정 PolicyRouter를 POST `/routes` 요청·응답 계약으로 노출한다.

    이 adapter는 HTTP 서버, 외부 API, 네트워크를 실행하지 않는다. 웹 프레임워크는 JSON body를
    ``route_post``에 전달하고 반환된 ``status_code``와 ``body``를 그대로 HTTP 응답으로 쓸 수
    있다. 모든 오류 응답은 원문이나 validation detail을 되돌려주지 않는다.
    """

    def __init__(self, *, policy_router: PolicyRouter) -> None:
        """HTTP 경계 뒤에서 사용할 결정론적 정책 Router를 보관한다."""
        self._policy_router = policy_router

    def route_post(self, payload: object) -> RouterAPIResponse:
        """POST `/routes` JSON body를 검증하고 policy 결정 또는 fail-closed 응답을 반환한다."""
        try:
            request = _routing_request_from_payload(payload)
        except (InvalidOperation, RoutingConfigurationError, ValidationError, ValueError):
            return RouterAPIResponse(
                status_code=400,
                body={
                    "outcome": "invalid_routing_request",
                    "error_code": "INVALID_ROUTING_REQUEST",
                },
            )
        try:
            decision = self._policy_router.route(request)
        except NoEligibleRouteError:
            return RouterAPIResponse(
                status_code=422,
                body={
                    "request_id": request.request_id,
                    "outcome": "no_eligible_route",
                    "error_code": "NO_ELIGIBLE_ROUTE",
                },
            )
        return RouterAPIResponse(status_code=200, body=_success_body(decision))


def _routing_request_from_payload(payload: object) -> RoutingRequest:
    """검증된 JSON 원시 타입을 기존 정책 계약으로 변환한다."""
    parsed = _RoutingRequestPayload.model_validate(payload)
    requirements_payload = parsed.requirements
    maximum_cost = (
        Decimal(requirements_payload.maximum_cost)
        if requirements_payload.maximum_cost is not None
        else None
    )
    return RoutingRequest(
        request_id=parsed.request_id,
        text=parsed.text,
        requirements=RoutingRequirements(
            required_capabilities=frozenset(requirements_payload.required_capabilities),
            maximum_cost=maximum_cost,
            maximum_latency_ms=requirements_payload.maximum_latency_ms,
            permitted_target_names=(
                frozenset(requirements_payload.permitted_target_names)
                if requirements_payload.permitted_target_names is not None
                else None
            ),
        ),
    )


def _success_body(decision: RouteDecision) -> dict[str, object]:
    """원문 없이 기존 JSON 가능 decision log만 성공 응답에 포함한다."""
    return {"outcome": "routed", "decision": decision.as_log_record()}
