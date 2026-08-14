"""고정 semantic score·embedding fixture와 정책 경계를 결합하는 Semantic Router."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext

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
    """요청 ID에 대응하는 고정 semantic fixture가 없을 때 발생한다."""


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
class SemanticIntentEmbedding:
    """한 intent의 고정된 비음수 Decimal embedding vector다."""

    intent: str
    embedding: tuple[Decimal, ...]

    def __post_init__(self) -> None:
        """intent와 재현 가능한 local embedding 값을 검증한다."""
        _validate_identifier(self.intent, "semantic embedding intent")
        _validate_embedding(self.embedding, "semantic intent embedding")


@dataclass(frozen=True, slots=True)
class SemanticEmbeddingFixture:
    """요청 ID별 query·intent embedding으로 local cosine score를 재현한다."""

    request_id: str
    query_embedding: tuple[Decimal, ...]
    intent_embeddings: tuple[SemanticIntentEmbedding, ...]

    def __post_init__(self) -> None:
        """fixture 자체의 식별자·vector·intent 중복을 fail closed 한다."""
        _validate_identifier(self.request_id, "semantic embedding fixture request_id")
        _validate_embedding(self.query_embedding, "semantic query embedding")
        if not self.intent_embeddings:
            raise RoutingConfigurationError(
                "semantic embedding fixture must contain at least one intent embedding"
            )
        intents = [intent_embedding.intent for intent_embedding in self.intent_embeddings]
        if len(intents) != len(set(intents)):
            raise RoutingConfigurationError("semantic embedding fixture intents must be unique")


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
    """고정 semantic score 또는 local embedding을 PolicyRouter 경계 안에서 판정한다.

    fixture는 ``request_id``로만 선택하며 실제 embedding 모델·LLM·네트워크를 호출하지
    않는다. embedding fixture는 비음수 ``Decimal`` vector의 local cosine similarity를
    계산하고, score fixture는 검토된 similarity를 그대로 사용한다. 두 mode를 한 Router에
    섞을 수 없다. 동점은 similarity가 높은 intent, 그 다음 intent 이름 순으로 해소한다.
    선택된 intent capability는 원래 요청의 capability와 합쳐져 policy 경계를 다시 통과해야
    한다.
    """

    def __init__(
        self,
        *,
        name: str,
        policy_router: PolicyRouter,
        routes: tuple[SemanticRoute, ...],
        minimum_similarity: Decimal,
        score_fixtures: tuple[SemanticScoreFixture, ...] = (),
        embedding_fixtures: tuple[SemanticEmbeddingFixture, ...] = (),
    ) -> None:
        """하나의 완전한 fixture mode와 명시적인 similarity threshold를 검증한다."""
        _validate_identifier(name, "semantic router name")
        if not routes:
            raise RoutingConfigurationError("semantic router must contain at least one route")
        if bool(score_fixtures) == bool(embedding_fixtures):
            raise RoutingConfigurationError(
                "semantic router must contain score fixtures or embedding fixtures, but not both"
            )
        route_intents = tuple(route.intent for route in routes)
        if len(route_intents) != len(set(route_intents)):
            raise RoutingConfigurationError("semantic route intents must be unique")
        fixtures: tuple[SemanticScoreFixture | SemanticEmbeddingFixture, ...]
        fixtures = score_fixtures or embedding_fixtures
        fixture_request_ids = [fixture.request_id for fixture in fixtures]
        if len(fixture_request_ids) != len(set(fixture_request_ids)):
            raise RoutingConfigurationError("semantic fixture request_ids must be unique")
        expected_intents = set(route_intents)
        if score_fixtures:
            for score_fixture in score_fixtures:
                if {score.intent for score in score_fixture.intent_scores} != expected_intents:
                    raise RoutingConfigurationError(
                        "each semantic score fixture must score every configured route intent "
                        "exactly once"
                    )
        else:
            for embedding_fixture in embedding_fixtures:
                _validate_embedding_fixture(embedding_fixture, expected_intents)
        _validate_unit_decimal(minimum_similarity, "minimum_similarity")
        self._name = name
        self._policy_router = policy_router
        self._routes_by_intent = {route.intent: route for route in routes}
        self._score_fixtures_by_request_id = {
            fixture.request_id: fixture for fixture in score_fixtures
        }
        self._embedding_fixtures_by_request_id = {
            fixture.request_id: fixture for fixture in embedding_fixtures
        }
        self._minimum_similarity = minimum_similarity

    def route(self, request: RoutingRequest) -> SemanticRouteDecision:
        """고정 score 또는 local cosine similarity의 최고 intent를 policy 경계에 전달한다."""
        intent_scores = self._intent_scores_for(request.request_id)
        eligible_scores = [
            score for score in intent_scores if score.similarity >= self._minimum_similarity
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

    def _intent_scores_for(self, request_id: str) -> tuple[SemanticIntentScore, ...]:
        """선택한 fixture mode에서 request ID의 모든 intent score를 얻는다."""
        score_fixture = self._score_fixtures_by_request_id.get(request_id)
        if score_fixture is not None:
            return score_fixture.intent_scores
        embedding_fixture = self._embedding_fixtures_by_request_id.get(request_id)
        if embedding_fixture is None:
            raise NoSemanticScoreFixtureError(
                "no semantic score fixture or embedding fixture is configured "
                "for the routing request"
            )
        return tuple(
            SemanticIntentScore(
                intent=intent_embedding.intent,
                similarity=_cosine_similarity(
                    embedding_fixture.query_embedding, intent_embedding.embedding
                ),
            )
            for intent_embedding in embedding_fixture.intent_embeddings
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


def _validate_embedding(embedding: object, name: str) -> None:
    """local cosine fixture가 유한한 비음수·비영 vector만 사용하게 한다."""
    if not isinstance(embedding, tuple) or not embedding:
        raise RoutingConfigurationError(f"{name} must be a nonempty tuple of Decimal values")
    if any(
        not isinstance(component, Decimal) or not component.is_finite() for component in embedding
    ):
        raise RoutingConfigurationError(f"{name} must contain only finite Decimal values")
    if any(component < Decimal("0") for component in embedding):
        raise RoutingConfigurationError(f"{name} must contain only nonnegative Decimal values")
    if not any(component > Decimal("0") for component in embedding):
        raise RoutingConfigurationError(f"{name} must not be a zero vector")


def _validate_embedding_fixture(
    fixture: SemanticEmbeddingFixture, expected_intents: set[str]
) -> None:
    """한 embedding fixture가 모든 route와 같은 차원의 vector를 가리키게 한다."""
    if {
        intent_embedding.intent for intent_embedding in fixture.intent_embeddings
    } != expected_intents:
        raise RoutingConfigurationError(
            "each semantic embedding fixture must embed every configured route intent exactly once"
        )
    if any(
        len(intent_embedding.embedding) != len(fixture.query_embedding)
        for intent_embedding in fixture.intent_embeddings
    ):
        raise RoutingConfigurationError(
            "semantic embedding fixture query and intent embeddings must share one dimension"
        )


def _cosine_similarity(
    query_embedding: tuple[Decimal, ...], intent_embedding: tuple[Decimal, ...]
) -> Decimal:
    """검증된 local vector 두 개의 cosine similarity를 고정 Decimal context로 계산한다."""
    # 호출자가 바꾼 전역 Decimal context가 fixture route·감사 점수를 바꾸지 않게 한다.
    with localcontext() as context:
        context.prec = 50
        dot_product = sum(
            (
                query_component * intent_component
                for query_component, intent_component in zip(
                    query_embedding, intent_embedding, strict=True
                )
            ),
            Decimal("0"),
        )
        query_norm_squared = sum(
            (component * component for component in query_embedding), Decimal("0")
        )
        intent_norm_squared = sum(
            (component * component for component in intent_embedding), Decimal("0")
        )
        try:
            similarity = dot_product / (query_norm_squared.sqrt() * intent_norm_squared.sqrt())
        except (InvalidOperation, ValueError) as error:
            raise RoutingConfigurationError(
                "semantic embedding fixture must produce a finite cosine similarity"
            ) from error
    _validate_unit_decimal(similarity, "semantic embedding cosine similarity")
    return similarity
