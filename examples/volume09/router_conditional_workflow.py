"""낮은 신뢰도의 Router 입력이 사람 검토와 위험 작업 승인을 모두 요구함을 보인다."""
from __future__ import annotations

from ai_platform.graph import ActionKind, RoutedWorkflow, RouteKind, RouterDecision


def show(*, label: str, status: str, events: list[str]) -> None:
    """상태 전이만 안정적으로 출력한다."""
    print(f"{label}: status={status}")
    print(f"events={' | '.join(events)}")


def main() -> None:
    """조건 Edge가 Router 검토와 실행 승인을 분리하는 오프라인 흐름을 실행한다."""
    workflow = RoutedWorkflow(confidence_threshold=0.80)
    route_waiting = workflow.invoke(
        run_id="router-demo-001",
        task="학습용 메시지를 전송한다",
        action=ActionKind.SEND,
        router_decision=RouterDecision(route=RouteKind.REVIEW, confidence=0.55),
    )
    show(
        label="Router 검토 전",
        status=route_waiting.status,
        events=[event.node for event in route_waiting.events],
    )

    approval_waiting = workflow.review_route(run_id="router-demo-001", route=RouteKind.REVIEW)
    show(
        label="경로 검토 후",
        status=approval_waiting.status,
        events=[event.node for event in approval_waiting.events],
    )

    rejected = workflow.resume(run_id="router-demo-001", approved=False)
    show(
        label="실행 거절 후",
        status=rejected.status,
        events=[event.node for event in rejected.events],
    )


if __name__ == "__main__":
    main()
