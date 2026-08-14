"""고정 escalation fixture와 정책 경계를 결합하는 결정론적 다단계 Router."""

from __future__ import annotations

from dataclasses import dataclass

from ai_platform.router.base import (
    NoEligibleRouteError,
    RouteDecision,
    RouteTarget,
    RouteTargetKind,
    RoutingConfigurationError,
    RoutingRequest,
    RoutingRequirements,
)
from ai_platform.router.policy import PolicyRouter


class NoEscalationFixtureError(NoEligibleRouteError):
    """요청 ID에 대응하는 고정 escalation fixture가 없을 때 발생한다."""


class EscalationRouteExhaustedError(NoEligibleRouteError):
    """명시된 escalation budget 안의 모든 stage가 정책상 실패했을 때 발생한다."""

    def __init__(self, *, request_id: str, attempted_stage_names: tuple[str, ...]) -> None:
        """원문 없이 요청 ID와 실제로 시도한 stage 이름만 보관한다."""
        super().__init__("no eligible route found within the configured escalation budget")
        self.request_id = request_id
        self.attempted_stage_names = attempted_stage_names

    def as_log_record(self) -> dict[str, object]:
        """사용자 원문 없이 JSON 직렬화 가능한 fail-closed 로그를 반환한다."""
        return {
            "request_id": self.request_id,
            "outcome": "no_eligible_escalation_route",
            "attempted_stage_names": list(self.attempted_stage_names),
        }


@dataclass(frozen=True, slots=True)
class RoutingStage:
    """한 escalation 단계의 허용 대상과 Agent·Tool·Model 유형을 고정한다."""

    name: str
    target_kind: RouteTargetKind
    policy_router: PolicyRouter
    permitted_target_names: frozenset[str]

    def __post_init__(self) -> None:
        """stage가 policy 내의 같은 유형 대상만 선택하도록 검증한다."""
        _validate_identifier(self.name, "routing stage name")
        if not isinstance(self.target_kind, RouteTargetKind):
            raise RoutingConfigurationError("routing stage target_kind must be a RouteTargetKind")
        if not self.permitted_target_names:
            raise RoutingConfigurationError(
                "routing stage permitted_target_names must not be empty"
            )
        targets_by_name = {target.name: target for target in self.policy_router.targets}
        for target_name in self.permitted_target_names:
            _validate_identifier(target_name, "routing stage permitted target name")
            target = targets_by_name.get(target_name)
            if target is None:
                raise RoutingConfigurationError(
                    "routing stage permitted target names must belong to its policy"
                )
            if target.kind is not self.target_kind:
                raise RoutingConfigurationError(
                    "routing stage permitted targets must match its target_kind"
                )


@dataclass(frozen=True, slots=True)
class EscalationFixture:
    """한 요청 ID가 따를 고정된 Agent·Tool·Model stage 순서를 선언한다."""

    request_id: str
    stage_names: tuple[str, ...]

    def __post_init__(self) -> None:
        """재현 가능한 fixture ID와 중복 없는 stage 순서를 요구한다."""
        _validate_identifier(self.request_id, "escalation fixture request_id")
        if not self.stage_names:
            raise RoutingConfigurationError("escalation fixture stage_names must not be empty")
        for stage_name in self.stage_names:
            _validate_identifier(stage_name, "escalation fixture stage name")
        if len(self.stage_names) != len(set(self.stage_names)):
            raise RoutingConfigurationError("escalation fixture stage_names must be unique")


@dataclass(frozen=True, slots=True)
class MultiStageRouteDecision:
    """성공 stage와 모든 실제 escalation 시도를 보관하는 감사 가능한 결정이다."""

    router_name: str
    stage_name: str
    target_kind: RouteTargetKind
    policy_decision: RouteDecision
    attempted_stage_names: tuple[str, ...]

    def __post_init__(self) -> None:
        """성공 stage가 마지막 시도이며 대상 유형과 일치함을 검증한다."""
        _validate_identifier(self.router_name, "multi-stage router name")
        _validate_identifier(self.stage_name, "routing decision stage name")
        if not isinstance(self.target_kind, RouteTargetKind):
            raise RoutingConfigurationError(
                "routing decision target_kind must be a RouteTargetKind"
            )
        if not self.attempted_stage_names:
            raise RoutingConfigurationError("attempted_stage_names must not be empty")
        for stage_name in self.attempted_stage_names:
            _validate_identifier(stage_name, "attempted stage name")
        if self.attempted_stage_names[-1] != self.stage_name:
            raise RoutingConfigurationError(
                "the successful stage must be the final attempted stage name"
            )
        if self.policy_decision.target.kind is not self.target_kind:
            raise RoutingConfigurationError(
                "the selected target must match the successful stage kind"
            )

    @property
    def target(self) -> RouteTarget:
        """호출자가 최종 policy가 선택한 대상을 바로 확인할 수 있게 한다."""
        return self.policy_decision.target

    @property
    def escalation_count(self) -> int:
        """첫 stage 이후 실제로 소비한 escalation 횟수를 반환한다."""
        return len(self.attempted_stage_names) - 1

    def as_log_record(self) -> dict[str, object]:
        """사용자 원문 없이 JSON 직렬화 가능한 성공 로그를 반환한다."""
        return {
            **self.policy_decision.as_log_record(),
            "multi_stage_router_name": self.router_name,
            "stage_name": self.stage_name,
            "stage_target_kind": self.target_kind.value,
            "escalation_count": self.escalation_count,
            "attempted_stage_names": list(self.attempted_stage_names),
        }


