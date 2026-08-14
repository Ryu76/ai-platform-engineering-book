"""Volume 08의 고정 fixture Router들을 하나의 로컬 미니 프로젝트로 조합한다."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ai_platform.router.api import RouterAPI
from ai_platform.router.audit import (
    serialize_router_audit_report,
    validate_router_audit_report,
)
from ai_platform.router.base import (
    RouteTarget,
    RouteTargetKind,
    RoutingRequest,
    RoutingRequirements,
)
from ai_platform.router.escalation import (
    EscalationFixture,
    MultiStageEscalationRouter,
    RoutingStage,
)
from ai_platform.router.fallback import PolicyFallbackRouter
from ai_platform.router.keyword import KeywordRoute, KeywordRouter
from ai_platform.router.llm import (
    LLMClassifierResponseFixture,
    LLMRoute,
    LLMRouter,
)
from ai_platform.router.policy import PolicyRouter
from ai_platform.router.rule import RuleRoute, RuleRouter
from ai_platform.router.semantic import (
    SemanticIntentScore,
    SemanticRoute,
    SemanticRouter,
    SemanticScoreFixture,
)


@dataclass(frozen=True, slots=True)
class RouterMiniProject:
    """하나의 고정 요청 집합을 각 Router 계약에 전달하는 로컬 실습 조합이다."""

    policy_router: PolicyRouter
    rule_router: RuleRouter
    keyword_router: KeywordRouter
    semantic_router: SemanticRouter
    llm_router: LLMRouter
    fallback_router: PolicyFallbackRouter
    escalation_router: MultiStageEscalationRouter
    api: RouterAPI

    def run(self) -> dict[str, object]:
        """외부 호출 없이 모든 결정의 원문 없는 JSON 가능 감사 결과를 반환한다."""
        policy_request = _request("mini-policy-001", "private general support request")
        rule_request = RoutingRequest(
            request_id="mini-rule-001",
            text="private billing rule request",
            requirements=RoutingRequirements(
                required_capabilities=frozenset({"billing", "respond"}),
                maximum_cost=Decimal("0.005"),
                maximum_latency_ms=100,
                permitted_target_names=frozenset({"mini-rule-billing-agent"}),
            ),
        )
        keyword_request = _request("mini-keyword-001", "private order tracking request")
        semantic_request = _request("mini-semantic-001", "private refund request")
        llm_request = _request("mini-llm-001", "private priority request")
        fallback_request = _request("mini-fallback-001", "private fallback request")
        escalation_request = _request(
            "mini-escalation-001",
            "private escalation request",
            permitted_target_names=frozenset({"mini-summary-model"}),
        )
        api_request_text = "private API order request"
        api_request_body = {
            "request_id": "mini-api-001",
            "text": api_request_text,
            "requirements": {
                "required_capabilities": ["lookup_order", "respond"],
                "maximum_cost": "0.004",
                "maximum_latency_ms": 80,
                "permitted_target_names": ["mini-api-order-agent"],
            },
        }
        policy_decision = self.policy_router.route(policy_request)
        rule_decision = self.rule_router.route(rule_request)
        keyword_decision = self.keyword_router.route(keyword_request)
        semantic_decision = self.semantic_router.route(semantic_request)
        llm_decision = self.llm_router.route(llm_request)
        fallback_decision = self.fallback_router.route(fallback_request)
        escalation_decision = self.escalation_router.route(escalation_request)
        api_response = self.api.route_post(api_request_body)
        report = {
            "policy": policy_decision.as_log_record(),
            "rule": rule_decision.as_log_record(),
            "keyword": keyword_decision.as_log_record(),
            "semantic": semantic_decision.as_log_record(),
            "llm": llm_decision.as_log_record(),
            "fallback": fallback_decision.as_log_record(),
            "escalation": escalation_decision.as_log_record(),
            "api": {"status_code": api_response.status_code, "body": api_response.body},
        }
        validate_router_audit_report(
            report,
            sensitive_values_by_route={
                "policy": (policy_request.text,),
                "rule": (rule_request.text,),
                "keyword": (keyword_request.text,),
                "semantic": (semantic_request.text,),
                "llm": (llm_request.text,),
                "fallback": (fallback_request.text,),
                "escalation": (escalation_request.text,),
                "api": (api_request_text,),
            },
        )
        return report

    def render_audit_report(self) -> str:
        """모든 고정 경로를 재검증한 canonical strict JSON audit report를 반환한다."""
        return serialize_router_audit_report(
            self.run(), sensitive_values_by_route=_mini_project_sensitive_values()
        )


def build_router_mini_project() -> RouterMiniProject:
    """고정 policy·classifier·fallback·escalation fixture를 안전한 로컬 조합으로 만든다."""
    policy_router = PolicyRouter(
        name="mini-policy-router",
        targets=(
            _target("mini-policy-agent", RouteTargetKind.AGENT, {"respond"}, "0.002", 50),
            _target("mini-policy-model", RouteTargetKind.MODEL, {"respond"}, "0.004", 90),
        ),
    )
    rule_router = RuleRouter(
        name="mini-rule-router",
        policy_router=PolicyRouter(
            name="mini-rule-policy",
            targets=(
                _target(
                    "mini-rule-billing-agent",
                    RouteTargetKind.AGENT,
                    {"billing", "refund", "respond"},
                    "0.003",
                    70,
                ),
            ),
        ),
        routes=(
            RuleRoute(
                name="billing-support",
                required_request_capabilities=frozenset({"billing"}),
                added_required_capabilities=frozenset({"refund"}),
                priority=10,
            ),
        ),
    )
    keyword_router = KeywordRouter(
        name="mini-keyword-router",
        policy_router=PolicyRouter(
            name="mini-keyword-policy",
            targets=(
                _target(
                    "mini-order-agent",
                    RouteTargetKind.AGENT,
                    {"lookup_order", "respond"},
                    "0.003",
                    70,
                ),
            ),
        ),
        routes=(
            KeywordRoute(
                intent="order_tracking",
                keywords=frozenset({"order", "tracking"}),
                required_capabilities=frozenset({"lookup_order", "respond"}),
                confidence=Decimal("0.90"),
            ),
        ),
        minimum_confidence=Decimal("0.80"),
    )
    semantic_router = SemanticRouter(
        name="mini-semantic-router",
        policy_router=PolicyRouter(
            name="mini-semantic-policy",
            targets=(
                _target(
                    "mini-refund-agent",
                    RouteTargetKind.AGENT,
                    {"issue_refund", "respond"},
                    "0.003",
                    75,
                ),
            ),
        ),
        routes=(
            SemanticRoute(
                intent="refund",
                required_capabilities=frozenset({"issue_refund", "respond"}),
            ),
        ),
        score_fixtures=(
            SemanticScoreFixture(
                request_id="mini-semantic-001",
                intent_scores=(SemanticIntentScore(intent="refund", similarity=Decimal("0.93")),),
            ),
        ),
        minimum_similarity=Decimal("0.85"),
    )
    llm_router = LLMRouter(
        name="mini-llm-router",
        policy_router=PolicyRouter(
            name="mini-llm-policy",
            targets=(
                _target(
                    "mini-priority-agent",
                    RouteTargetKind.AGENT,
                    {"priority_support", "respond"},
                    "0.004",
                    80,
                ),
            ),
        ),
        routes=(
            LLMRoute(
                intent="priority_support",
                required_capabilities=frozenset({"priority_support", "respond"}),
            ),
        ),
        response_fixtures=(
            LLMClassifierResponseFixture(
                request_id="mini-llm-001",
                intent="priority_support",
                confidence=Decimal("0.92"),
            ),
        ),
        minimum_confidence=Decimal("0.85"),
    )
    fallback_router = PolicyFallbackRouter(
        name="mini-fallback-router",
        primary_router=PolicyRouter(
            name="mini-primary-policy",
            targets=(
                _target(
                    "mini-unhealthy-primary-agent",
                    RouteTargetKind.AGENT,
                    {"respond"},
                    "0.001",
                    40,
                    healthy=False,
                ),
            ),
        ),
        fallback_routers=(
            PolicyRouter(
                name="mini-fallback-policy",
                targets=(
                    _target(
                        "mini-fallback-agent",
                        RouteTargetKind.AGENT,
                        {"respond"},
                        "0.002",
                        60,
                    ),
                ),
            ),
        ),
        retry_budget=1,
    )
    escalation_router = MultiStageEscalationRouter(
        name="mini-escalation-router",
        stages=(
            _stage(
                "mini-agent-stage",
                _target(
                    "mini-triage-agent",
                    RouteTargetKind.AGENT,
                    {"respond"},
                    "0.001",
                    40,
                    healthy=False,
                ),
            ),
            _stage(
                "mini-tool-stage",
                _target(
                    "mini-order-tool",
                    RouteTargetKind.TOOL,
                    {"respond"},
                    "0.002",
                    60,
                    healthy=False,
                ),
            ),
            _stage(
                "mini-model-stage",
                _target(
                    "mini-summary-model",
                    RouteTargetKind.MODEL,
                    {"respond"},
                    "0.004",
                    90,
                ),
            ),
        ),
        escalation_fixtures=(
            EscalationFixture(
                request_id="mini-escalation-001",
                stage_names=("mini-agent-stage", "mini-tool-stage", "mini-model-stage"),
            ),
        ),
        escalation_budget=2,
    )
    api = RouterAPI(
        policy_router=PolicyRouter(
            name="mini-api-policy",
            targets=(
                _target(
                    "mini-api-order-agent",
                    RouteTargetKind.AGENT,
                    {"lookup_order", "respond"},
                    "0.003",
                    70,
                ),
            ),
        )
    )
    return RouterMiniProject(
        policy_router=policy_router,
        rule_router=rule_router,
        keyword_router=keyword_router,
        semantic_router=semantic_router,
        llm_router=llm_router,
        fallback_router=fallback_router,
        escalation_router=escalation_router,
        api=api,
    )


def _request(
    request_id: str,
    text: str,
    *,
    permitted_target_names: frozenset[str] | None = None,
) -> RoutingRequest:
    """모든 미니 프로젝트 요청에 같은 비용·지연 시간·capability 정책을 적용한다."""
    return RoutingRequest(
        request_id=request_id,
        text=text,
        requirements=RoutingRequirements(
            required_capabilities=frozenset({"respond"}),
            maximum_cost=Decimal("0.005"),
            maximum_latency_ms=100,
            permitted_target_names=permitted_target_names,
        ),
    )


def _mini_project_sensitive_values() -> dict[str, tuple[str]]:
    """고정 경로별 원문을 export 직전 privacy 검증에만 제공한다."""
    return {
        "policy": ("private general support request",),
        "rule": ("private billing rule request",),
        "keyword": ("private order tracking request",),
        "semantic": ("private refund request",),
        "llm": ("private priority request",),
        "fallback": ("private fallback request",),
        "escalation": ("private escalation request",),
        "api": ("private API order request",),
    }


def _target(
    name: str,
    kind: RouteTargetKind,
    capabilities: set[str],
    cost: str,
    latency_ms: int,
    *,
    healthy: bool = True,
) -> RouteTarget:
    """고정 비용·지연 시간·상태를 가진 fixture target을 만든다."""
    return RouteTarget(
        name=name,
        kind=kind,
        capabilities=frozenset(capabilities),
        estimated_cost=Decimal(cost),
        estimated_latency_ms=latency_ms,
        healthy=healthy,
    )


def _stage(name: str, target: RouteTarget) -> RoutingStage:
    """target 종류와 정책 소속을 다시 검증하는 고정 escalation stage를 만든다."""
    return RoutingStage(
        name=name,
        target_kind=target.kind,
        policy_router=PolicyRouter(name=f"{name}-policy", targets=(target,)),
        permitted_target_names=frozenset({target.name}),
    )
