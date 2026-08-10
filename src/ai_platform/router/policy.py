"""Capability·cost·latency 제약으로 대상을 결정론적으로 선택하는 정책 Router."""

from __future__ import annotations

from collections.abc import Sequence

from ai_platform.router.base import (
    NoEligibleRouteError,
    RouteDecision,
    RouteTarget,
    RoutingConfigurationError,
    RoutingRequest,
)


class PolicyRouter:
    """외부 API 없이 고정 대상 목록과 요청 조건을 비교하는 Router다.

    모든 조건을 만족하는 정상 대상 중 추정 비용, 추정 지연 시간, 대상 이름 순으로
    가장 작은 값을 선택한다. 따라서 입력과 대상 목록이 같으면 결정도 항상 같다.
    """

    def __init__(self, *, name: str, targets: Sequence[RouteTarget]) -> None:
        """정책 이름과 중복 없는 대상 목록을 검증해 고정한다."""
        if not isinstance(name, str) or not name.strip():
            raise RoutingConfigurationError("policy name must be a nonempty string")
        if not targets:
            raise RoutingConfigurationError("policy must contain at least one target")
        names = [target.name for target in targets]
        if len(names) != len(set(names)):
            raise RoutingConfigurationError("target names must be unique within a policy")
        self._name = name
        self._targets = tuple(targets)

    @property
    def name(self) -> str:
        """결정 로그에 사용할 사람이 읽을 수 있는 정책 이름을 반환한다."""
        return self._name

    @property
    def targets(self) -> tuple[RouteTarget, ...]:
        """상위 Router가 stage 계약을 검증할 수 있게 불변 대상 목록을 반환한다."""
        return self._targets

    def route(self, request: RoutingRequest) -> RouteDecision:
        """요청 조건을 모두 통과한 가장 경제적인 정상 대상을 선택한다."""
        candidates = [target for target in self._targets if self._is_eligible(target, request)]
        if not candidates:
            raise NoEligibleRouteError("no healthy target meets the routing requirements")
        selected = min(
            candidates,
            key=lambda target: (
                target.estimated_cost,
                target.estimated_latency_ms,
                target.name,
            ),
        )
        return RouteDecision(
            request_id=request.request_id,
            policy_name=self._name,
            target=selected,
            reason="healthy-capability-cost-latency-policy",
        )

    @staticmethod
    def _is_eligible(target: RouteTarget, request: RoutingRequest) -> bool:
        """권한, 상태, 기능, 비용, 지연 시간 조건을 순서대로 검사한다."""
        requirements = request.requirements
        if not target.healthy:
            return False
        if (
            requirements.permitted_target_names is not None
            and target.name not in requirements.permitted_target_names
        ):
            return False
        if not requirements.required_capabilities.issubset(target.capabilities):
            return False
        if (
            requirements.maximum_cost is not None
            and target.estimated_cost > requirements.maximum_cost
        ):
            return False
        return (
            requirements.maximum_latency_ms is None
            or target.estimated_latency_ms <= requirements.maximum_latency_ms
        )
