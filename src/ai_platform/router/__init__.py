"""Volume 08의 결정론적 Router 실습 모듈."""

from ai_platform.router.api import RouterAPI, RouterAPIResponse
from ai_platform.router.audit import (
    UnsafeRouterAuditRecordError,
    serialize_router_audit_report,
    validate_router_audit_record,
    validate_router_audit_report,
)
from ai_platform.router.base import (
    NoEligibleRouteError,
    RouteDecision,
    RouteTarget,
    RouteTargetKind,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
)
from ai_platform.router.escalation import (
    EscalationFixture,
    EscalationRouteExhaustedError,
    MultiStageEscalationRouter,
    MultiStageRouteDecision,
    NoEscalationFixtureError,
    RoutingStage,
)
from ai_platform.router.evaluation import (
    KeywordRoutingEvaluationCase,
    KeywordRoutingEvaluationReport,
    KeywordRoutingExpectation,
    KeywordRoutingOutcome,
    RoutingQualityGateError,
    evaluate_keyword_router,
)
from ai_platform.router.fallback import (
    FallbackRouteDecision,
    FallbackRouteExhaustedError,
    PolicyFallbackRouter,
)
from ai_platform.router.keyword import (
    KeywordRoute,
    KeywordRouteDecision,
    KeywordRouter,
    NoConfidentKeywordRouteError,
)
from ai_platform.router.llm import (
    LLMClassifierResponseFixture,
    LLMRoute,
    LLMRouteDecision,
    LLMRouter,
    NoConfidentLLMRouteError,
    NoLLMClassifierResponseFixtureError,
)
from ai_platform.router.mini_project import RouterMiniProject, build_router_mini_project
from ai_platform.router.policy import PolicyRouter
from ai_platform.router.rule import (
    NoMatchingRuleRouteError,
    RuleRoute,
    RuleRouteDecision,
    RuleRouter,
)
from ai_platform.router.semantic import (
    NoConfidentSemanticRouteError,
    NoSemanticScoreFixtureError,
    SemanticIntentScore,
    SemanticRoute,
    SemanticRouteDecision,
    SemanticRouter,
    SemanticScoreFixture,
)

__all__ = [
    "UnsafeRouterAuditRecordError",
    "serialize_router_audit_report",
    "validate_router_audit_record",
    "validate_router_audit_report",
    "NoEligibleRouteError",
    "NoConfidentKeywordRouteError",
    "NoEscalationFixtureError",
    "NoConfidentLLMRouteError",
    "NoConfidentSemanticRouteError",
    "NoLLMClassifierResponseFixtureError",
    "NoMatchingRuleRouteError",
    "NoSemanticScoreFixtureError",
    "EscalationFixture",
    "EscalationRouteExhaustedError",
    "FallbackRouteDecision",
    "FallbackRouteExhaustedError",
    "KeywordRoute",
    "KeywordRouteDecision",
    "KeywordRouter",
    "KeywordRoutingEvaluationCase",
    "KeywordRoutingEvaluationReport",
    "KeywordRoutingExpectation",
    "KeywordRoutingOutcome",
    "LLMClassifierResponseFixture",
    "LLMRoute",
    "LLMRouteDecision",
    "LLMRouter",
    "MultiStageEscalationRouter",
    "MultiStageRouteDecision",
    "PolicyFallbackRouter",
    "PolicyRouter",
    "RouteDecision",
    "RouteTarget",
    "RouteTargetKind",
    "RuleRoute",
    "RuleRouteDecision",
    "RuleRouter",
    "RouterMiniProject",
    "RouterAPI",
    "RouterAPIResponse",
    "RoutingConfigurationError",
    "RoutingQualityGateError",
    "RoutingRequest",
    "RoutingRequirements",
    "RoutingStage",
    "SemanticIntentScore",
    "SemanticRoute",
    "SemanticRouteDecision",
    "SemanticRouter",
    "SemanticScoreFixture",
    "build_router_mini_project",
    "evaluate_keyword_router",
]