class MultiStageEscalationRouter:
    """고정 fixture가 정한 stage를 정책 경계 안에서 제한적으로 escalation한다.

    fixture는 요청 ID에 따라 Agent·Tool·Model stage의 선언 순서를 제공한다. 첫 stage는 항상
    시도하며, 그 뒤에는 최대 ``escalation_budget``개의 stage만 추가로 시도한다. 각 stage는
    원래 request의 capability·허용 대상·비용·지연 시간 제약을 보존한 새 request를 자기
    policy에 전달한다. 따라서 escalation은 어떠한 정책 제약도 완화하거나 우회할 수 없다.
    """

    def __init__(
        self,
        *,
        name: str,
        stages: tuple[RoutingStage, ...],
        escalation_fixtures: tuple[EscalationFixture, ...],
        escalation_budget: int,
    ) -> None:
        """모호하지 않은 stage·fixture 목록과 명시적인 escalation 예산을 검증한다."""
        _validate_identifier(name, "multi-stage router name")
        if not stages:
            raise RoutingConfigurationError("multi-stage router must contain at least one stage")
        if not escalation_fixtures:
            raise RoutingConfigurationError(
                "multi-stage router must contain at least one escalation fixture"
            )
        if (
            isinstance(escalation_budget, bool)
            or not isinstance(escalation_budget, int)
            or escalation_budget < 0
        ):
            raise RoutingConfigurationError("escalation_budget must be a nonnegative integer")
        stage_names = [stage.name for stage in stages]
        if len(stage_names) != len(set(stage_names)):
            raise RoutingConfigurationError("routing stage names must be unique")
        stage_names_set = set(stage_names)
        fixture_request_ids = [fixture.request_id for fixture in escalation_fixtures]
        if len(fixture_request_ids) != len(set(fixture_request_ids)):
            raise RoutingConfigurationError("escalation fixture request_ids must be unique")
        for fixture in escalation_fixtures:
            if not set(fixture.stage_names).issubset(stage_names_set):
                raise RoutingConfigurationError(
                    "escalation fixture stage_names must match configured routing stages"
                )
        self._name = name
        self._stages_by_name = {stage.name: stage for stage in stages}
        self._fixtures_by_request_id = {
            fixture.request_id: fixture for fixture in escalation_fixtures
        }
        self._escalation_budget = escalation_budget

    def route(self, request: RoutingRequest) -> MultiStageRouteDecision:
        """고정 stage 순서를 예산 안에서 시도하고 실패 시 fail closed 한다."""
        fixture = self._fixtures_by_request_id.get(request.request_id)
        if fixture is None:
            raise NoEscalationFixtureError(
                "no escalation fixture is configured for the routing request"
            )
        stage_names_to_try = fixture.stage_names[: self._escalation_budget + 1]
        attempted_stage_names: list[str] = []
        for stage_name in stage_names_to_try:
            stage = self._stages_by_name[stage_name]
            attempted_stage_names.append(stage.name)
            try:
                policy_decision = stage.policy_router.route(
                    _constrain_request_to_stage(request, stage)
                )
            except NoEligibleRouteError:
                continue
            return MultiStageRouteDecision(
                router_name=self._name,
                stage_name=stage.name,
                target_kind=stage.target_kind,
                policy_decision=policy_decision,
                attempted_stage_names=tuple(attempted_stage_names),
            )
        raise EscalationRouteExhaustedError(
            request_id=request.request_id,
            attempted_stage_names=tuple(attempted_stage_names),
        )


def _constrain_request_to_stage(request: RoutingRequest, stage: RoutingStage) -> RoutingRequest:
    """원래 정책 제약을 보존하면서 stage의 허용 대상으로만 범위를 좁힌다."""
    requirements = request.requirements
    permitted_target_names = stage.permitted_target_names
    if requirements.permitted_target_names is not None:
        permitted_target_names = permitted_target_names & requirements.permitted_target_names
    if not permitted_target_names:
        raise NoEligibleRouteError("no stage target is permitted by the routing request")
    return RoutingRequest(
        request_id=request.request_id,
        text=request.text,
        requirements=RoutingRequirements(
            required_capabilities=requirements.required_capabilities,
            maximum_cost=requirements.maximum_cost,
            maximum_latency_ms=requirements.maximum_latency_ms,
            permitted_target_names=permitted_target_names,
        ),
    )


def _validate_identifier(value: object, name: str) -> None:
    """비어 있거나 문자열이 아닌 식별자를 거부한다."""
    if not isinstance(value, str) or not value.strip():
        raise RoutingConfigurationError(f"{name} must be a nonempty string")
