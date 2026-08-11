"""정책 경계를 유지한 채 제한된 fallback을 수행하는 결정론적 Router."""

from __future__ import annotations

from dataclasses import dataclass

from ai_platform.router.base import (
    NoEligibleRouteError,
    RouteDecision,
    RouteTarget,
    RoutingConfigurationError,
    RoutingRequest,
)
from ai_platform.router.policy import PolicyRouter


class FallbackRouteExhaustedError(NoEligibleRouteError):
    """허용된 모든 policy 시도가 안전하게 실패했을 때 발생한다."""

    def __init__(self, *, request_id: str, attempted_policy_names: tuple[str, ...]) -> None:
        """원문 없이 요청 ID와 실제로 시도한 policy 이름만 보관한다."""
        super().__init__("no eligible route found within the configured fallback retry budget")
        self.request_id = request_id
        self.attempted_policy_names = attempted_policy_names

    def as_log_record(self) -> dict[str, object]:
        """사용자 원문 없이 JSON 직렬화 가능한 fail-closed 로그를 반환한다."""
        return {
            "request_id": self.request_id,
            "outcome": "no_eligible_fallback_route",
            "attempted_policy_names": list(self.attempted_policy_names),
        }


@dataclass(frozen=True, slots=True)
class FallbackRouteDecision:
    """성공한 policy 결정과 그 이전의 안전한 fallback 시도를 보관한다."""

    router_name: str
    policy_decision: RouteDecision
    attempted_policy_names: tuple[str, ...]

    def __post_init__(self) -> None:
        """성공 policy가 마지막 시도와 일치하는 불변의 감사 기록을 보장한다."""
        _validate_identifier(self.router_name, "fallback router name")
        if not self.attempted_policy_names:
            raise RoutingConfigurationError("attempted_policy_names must not be empty")
        for policy_name in self.attempted_policy_names:
            _validate_identifier(policy_name, "attempted policy name")
        if self.attempted_policy_names[-1] != self.policy_decision.policy_name:
            raise RoutingConfigurationError(
                "the successful policy must be the final attempted policy name"
            )

    @property
    def target(self) -> RouteTarget:
        """호출자가 최종 policy가 선택한 대상을 바로 확인할 수 있게 한다."""
        return self.policy_decision.target

    @property
    def fallback_count(self) -> int:
        """primary 이후 실제로 소비한 fallback retry 횟수를 반환한다."""
        return len(self.attempted_policy_names) - 1

    def as_log_record(self) -> dict[str, object]:
        """사용자 원문 없이 JSON 직렬화 가능한 성공 로그를 반환한다."""
        return {
            **self.policy_decision.as_log_record(),
            "fallback_router_name": self.router_name,
            "fallback_count": self.fallback_count,
            "attempted_policy_names": list(self.attempted_policy_names),
        }


class PolicyFallbackRouter:
    """primary policy와 명시적 fallback policy를 제한된 retry budget 안에서 시도한다.

    모든 시도는 같은 ``RoutingRequest``를 각 ``PolicyRouter``에 전달한다. 따라서 fallback은
    capability, 허용 대상, 비용, 지연 시간, 상태 제약을 완화하거나 우회할 수 없다. primary를
    먼저 시도하고, 실패한 경우 선언 순서대로 최대 ``retry_budget``개의 fallback만 시도한다.
    """

    def __init__(
        self,
        *,
        name: str,
        primary_router: PolicyRouter,
        fallback_routers: tuple[PolicyRouter, ...],
        retry_budget: int,
    ) -> None:
        """모호하지 않은 policy 순서와 명시적인 fallback retry 예산을 검증한다."""
        _validate_identifier(name, "fallback router name")
        if isinstance(retry_budget, bool) or not isinstance(retry_budget, int) or retry_budget < 0:
            raise RoutingConfigurationError("retry_budget must be a nonnegative integer")
        policy_names = [primary_router.name, *(router.name for router in fallback_routers)]
        if len(policy_names) != len(set(policy_names)):
            raise RoutingConfigurationError("primary and fallback policy names must be unique")
        self._name = name
        self._primary_router = primary_router
        self._fallback_routers = fallback_routers
        self._retry_budget = retry_budget

    def route(self, request: RoutingRequest) -> FallbackRouteDecision:
        """제한된 순서로 policy를 시도하고, 예산 소진 시 fail closed 한다."""
        routers_to_try = (self._primary_router, *self._fallback_routers[: self._retry_budget])
        attempted_policy_names: list[str] = []
        for policy_router in routers_to_try:
            attempted_policy_names.append(policy_router.name)
            try:
                policy_decision = policy_router.route(request)
            except NoEligibleRouteError:
                continue
            return FallbackRouteDecision(
                router_name=self._name,
                policy_decision=policy_decision,
                attempted_policy_names=tuple(attempted_policy_names),
            )
        raise FallbackRouteExhaustedError(
            request_id=request.request_id,
            attempted_policy_names=tuple(attempted_policy_names),
        )


def _validate_identifier(value: object, name: str) -> None:
    """비어 있거나 문자열이 아닌 식별자를 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise RoutingConfigurationError(f"{name} must be a nonempty string")
