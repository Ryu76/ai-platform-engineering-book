"""고정 keyword fixture와 정책 Router를 결합하는 결정론적 intent Router."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Final

from ai_platform.router.base import (
    NoEligibleRouteError,
    RouteDecision,
    RouteTarget,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
)
from ai_platform.router.policy import PolicyRouter

_TOKEN_PATTERN: Final = re.compile(r"\w+", re.UNICODE)


class NoConfidentKeywordRouteError(NoEligibleRouteError):
    """일치한 keyword rule이 없거나 신뢰도 기준을 통과하지 못할 때 발생한다."""


@dataclass(frozen=True, slots=True)
class KeywordRoute:
    """한 intent의 단일-token keyword, 신뢰도 및 필수 capability를 고정한다."""

    intent: str
    keywords: frozenset[str]
    required_capabilities: frozenset[str]
    confidence: Decimal

    def __post_init__(self) -> None:
        """문자열 기반 rule을 모호하지 않은 결정론적 fixture로 제한한다."""
        _validate_identifier(self.intent, "intent")
        if not self.keywords:
            raise RoutingConfigurationError("keyword route keywords must not be empty")
        for keyword in self.keywords:
            if len(_tokens(keyword)) != 1:
                raise RoutingConfigurationError(
                    "each keyword must contain exactly one nonempty token"
                )
        if not self.required_capabilities:
            raise RoutingConfigurationError("keyword route capabilities must not be empty")
        for capability in self.required_capabilities:
            _validate_identifier(capability, "keyword route capability")
        _validate_confidence(self.confidence, "keyword route confidence")


@dataclass(frozen=True, slots=True)
class KeywordRouteDecision:
    """Keyword intent 판정과 그 뒤의 정책 대상 선택을 함께 보관한다."""

    router_name: str
    intent: str
    matched_keywords: tuple[str, ...]
    confidence: Decimal
    policy_decision: RouteDecision

    def __post_init__(self) -> None:
        """원문 없이 감사 가능한 classifier 결과만 기록하도록 검증한다."""
        _validate_identifier(self.router_name, "keyword router name")
        _validate_identifier(self.intent, "intent")
        if not self.matched_keywords:
            raise RoutingConfigurationError("matched_keywords must not be empty")
        for keyword in self.matched_keywords:
            if len(_tokens(keyword)) != 1:
                raise RoutingConfigurationError("matched keyword must contain exactly one token")
        _validate_confidence(self.confidence, "keyword decision confidence")

    @property
    def target(self) -> RouteTarget:
        """호출자가 정책 Router가 선택한 대상을 바로 확인할 수 있게 한다."""
        return self.policy_decision.target

    def as_log_record(self) -> dict[str, object]:
        """사용자 원문 없이 JSON 직렬화 가능한 합성 결정 로그를 반환한다."""
        return {
            **self.policy_decision.as_log_record(),
            "classifier_name": self.router_name,
            "intent": self.intent,
            "classifier_confidence": str(self.confidence),
            "matched_keywords": list(self.matched_keywords),
        }


class KeywordRouter:
    """고정 token rule을 confidence threshold로 판정한 뒤 PolicyRouter에 위임한다.

    동일 요청은 confidence, 일치 keyword 수, intent 이름 순으로 같은 rule을 선택한다.
    선택된 intent의 capability는 원래 요청의 capability와 합쳐져 정책 Router에서 다시
    권한·상태·비용·지연 시간 조건을 검사한다.
    """

    def __init__(
        self,
        *,
        name: str,
        policy_router: PolicyRouter,
        routes: tuple[KeywordRoute, ...],
        minimum_confidence: Decimal,
    ) -> None:
        """명시적인 threshold와 중복 없는 intent fixture를 검증한다."""
        _validate_identifier(name, "keyword router name")
        if not routes:
            raise RoutingConfigurationError("keyword router must contain at least one route")
        intents = [route.intent for route in routes]
        if len(intents) != len(set(intents)):
            raise RoutingConfigurationError("keyword route intents must be unique")
        _validate_confidence(minimum_confidence, "minimum_confidence")
        self._name = name
        self._policy_router = policy_router
        self._routes = routes
        self._minimum_confidence = minimum_confidence

    def route(self, request: RoutingRequest) -> KeywordRouteDecision:
        """최고 confidence keyword intent를 정책 제약 안에서 실행 대상으로 변환한다."""
        request_tokens = frozenset(_tokens(request.text))
        matches = [
            (route, tuple(sorted(_normalized_keywords(route) & request_tokens)))
            for route in self._routes
        ]
        eligible_matches = [
            (route, matched_keywords)
            for route, matched_keywords in matches
            if matched_keywords and route.confidence >= self._minimum_confidence
        ]
        if not eligible_matches:
            raise NoConfidentKeywordRouteError(
                "no keyword route meets the configured confidence threshold"
            )
        selected_route, matched_keywords = min(
            eligible_matches,
            key=lambda match: (-match[0].confidence, -len(match[1]), match[0].intent),
        )
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
        policy_decision = self._policy_router.route(constrained_request)
        return KeywordRouteDecision(
            router_name=self._name,
            intent=selected_route.intent,
            matched_keywords=matched_keywords,
            confidence=selected_route.confidence,
            policy_decision=policy_decision,
        )


def _normalized_keywords(route: KeywordRoute) -> frozenset[str]:
    """검증된 rule keyword를 case-folded token 집합으로 반환한다."""
    return frozenset(_tokens(keyword)[0] for keyword in route.keywords)


def _tokens(text: str) -> tuple[str, ...]:
    """공백·대소문자·문장부호 차이를 제거한 Unicode token을 반환한다."""
    return tuple(token.casefold() for token in _TOKEN_PATTERN.findall(text))


def _validate_identifier(value: object, name: str) -> None:
    """비어 있거나 문자열이 아닌 식별자를 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise RoutingConfigurationError(f"{name} must be a nonempty string")


def _validate_confidence(value: object, name: str) -> None:
    """threshold와 rule confidence를 유한한 Decimal 0 이상 1 이하로 제한한다."""
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
