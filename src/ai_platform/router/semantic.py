"""고정 semantic score fixture와 정책 Router를 결합하는 결정론적 Semantic Router."""

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


class NoSemanticScoreFixtureError(NoEligibleRouteError):
    """요청 ID에 대응하는 고정 semantic score fixture가 없을 때 발생한다."""


class NoConfidentSemanticRouteError(NoEligibleRouteError):
    """고정 semantic score가 similarity threshold를 통과하지 못할 때 발생한다."""


@dataclass(frozen=True, slots=True)
class SemanticRoute:
    """한 semantic intent가 요구하는 capability를 고정한다."""

    intent: str
    required_capabilities: frozenset[str]

    def __post_init__(self) -> None:
        """의도 이름과 capability 계약을 모호하지 않게 검증한다."""
        _validate_identifier(self.intent, "semantic route intent")
        if not self.required_capabilities:
            raise RoutingConfigurationError("semantic route capabilities must not be empty")
        for capability in self.required_capabilities:
            _validate_identifier(capability, "semantic route capability")


@dataclass(frozen=True, slots=True)
class SemanticIntentScore:
    """한 intent에 대한 사전 계산된 0~1 semantic similarity fixture다."""

    intent: str
    similarity: Decimal

    def __post_init__(self) -> None:
        """고정 점수를 유한한 Decimal 단위 구간으로 제한한다."""
        _validate_identifier(self.intent, "semantic score intent")
        _validate_unit_decimal(self.similarity, "semantic similarity")


@dataclass(frozen=True, slots=True)
class SemanticScoreFixture:
    """한 요청 ID에 대해 외부 embedding 호출 없이 사용할 semantic 점수를 고정한다."""

    request_id: str
    intent_scores: tuple[SemanticIntentScore, ...]

    def __post_init__(self) -> None:
        """재현 가능한 fixture ID와 중복 없는 intent score를 요구한다."""
        _validate_identifier(self.request_id, "semantic score fixture request_id")
        if not self.intent_scores:
            raise RoutingConfigurationError(
                "semantic score fixture must contain at least one intent score"
            )
        intents = [score.intent for score in self.intent_scores]
        if len(intents) != len(set(intents)):
            raise RoutingConfigurationError("semantic score fixture intents must be unique")


@dataclass(frozen=True, slots=True)
class SemanticRouteDecision:
    """Semantic intent 판정과 정책 대상 선택을 함께 보관한다."""

    router_name: str
    intent: str
    similarity: Decimal
    policy_decision: RouteDecision

    def __post_init__(self) -> None:
        """원문 없이 감사 가능한 semantic 분류 결과를 검증한다."""
        _validate_identifier(self.router_name, "semantic router name")
        _validate_identifier(self.intent, "semantic decision intent")
        _validate_unit_decimal(self.similarity, "semantic decision similarity")

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
            "semantic_similarity": str(self.similarity),
        }


class SemanticRouter:
    """고정 semantic score를 threshold로 판정한 뒤 PolicyRouter에 위임한다.

    score fixture는 ``request_id``로만 선택하며, 실제 embedding·LLM·네트워크 호출을 하지
    않는다. 동점은 similarity가 높은 intent, 그 다음 intent 이름 순으로 해소한다. 선택된
    intent capability는 원래 요청의 capability와 합쳐져 policy 경계를 다시 통과해야 한다.
    """

    def __init__(
        self,
        *,
        name: str,
        policy_router: PolicyRouter,
        routes: tuple[SemanticRoute, ...],
        score_fixtures: tuple[SemanticScoreFixture, ...],
        minimum_similarity: Decimal,
    ) -> None:
        """완전한 고정 fixture와 명시적인 similarity threshold를 검증한다."""
        _validate_identifier(name, "semantic router name")
        if not routes:
            raise RoutingConfigurationError("semantic router must contain at least one route")
        if not score_fixtures:
            raise RoutingConfigurationError(
                "semantic router must contain at least one score fixture"
            )
        route_intents = tuple(route.intent for route in routes)
        if len(route_intents) != len(set(route_intents)):
            raise RoutingConfigurationError("semantic route intents must be unique")
        fixture_request_ids = [fixture.request_id for fixture in score_fixtures]
        if len(fixture_request_ids) != len(set(fixture_request_ids)):
            raise RoutingConfigurationError("semantic score fixture request_ids must be unique")
        expected_intents = set(route_intents)
        for fixture in score_fixtures:
            if {score.intent for score in fixture.intent_scores} != expected_intents:
                raise RoutingConfigurationError(
                    "each semantic score fixture must score every configured route intent "
                    "exactly once"
                )
        _validate_unit_decimal(minimum_similarity, "minimum_similarity")
        self._name = name
        self._policy_router = policy_router
        self._routes_by_intent = {route.intent: route for route in routes}
        self._score_fixtures_by_request_id = {
            fixture.request_id: fixture for fixture in score_fixtures
        }
        self._minimum_similarity = minimum_similarity

    def route(self, request: RoutingRequest) -> SemanticRouteDecision:
        """고정 점수의 최고 eligible intent를 policy 경계 안에서 대상으로 변환한다."""
        fixture = self._score_fixtures_by_request_id.get(request.request_id)
        if fixture is None:
            raise NoSemanticScoreFixtureError(
                "no semantic score fixture is configured for the routing request"
            )
        eligible_scores = [
            score for score in fixture.intent_scores if score.similarity >= self._minimum_similarity
        ]
        if not eligible_scores:
            raise NoConfidentSemanticRouteError(
                "no semantic route meets the configured similarity threshold"
            )
        selected_score = min(eligible_scores, key=lambda score: (-score.similarity, score.intent))
        selected_route = self._routes_by_intent[selected_score.intent]
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
        return SemanticRouteDecision(
            router_name=self._name,
            intent=selected_route.intent,
            similarity=selected_score.similarity,
            policy_decision=self._policy_router.route(constrained_request),
        )


def _validate_identifier(value: object, name: str) -> None:
    """비어 있거나 문자열이 아닌 식별자를 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise RoutingConfigurationError(f"{name} must be a nonempty string")


def _validate_unit_decimal(value: object, name: str) -> None:
    """similarity와 threshold를 유한한 Decimal 0 이상 1 이하로 제한한다."""
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
