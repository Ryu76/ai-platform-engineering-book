"""명시적 request capability rule을 정책 Router에 연결하는 결정론적 Router."""

from __future__ import annotations

from dataclasses import dataclass

from ai_platform.router.base import (
    NoEligibleRouteError,
    RouteDecision,
    RouteTarget,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
)
from ai_platform.router.policy import PolicyRouter


class NoMatchingRuleRouteError(NoEligibleRouteError):
    """명시적으로 구성된 rule이 요청 조건에 일치하지 않을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class RuleRoute:
    """요청 capability 조건에 일치할 때 추가 capability를 요구하는 고정 rule이다."""

    name: str
    required_request_capabilities: frozenset[str]
    added_required_capabilities: frozenset[str]
    priority: int

    def __post_init__(self) -> None:
        """모호하지 않은 정적 rule fixture를 검증한다."""
        _validate_identifier(self.name, "rule route name")
        if not self.required_request_capabilities:
            raise RoutingConfigurationError("rule route request capabilities must not be empty")
        _validate_capabilities(self.required_request_capabilities, "rule route request capability")
        if not self.added_required_capabilities:
            raise RoutingConfigurationError("rule route added capabilities must not be empty")
        _validate_capabilities(self.added_required_capabilities, "rule route added capability")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise RoutingConfigurationError("rule route priority must be an integer")


@dataclass(frozen=True, slots=True)
class RuleRouteDecision:
    """선택된 rule과 policy 재검증 결과를 원문 없이 보관한다."""

    router_name: str
    rule_name: str
    policy_decision: RouteDecision

    def __post_init__(self) -> None:
        """감사 로그에 사용할 식별자를 검증한다."""
        _validate_identifier(self.router_name, "rule router name")
        _validate_identifier(self.rule_name, "rule route name")

    @property
    def target(self) -> RouteTarget:
        """PolicyRouter가 선택한 최종 대상을 반환한다."""
        return self.policy_decision.target

    def as_log_record(self) -> dict[str, object]:
        """사용자 원문 없이 JSON 직렬화 가능한 합성 결정 로그를 반환한다."""
        return {
            **self.policy_decision.as_log_record(),
            "rule_router_name": self.router_name,
            "rule_name": self.rule_name,
        }


class RuleRouter:
    """명시적 request capability rule을 고른 뒤 PolicyRouter에 재검증을 위임한다.

    모든 일치 rule 중 priority가 큰 rule을 우선하고, priority가 같으면 rule 이름을
    사전순으로 선택한다. 선택 rule의 추가 capability는 원래 요청 capability와 합쳐져
    PolicyRouter의 allowlist, health, cost, latency 제약을 그대로 통과해야 한다.
    """

    def __init__(
        self,
        *,
        name: str,
        policy_router: PolicyRouter,
        routes: tuple[RuleRoute, ...],
    ) -> None:
        """이름과 중복 없는 명시적 rule 목록을 검증해 고정한다."""
        _validate_identifier(name, "rule router name")
        if not routes:
            raise RoutingConfigurationError("rule router must contain at least one route")
        route_names = [route.name for route in routes]
        if len(route_names) != len(set(route_names)):
            raise RoutingConfigurationError("rule route names must be unique")
        self._name = name
        self._policy_router = policy_router
        self._routes = routes

    def route(self, request: RoutingRequest) -> RuleRouteDecision:
        """최우선 명시 rule을 고르고 더 좁아진 조건으로 정책을 재검증한다."""
        request_capabilities = request.requirements.required_capabilities
        matching_routes = [
            route
            for route in self._routes
            if route.required_request_capabilities.issubset(request_capabilities)
        ]
        if not matching_routes:
            raise NoMatchingRuleRouteError("no rule route matches the request capabilities")
        selected_route = min(matching_routes, key=lambda route: (-route.priority, route.name))
        requirements = request.requirements
        constrained_request = RoutingRequest(
            request_id=request.request_id,
            text=request.text,
            requirements=RoutingRequirements(
                required_capabilities=(
                    requirements.required_capabilities | selected_route.added_required_capabilities
                ),
                maximum_cost=requirements.maximum_cost,
                maximum_latency_ms=requirements.maximum_latency_ms,
                permitted_target_names=requirements.permitted_target_names,
            ),
        )
        return RuleRouteDecision(
            router_name=self._name,
            rule_name=selected_route.name,
            policy_decision=self._policy_router.route(constrained_request),
        )


def _validate_capabilities(capabilities: frozenset[str], name: str) -> None:
    """모든 고정 capability가 비어 있지 않은 문자열인지 확인한다."""
    for capability in capabilities:
        _validate_identifier(capability, name)


def _validate_identifier(value: object, name: str) -> None:
    """빈 문자열, 공백 전용 문자열, 문자열이 아닌 식별자를 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise RoutingConfigurationError(f"{name} must be a nonempty string")
