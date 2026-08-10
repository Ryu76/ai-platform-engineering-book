"""고정 LLM classifier response fixture와 정책 Router를 결합하는 결정론적 Router."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from ai_platform.router.base import (
    NoEligibleRouteError,
    RouteDecision,
    RouteTarget,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
)
from ai_platform.router.policy import PolicyRouter


class NoLLMClassifierResponseFixtureError(NoEligibleRouteError):
    """요청 ID에 대응하는 고정 LLM classifier response fixture가 없을 때 발생한다."""


class NoConfidentLLMRouteError(NoEligibleRouteError):
    """고정 LLM classifier confidence가 threshold를 통과하지 못할 때 발생한다."""


@dataclass(frozen=True, slots=True)
class LLMRoute:
    """한 LLM classifier intent가 요구하는 capability를 고정한다."""

    intent: str
    required_capabilities: frozenset[str]

    def __post_init__(self) -> None:
        """의도 이름과 capability 계약을 모호하지 않게 검증한다."""
        _validate_identifier(self.intent, "LLM route intent")
        if not self.required_capabilities:
            raise RoutingConfigurationError("LLM route capabilities must not be empty")
        for capability in self.required_capabilities:
            _validate_identifier(capability, "LLM route capability")


@dataclass(frozen=True, slots=True)
class LLMClassifierResponseFixture:
    """한 요청의 사전 검토된 LLM intent label과 confidence를 고정한다."""

    request_id: str
    intent: str
    confidence: Decimal

    def __post_init__(self) -> None:
        """원문·prompt·model output 없이 결정에 필요한 최소 fixture만 검증한다."""
        _validate_identifier(self.request_id, "LLM classifier fixture request_id")
        _validate_identifier(self.intent, "LLM classifier fixture intent")
        _validate_unit_decimal(self.confidence, "LLM classifier fixture confidence")


@dataclass(frozen=True, slots=True)
class LLMRouteDecision:
    """고정 LLM intent 판정과 정책 대상 선택을 함께 보관한다."""

    router_name: str
    intent: str
    confidence: Decimal
    policy_decision: RouteDecision

    def __post_init__(self) -> None:
        """원문 없이 감사 가능한 classifier 결과를 검증한다."""
        _validate_identifier(self.router_name, "LLM router name")
        _validate_identifier(self.intent, "LLM decision intent")
        _validate_unit_decimal(self.confidence, "LLM decision confidence")

    @property
    def target(self) -> RouteTarget:
        """호출자가 정책 Router가 선택한 대상을 바로 확인할 수 있게 한다."""
        return self.policy_decision.target

    def as_log_record(self) -> dict[str, str]:
        """사용자 원문 없이 JSON 직렬화 가능한 합성 결정 로그를 반환한다."""
        return {
            **self.policy_decision.as_log_record(),
            "classifier_name": self.router_name,
            "intent": self.intent,
            "llm_classifier_confidence": str(self.confidence),
        }


class LLMRouter:
    """고정 LLM classifier response를 threshold로 판정한 뒤 PolicyRouter에 위임한다.

    response fixture는 ``request_id``로만 선택한다. 이 구현은 LLM, API, 네트워크를 호출하지
    않으며 prompt나 raw response도 보관하지 않는다. 선택된 intent capability는 원래 요청의
    capability와 합쳐져 policy 경계를 다시 통과해야 한다.
    """

    def __init__(
        self,
        *,
        name: str,
        policy_router: PolicyRouter,
        routes: tuple[LLMRoute, ...],
        response_fixtures: tuple[LLMClassifierResponseFixture, ...],
        minimum_confidence: Decimal,
    ) -> None:
        """완전한 고정 fixture와 명시적인 confidence threshold를 검증한다."""
        _validate_identifier(name, "LLM router name")
        if not routes:
            raise RoutingConfigurationError("LLM router must contain at least one route")
        if not response_fixtures:
            raise RoutingConfigurationError(
                "LLM router must contain at least one classifier response fixture"
            )
        route_intents = [route.intent for route in routes]
        if len(route_intents) != len(set(route_intents)):
            raise RoutingConfigurationError("LLM route intents must be unique")
        fixture_request_ids = [fixture.request_id for fixture in response_fixtures]
        if len(fixture_request_ids) != len(set(fixture_request_ids)):
            raise RoutingConfigurationError("LLM classifier fixture request_ids must be unique")
        expected_intents = set(route_intents)
        for fixture in response_fixtures:
            if fixture.intent not in expected_intents:
                raise RoutingConfigurationError(
                    "LLM classifier fixture intent must match a configured route intent"
                )
        _validate_unit_decimal(minimum_confidence, "minimum_confidence")
        self._name = name
        self._policy_router = policy_router
        self._routes_by_intent = {route.intent: route for route in routes}
        self._response_fixtures_by_request_id = {
            fixture.request_id: fixture for fixture in response_fixtures
        }
        self._minimum_confidence = minimum_confidence

    def route(self, request: RoutingRequest) -> LLMRouteDecision:
        """고정 LLM label을 policy 제약 안에서 실행 대상으로 변환한다."""
        fixture = self._response_fixtures_by_request_id.get(request.request_id)
        if fixture is None:
            raise NoLLMClassifierResponseFixtureError(
                "no LLM classifier response fixture is configured for the routing request"
            )
        if fixture.confidence < self._minimum_confidence:
            raise NoConfidentLLMRouteError(
                "no LLM classifier response meets the configured confidence threshold"
            )
        selected_route = self._routes_by_intent[fixture.intent]
        requirements = request.requirements
        constrained_request = RoutingRequest(
            request_id=request.request_id,
            text=request.text,
            requirements=RoutingRequirements(
                required_capabilities=(
                    requirements.required_capabilities | selected_route.required_capabilities
                ),
                maximum_cost=requirements.maximum_cost,
                maximum_latency_ms=requirements.maximum_latency_ms,
                permitted_target_names=requirements.permitted_target_names,
            ),
        )
        return LLMRouteDecision(
            router_name=self._name,
            intent=selected_route.intent,
            confidence=fixture.confidence,
            policy_decision=self._policy_router.route(constrained_request),
        )


def _validate_identifier(value: object, name: str) -> None:
    """비어 있거나 문자열이 아닌 식별자를 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise RoutingConfigurationError(f"{name} must be a nonempty string")


def _validate_unit_decimal(value: object, name: str) -> None:
    """confidence와 threshold를 유한한 Decimal 0 이상 1 이하로 제한한다."""
    if not isinstance(value, Decimal):
        raise RoutingConfigurationError(f"{name} must be a Decimal")
    try:
        valid = value.is_finite() and Decimal("0") <= value <= Decimal("1")
    except InvalidOperation as error:
        raise RoutingConfigurationError(
            f"{name} must be a finite Decimal between 0 and 1"
        ) from error
    if not valid:
        raise RoutingConfigurationError(f"{name} must be a finite Decimal between 0 and 1")
