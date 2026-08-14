"""Volume 09 오프라인 상태형 Workflow의 안전 계약을 검사한다."""
from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from pydantic import ValidationError

from ai_platform.graph import (
    ActionKind,
    ApprovalRequest,
    DeterministicWorkflow,
    JsonFileCheckpointer,
    MemoryCheckpointer,
    PlannerDeveloperReviewerWorkflow,
    RetryPlan,
    RetryWorkflow,
    ReviewDecision,
    RoutedWorkflow,
    RouteKind,
    RouterDecision,
    RunIdPath,
    StartWorkflowRequest,
    StreamingWorkflow,
    SubgraphWorkflow,
    WorkflowApiAdapter,
    WorkflowEvent,
    WorkflowRunConflictError,
    WorkflowState,
    WorkflowStatus,
    reduce_events,
)


def test_safe_action_reaches_end_without_human_approval() -> None:
    """읽기 작업은 START부터 END까지 결정론적으로 완료한다."""
    workflow = DeterministicWorkflow()

    state = workflow.invoke(run_id="safe-001", task="로컬 문서를 읽는다", action=ActionKind.READ)

    assert state.status is WorkflowStatus.COMPLETED
    assert state.approval_required is False
    assert state.approval_granted is None
    assert state.result == "오프라인 시뮬레이션 완료: read / 로컬 문서를 읽는다"
    assert [event.node for event in state.events] == ["plan", "approval", "execute"]


def test_risky_action_interrupts_before_execution_and_can_resume_after_approval() -> None:
    """배포는 명시적 사람 승인 전에는 결과를 만들거나 실행하지 않는다."""
    workflow = DeterministicWorkflow()

    waiting = workflow.invoke(
        run_id="deploy-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.result is None
    assert waiting.approval_granted is None
    assert [event.node for event in waiting.events] == ["plan", "approval"]
    assert workflow.checkpoint(run_id="deploy-001") == waiting

    completed = workflow.resume(run_id="deploy-001", approved=True)

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.approval_granted is True
    assert completed.result == "오프라인 시뮬레이션 완료: deploy / 학습용 배포를 준비한다"
    assert [event.node for event in completed.events] == ["plan", "approval", "approval", "execute"]


def test_rejected_risky_action_stops_without_execution() -> None:
    """거절 결정은 END의 rejected 상태로 끝나며 execute Node에 닿지 않는다."""
    workflow = DeterministicWorkflow()
    workflow.invoke(run_id="delete-001", task="임시 파일을 삭제한다", action=ActionKind.DELETE)

    rejected = workflow.resume(run_id="delete-001", approved=False)

    assert rejected.status is WorkflowStatus.REJECTED
    assert rejected.approval_granted is False
    assert rejected.result is None
    assert [event.node for event in rejected.events] == ["plan", "approval", "approval"]


def test_resume_requires_an_existing_waiting_checkpoint() -> None:
    """없는 실행 ID나 완료된 Workflow는 재개할 수 없다."""
    workflow = DeterministicWorkflow()

    with pytest.raises(KeyError, match="checkpoint not found"):
        workflow.resume(run_id="missing", approved=True)

    workflow.invoke(run_id="complete-001", task="로컬 문서를 읽는다", action=ActionKind.READ)
    with pytest.raises(ValueError, match="waiting state"):
        workflow.resume(run_id="complete-001", approved=True)


def test_state_rejects_empty_task() -> None:
    """상태 입력 검증이 빈 작업을 Node까지 전달하지 않는다."""
    with pytest.raises(ValueError, match="task must not be empty"):
        WorkflowState.start(task="  ", action=ActionKind.READ)


def test_event_reducer_appends_local_node_updates_in_a_contiguous_audit_order() -> None:
    """Reducer는 Node별 로컬 이벤트를 기존 감사 로그 뒤에 결정론적으로 병합한다."""
    existing = (WorkflowEvent(sequence=1, node="plan", detail="계획"),)
    updates = (
        WorkflowEvent(sequence=1, node="approval", detail="안전 작업 확인"),
        WorkflowEvent(sequence=2, node="execute", detail="오프라인 완료"),
    )

    merged = reduce_events(existing, updates)

    assert [event.sequence for event in merged] == [1, 2, 3]
    assert [event.node for event in merged] == ["plan", "approval", "execute"]
    assert [event.detail for event in merged] == ["계획", "안전 작업 확인", "오프라인 완료"]


def test_event_reducer_rejects_non_contiguous_existing_or_local_update_sequences() -> None:
    """모호한 이벤트 순서는 reducer 경계에서 명시적으로 거부한다."""
    invalid_existing = (WorkflowEvent(sequence=2, node="plan", detail="계획"),)
    valid_update = (WorkflowEvent(sequence=1, node="approval", detail="확인"),)

    with pytest.raises(ValueError, match="existing events"):
        reduce_events(invalid_existing, valid_update)

    invalid_updates = (WorkflowEvent(sequence=2, node="approval", detail="확인"),)
    with pytest.raises(ValueError, match="event updates"):
        reduce_events((), invalid_updates)


def test_high_confidence_router_decision_uses_selected_specialist_node() -> None:
    """신뢰도 높은 Router 입력은 조건 Edge로 개발 Node를 선택해 완료한다."""
    workflow = RoutedWorkflow(confidence_threshold=0.80)

    completed = workflow.invoke(
        run_id="route-001",
        task="로컬 문자열을 정규화한다",
        action=ActionKind.TRANSFORM,
        router_decision=RouterDecision(route=RouteKind.DEVELOPMENT, confidence=0.92),
    )

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.selected_route is RouteKind.DEVELOPMENT
    assert completed.result == "오프라인 시뮬레이션 완료: transform / 로컬 문자열을 정규화한다"
    assert [event.node for event in completed.events] == [
        "plan",
        "router",
        "development",
        "approval",
        "execute",
    ]


def test_missing_router_decision_waits_for_human_route_review_then_completes() -> None:
    """Router 입력이 없으면 전문 Node나 execute 전에 사람 경로 검토에서 중단한다."""
    workflow = RoutedWorkflow()

    waiting = workflow.invoke(
        run_id="route-missing-001",
        task="로컬 문서의 근거를 조사한다",
        action=ActionKind.READ,
        router_decision=None,
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_ROUTE_REVIEW
    assert waiting.selected_route is None
    assert waiting.result is None
    assert [event.node for event in waiting.events] == ["plan", "router"]

    completed = workflow.review_route(run_id="route-missing-001", route=RouteKind.RESEARCH)

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.selected_route is RouteKind.RESEARCH
    assert [event.node for event in completed.events] == [
        "plan",
        "router",
        "route_review",
        "research",
        "approval",
        "execute",
    ]


def test_low_confidence_risky_route_needs_route_review_and_separate_approval() -> None:
    """낮은 신뢰도와 위험 작업은 사람 경로 검토와 실행 승인을 모두 요구한다."""
    workflow = RoutedWorkflow(confidence_threshold=0.80)
    waiting = workflow.invoke(
        run_id="route-risky-001",
        task="학습용 메시지를 전송한다",
        action=ActionKind.SEND,
        router_decision=RouterDecision(route=RouteKind.REVIEW, confidence=0.79),
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_ROUTE_REVIEW
    assert "execute" not in [event.node for event in waiting.events]

    awaiting_approval = workflow.review_route(
        run_id="route-risky-001", route=RouteKind.REVIEW
    )

    assert awaiting_approval.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert awaiting_approval.approval_granted is None
    assert "execute" not in [event.node for event in awaiting_approval.events]

    rejected = workflow.resume(run_id="route-risky-001", approved=False)

    assert rejected.status is WorkflowStatus.REJECTED
    assert "execute" not in [event.node for event in rejected.events]


def test_router_decision_rejects_invalid_confidence() -> None:
    """Router 입력은 Node 실행 전에 유효한 신뢰도 범위를 강제한다."""
    with pytest.raises(ValueError, match="router confidence"):
        RouterDecision(route=RouteKind.RESEARCH, confidence=1.01)


def test_planner_developer_reviewer_safe_workflow_completes_in_role_order() -> None:
    """검토를 통과한 안전 작업은 고정된 역할 순서로 오프라인 완료한다."""
    workflow = PlannerDeveloperReviewerWorkflow()

    completed = workflow.invoke(
        run_id="pdr-safe-001",
        task="로컬 문자열을 정규화하는 초안을 검토한다",
        action=ActionKind.TRANSFORM,
        review_decision=ReviewDecision(approved=True, feedback="테스트 가능한 초안입니다."),
    )

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.review_approved is True
    assert completed.approval_granted is None
    assert [event.node for event in completed.events] == [
        "plan",
        "developer",
        "reviewer",
        "approval",
        "execute",
    ]


def test_reviewer_rejection_ends_before_approval_and_execution() -> None:
    """Reviewer 거절은 실행 권한이나 execute Node 없이 별도 END로 끝난다."""
    workflow = PlannerDeveloperReviewerWorkflow()

    rejected = workflow.invoke(
        run_id="pdr-review-rejected-001",
        task="학습용 변경 초안을 검토한다",
        action=ActionKind.DEPLOY,
        review_decision=ReviewDecision(approved=False, feedback="영향 범위가 빠졌습니다."),
    )

    assert rejected.status is WorkflowStatus.REVIEW_REJECTED
    assert rejected.review_approved is False
    assert rejected.approval_granted is None
    assert rejected.result is None
    assert [event.node for event in rejected.events] == ["plan", "developer", "reviewer"]


def test_risky_reviewed_workflow_requires_separate_human_approval() -> None:
    """Reviewer 통과는 위험 작업의 사람 실행 승인을 대체하지 않는다."""
    workflow = PlannerDeveloperReviewerWorkflow()
    waiting = workflow.invoke(
        run_id="pdr-risky-001",
        task="학습용 배포 초안을 검토한다",
        action=ActionKind.DEPLOY,
        review_decision=ReviewDecision(approved=True, feedback="롤백 절차가 명확합니다."),
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.review_approved is True
    assert waiting.approval_granted is None
    assert [event.node for event in waiting.events] == [
        "plan",
        "developer",
        "reviewer",
        "approval",
    ]
    assert "execute" not in [event.node for event in waiting.events]

    completed = workflow.resume(run_id="pdr-risky-001", approved=True)

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.approval_granted is True
    assert [event.node for event in completed.events] == [
        "plan",
        "developer",
        "reviewer",
        "approval",
        "approval",
        "execute",
    ]


def test_review_decision_rejects_blank_audit_fields() -> None:
    """Reviewer 판정은 재현 가능한 감사 근거와 출처를 요구한다."""
    with pytest.raises(ValueError, match="review feedback"):
        ReviewDecision(approved=True, feedback=" ")

    with pytest.raises(ValueError, match="review source"):
        ReviewDecision(approved=True, feedback="통과", source=" ")


def test_subgraph_workflow_keeps_risky_action_at_parent_approval_boundary() -> None:
    """Subgraph의 검토 통과 뒤에도 부모 Workflow만 실행 승인 interrupt를 만든다."""
    workflow = SubgraphWorkflow()

    waiting = workflow.invoke(
        run_id="subgraph-risky-001",
        task="학습용 배포 초안을 검토한다",
        action=ActionKind.DEPLOY,
        review_decision=ReviewDecision(approved=True, feedback="검토 기준을 충족합니다."),
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.review_approved is True
    assert waiting.approval_granted is None
    assert [event.node for event in waiting.events] == [
        "plan",
        "developer",
        "reviewer",
        "approval",
    ]
    assert "execute" not in [event.node for event in waiting.events]
    assert workflow.checkpoint(run_id="subgraph-risky-001") == waiting

    completed = workflow.resume(run_id="subgraph-risky-001", approved=True)

    assert completed.status is WorkflowStatus.COMPLETED
    assert [event.node for event in completed.events] == [
        "plan",
        "developer",
        "reviewer",
        "approval",
        "approval",
        "execute",
    ]


def test_subgraph_workflow_stops_at_reviewer_rejection_before_parent_approval() -> None:
    """Subgraph 거절은 부모 Approval Node와 execute Node를 모두 건너뛴다."""
    rejected = SubgraphWorkflow().invoke(
        run_id="subgraph-rejected-001",
        task="학습용 배포 초안을 검토한다",
        action=ActionKind.DEPLOY,
        review_decision=ReviewDecision(approved=False, feedback="영향 범위가 빠졌습니다."),
    )

    assert rejected.status is WorkflowStatus.REVIEW_REJECTED
    assert [event.node for event in rejected.events] == ["plan", "developer", "reviewer"]
    assert "approval" not in [event.node for event in rejected.events]
    assert "execute" not in [event.node for event in rejected.events]


def test_retry_workflow_recovers_within_its_fixed_retry_limit() -> None:
    """첫 실패 뒤 Error Node가 허용한 한 번의 재시도로 안전 작업을 완료한다."""
    workflow = RetryWorkflow()

    completed = workflow.invoke(
        run_id="retry-recover-001",
        task="로컬 문자열을 변환한다",
        action=ActionKind.TRANSFORM,
        retry_plan=RetryPlan(failures_before_success=1, max_retries=1),
    )

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.attempt_count == 2
    assert [event.node for event in completed.events] == [
        "plan",
        "approval",
        "execute",
        "error",
        "execute",
    ]


def test_retry_workflow_ends_at_error_node_when_retry_limit_is_exhausted() -> None:
    """실패가 상한을 넘으면 추가 시도 없이 FAILED END로 종료한다."""
    failed = RetryWorkflow().invoke(
        run_id="retry-failed-001",
        task="로컬 문자열을 변환한다",
        action=ActionKind.TRANSFORM,
        retry_plan=RetryPlan(failures_before_success=2, max_retries=1),
    )

    assert failed.status is WorkflowStatus.FAILED
    assert failed.result is None
    assert failed.attempt_count == 2
    assert [event.node for event in failed.events] == [
        "plan",
        "approval",
        "execute",
        "error",
        "execute",
        "error",
    ]


def test_retry_workflow_requires_approval_before_a_risky_attempt_or_retry() -> None:
    """위험 작업은 재시도 계획이 있어도 승인 전에는 실행 시도를 시작하지 않는다."""
    workflow = RetryWorkflow()
    waiting = workflow.invoke(
        run_id="retry-risky-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
        retry_plan=RetryPlan(failures_before_success=1, max_retries=1),
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.attempt_count == 0
    assert "execute" not in [event.node for event in waiting.events]

    rejected = workflow.resume(run_id="retry-risky-001", approved=False)

    assert rejected.status is WorkflowStatus.REJECTED
    assert rejected.attempt_count == 0
    assert "execute" not in [event.node for event in rejected.events]


def test_retry_plan_rejects_negative_limits_and_blank_source() -> None:
    """재시도 입력은 재현 가능한 양수 범위와 감사 출처를 강제한다."""
    with pytest.raises(ValueError, match="failures_before_success"):
        RetryPlan(failures_before_success=-1, max_retries=0)

    with pytest.raises(ValueError, match="max_retries"):
        RetryPlan(failures_before_success=0, max_retries=-1)

    with pytest.raises(ValueError, match="retry source"):
        RetryPlan(failures_before_success=0, max_retries=0, source=" ")


def test_json_file_checkpoint_survives_a_new_workflow_instance_and_keeps_approval_gate(
    tmp_path: Path,
) -> None:
    """로컬 JSON Checkpoint는 새 인스턴스에서도 위험 작업의 승인 대기를 보존한다."""
    checkpoint_path = tmp_path / "volume09-checkpoints.json"
    waiting = DeterministicWorkflow(
        checkpointer=JsonFileCheckpointer(path=checkpoint_path)
    ).invoke(
        run_id="persistent-deploy-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )

    restored_workflow = DeterministicWorkflow(
        checkpointer=JsonFileCheckpointer(path=checkpoint_path)
    )
    restored = restored_workflow.checkpoint(run_id="persistent-deploy-001")

    assert restored == waiting
    assert restored.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert "execute" not in [event.node for event in restored.events]

    completed = restored_workflow.resume(run_id="persistent-deploy-001", approved=True)

    assert completed.status is WorkflowStatus.COMPLETED
    assert [event.node for event in completed.events] == [
        "plan", "approval", "approval", "execute"
    ]


def test_json_file_checkpoint_rejects_suspected_sensitive_state_text(tmp_path: Path) -> None:
    """영속 Checkpointer는 자격 증명처럼 보이는 텍스트를 파일에 쓰지 않는다."""
    checkpoint_path = tmp_path / "volume09-checkpoints.json"
    checkpointer = JsonFileCheckpointer(path=checkpoint_path)
    state = WorkflowState.start(
        task="sk-" + "offline-value",
        action=ActionKind.READ,
    )

    with pytest.raises(ValueError, match="suspected sensitive data"):
        checkpointer.save(run_id="persistent-safe-001", state=state)

    assert not checkpoint_path.exists()


def test_json_file_checkpoint_rejects_a_corrupt_payload(tmp_path: Path) -> None:
    """부분 기록되었거나 변조된 JSON은 재개 전에 명시적으로 실패한다."""
    checkpoint_path = tmp_path / "volume09-checkpoints.json"
    checkpoint_path.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="not valid JSON"):
        JsonFileCheckpointer(path=checkpoint_path).load(run_id="persistent-safe-001")


def test_json_file_checkpoint_rejects_a_valid_json_payload_with_a_stale_checksum(
    tmp_path: Path,
) -> None:
    """유효한 JSON이라도 checksum과 다른 Checkpoint 내용은 재개하지 않는다."""
    checkpoint_path = tmp_path / "checksummed-checkpoints.json"
    checkpointer = JsonFileCheckpointer(path=checkpoint_path)
    checkpointer.save(
        run_id="checksum-guard-001",
        state=WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ),
    )
    checkpoint_path.write_text(
        checkpoint_path.read_text(encoding="utf-8").replace(
            "로컬 문서를 읽는다", "로컬 문서를 변경한다"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="checksum does not match"):
        checkpointer.load(run_id="checksum-guard-001")


def test_json_file_checkpoint_rejects_a_replaced_checksum_field(tmp_path: Path) -> None:
    """Payload를 바꾸지 않아도 교체된 checksum 필드는 재개 전에 거부한다."""
    checkpoint_path = tmp_path / "checksummed-field-checkpoints.json"
    checkpointer = JsonFileCheckpointer(path=checkpoint_path)
    checkpointer.save(
        run_id="checksum-field-guard-001",
        state=WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ),
    )
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    payload["payload_sha256"] = "0" * 64
    checkpoint_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="checksum does not match"):
        checkpointer.load(run_id="checksum-field-guard-001")


def test_json_file_checkpoint_rejects_a_rechecksummed_risky_approval_bypass(
    tmp_path: Path,
) -> None:
    """유효 checksum을 다시 써도 위험 Action의 승인 정책을 우회한 State는 복원하지 않는다."""
    checkpoint_path = tmp_path / "approval-policy-checkpoints.json"
    checkpointer = JsonFileCheckpointer(path=checkpoint_path)
    run_id = "approval-policy-guard-001"
    checkpointer.save(
        run_id=run_id,
        state=WorkflowState.start(
            task="학습용 배포를 준비한다", action=ActionKind.DEPLOY
        ).record(
            node="plan",
            detail="오프라인 계획을 만듭니다.",
            status=WorkflowStatus.PLANNED,
        ),
    )
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    payload["checkpoints"][run_id]["status"] = "ready"
    payload["checkpoints"][run_id]["approval_required"] = False
    payload["checkpoints"][run_id]["approval_granted"] = True
    canonical_payload = json.dumps(
        {
            "schema_version": payload["schema_version"],
            "checkpoints": payload["checkpoints"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["payload_sha256"] = hashlib.sha256(canonical_payload).hexdigest()
    checkpoint_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="action approval policy"):
        checkpointer.load(run_id=run_id)


def test_json_file_checkpoint_rejects_a_rechecksummed_risky_approval_without_audit_trail(
    tmp_path: Path,
) -> None:
    """승인 Boolean만 추가한 위험 완료 State는 승인 감사 기록 없이 복원하지 않는다."""
    checkpoint_path = tmp_path / "approval-audit-checkpoints.json"
    checkpointer = JsonFileCheckpointer(path=checkpoint_path)
    run_id = "approval-audit-guard-001"
    checkpointer.save(
        run_id=run_id,
        state=WorkflowState.start(
            task="학습용 배포를 준비한다", action=ActionKind.DEPLOY
        ).record(
            node="plan",
            detail="오프라인 계획을 만듭니다.",
            status=WorkflowStatus.PLANNED,
        ),
    )
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    state = payload["checkpoints"][run_id]
    state["status"] = "completed"
    state["approval_granted"] = True
    state["result"] = "오프라인 시뮬레이션 완료: deploy / 학습용 배포를 준비한다"
    canonical_payload = json.dumps(
        {
            "schema_version": payload["schema_version"],
            "checkpoints": payload["checkpoints"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["payload_sha256"] = hashlib.sha256(canonical_payload).hexdigest()
    checkpoint_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="approval audit trail"):
        checkpointer.load(run_id=run_id)


def test_json_file_checkpoint_rejects_a_rechecksummed_conflicting_approval_audit_trail(
    tmp_path: Path,
) -> None:
    """상반된 결정이 함께 있는 위험 완료 State는 checksum이 맞아도 복원하지 않는다."""
    checkpoint_path = tmp_path / "conflicting-approval-audit-checkpoints.json"
    checkpointer = JsonFileCheckpointer(path=checkpoint_path)
    run_id = "conflicting-approval-audit-guard-001"
    waiting = DeterministicWorkflow(checkpointer=checkpointer).invoke(
        run_id=run_id,
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL

    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    state = payload["checkpoints"][run_id]
    state["status"] = "completed"
    state["approval_granted"] = True
    state["result"] = "오프라인 시뮬레이션 완료: deploy / 학습용 배포를 준비한다"
    state["events"].extend(
        [
            {
                "sequence": 3,
                "node": "approval",
                "detail": "사람이 작업을 거절했습니다. 실행하지 않습니다.",
            },
            {
                "sequence": 4,
                "node": "approval",
                "detail": "사람 승인을 받았습니다. 실행 시뮬레이션으로 이동합니다.",
            },
            {
                "sequence": 5,
                "node": "execute",
                "detail": "외부 시스템을 변경하지 않는 결정론적 실행 결과를 만들었습니다.",
            },
        ]
    )
    canonical_payload = json.dumps(
        {
            "schema_version": payload["schema_version"],
            "checkpoints": payload["checkpoints"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["payload_sha256"] = hashlib.sha256(canonical_payload).hexdigest()
    checkpoint_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="approval audit trail"):
        checkpointer.load(run_id=run_id)


def test_json_file_checkpoint_rejects_duplicate_json_keys_before_state_restore(
    tmp_path: Path,
) -> None:
    """마지막 중복 키를 조용히 채택하지 않고 모호한 JSON Checkpoint를 거부한다."""
    checkpoint_path = tmp_path / "duplicate-key-checkpoints.json"
    checkpointer = JsonFileCheckpointer(path=checkpoint_path)
    checkpointer.save(
        run_id="duplicate-key-guard-001",
        state=WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ),
    )
    valid_payload = checkpoint_path.read_text(encoding="utf-8")
    duplicate_schema_version = valid_payload.replace(
        '  "schema_version": 2\n}',
        '  "schema_version": 2,\n  "schema_version": 2\n}',
    )
    assert duplicate_schema_version != valid_payload
    checkpoint_path.write_text(duplicate_schema_version, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate object keys"):
        checkpointer.load(run_id="duplicate-key-guard-001")


def test_json_file_checkpoint_rejects_a_duplicate_nested_event_key_before_checksum(
    tmp_path: Path,
) -> None:
    """중첩 감사 event의 중복 키도 checksum·State 복원 전에 거부한다."""
    checkpoint_path = tmp_path / "duplicate-nested-key-checkpoints.json"
    checkpointer = JsonFileCheckpointer(path=checkpoint_path)
    state = WorkflowState.start(
        task="로컬 문서를 읽는다", action=ActionKind.READ
    ).record(
        node="plan",
        detail="오프라인 계획을 만듭니다.",
        status=WorkflowStatus.PLANNED,
    )
    checkpointer.save(run_id="duplicate-nested-key-guard-001", state=state)
    valid_payload = checkpoint_path.read_text(encoding="utf-8")
    duplicate_event_sequence = valid_payload.replace(
        '          "sequence": 1\n',
        '          "sequence": 1,\n          "sequence": 1\n',
    )
    assert duplicate_event_sequence != valid_payload
    checkpoint_path.write_text(duplicate_event_sequence, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate object keys"):
        checkpointer.load(run_id="duplicate-nested-key-guard-001")


def test_json_file_checkpoint_rejects_an_existing_hard_link_alias(tmp_path: Path) -> None:
    """원자적 교체가 hard link 별칭을 분리하지 않도록 기존 다중 링크를 거부한다."""
    checkpoint_path = tmp_path / "checkpoints.json"
    checkpointer = JsonFileCheckpointer(path=checkpoint_path)
    checkpointer.save(
        run_id="hard-link-guard-001",
        state=WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ),
    )
    hard_link_path = tmp_path / "checkpoints-hard-link.json"
    os.link(checkpoint_path, hard_link_path)

    with pytest.raises(ValueError, match="multiple hard links"):
        JsonFileCheckpointer(path=hard_link_path)

    with pytest.raises(ValueError, match="multiple hard links"):
        checkpointer.load(run_id="hard-link-guard-001")


def test_streaming_workflow_emits_saved_node_updates_in_fixed_safe_order() -> None:
    """안전 작업의 상태 스트림은 저장 뒤 plan, approval, execute 순서로 끝난다."""
    workflow = StreamingWorkflow()

    updates = list(
        workflow.stream(
            run_id="stream-safe-001",
            task="로컬 문서를 읽는다",
            action=ActionKind.READ,
        )
    )

    assert [update.event.node for update in updates] == ["plan", "approval", "execute"]
    assert [update.state.status for update in updates] == [
        WorkflowStatus.PLANNED,
        WorkflowStatus.READY,
        WorkflowStatus.COMPLETED,
    ]
    assert [update.event.sequence for update in updates] == [1, 2, 3]
    assert updates[-1].state == workflow.checkpoint(run_id="stream-safe-001")
    assert updates[-1].state.result == "오프라인 시뮬레이션 완료: read / 로컬 문서를 읽는다"


def test_streaming_workflow_holds_risky_execution_until_explicit_approval() -> None:
    """위험 작업은 초기 스트림에 execute를 만들지 않고 승인 재개 뒤에만 만든다."""
    workflow = StreamingWorkflow()

    waiting_updates = list(
        workflow.stream(
            run_id="stream-risky-001",
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )

    assert [update.event.node for update in waiting_updates] == ["plan", "approval"]
    assert waiting_updates[-1].state.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert "execute" not in [update.event.node for update in waiting_updates]
    assert workflow.checkpoint(run_id="stream-risky-001") == waiting_updates[-1].state

    resumed_updates = list(
        workflow.resume_stream(run_id="stream-risky-001", approved=True)
    )

    assert [update.event.node for update in resumed_updates] == ["approval", "execute"]
    assert [update.state.status for update in resumed_updates] == [
        WorkflowStatus.READY,
        WorkflowStatus.COMPLETED,
    ]
    assert resumed_updates[-1].state.approval_granted is True


def test_concurrent_new_streams_create_one_risky_waiting_checkpoint() -> None:
    """동시 Streaming 시작은 하나의 위험 run만 승인 대기와 update를 만든다."""
    checkpointer = MemoryCheckpointer()
    workflow = StreamingWorkflow(checkpointer=checkpointer)
    run_id = "stream-concurrent-start-001"
    barrier = Barrier(8)

    def start_once() -> tuple[WorkflowStatus, tuple[str, ...]] | str:
        barrier.wait(timeout=5)
        try:
            updates = tuple(
                workflow.stream_new(
                    run_id=run_id,
                    task="학습용 배포를 준비한다",
                    action=ActionKind.DEPLOY,
                )
            )
        except WorkflowRunConflictError:
            return "conflict"
        return updates[-1].state.status, tuple(update.event.node for update in updates)

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: start_once(), range(8)))

    assert outcomes.count((WorkflowStatus.WAITING_FOR_APPROVAL, ("plan", "approval"))) == 1
    assert outcomes.count("conflict") == 7
    waiting = checkpointer.load(run_id=run_id)
    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.approval_granted is None
    assert waiting.result is None
    assert [event.node for event in waiting.events] == ["plan", "approval"]
    assert "execute" not in [event.node for event in waiting.events]


def test_concurrent_streaming_approvals_emit_one_execution_and_preserve_terminal_checkpoint(
) -> None:
    """동시 스트리밍 재개는 한 승인만 소비하고 하나의 execute update만 내보낸다."""
    checkpointer = MemoryCheckpointer()
    workflow = StreamingWorkflow(checkpointer=checkpointer)
    run_id = "stream-concurrent-approval-001"
    list(
        workflow.stream(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def approve_once() -> tuple[WorkflowStatus, tuple[str, ...]] | str:
        barrier.wait(timeout=5)
        try:
            updates = tuple(workflow.resume_stream(run_id=run_id, approved=True))
        except WorkflowRunConflictError:
            return "conflict"
        return updates[-1].state.status, tuple(update.event.node for update in updates)

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: approve_once(), range(8)))

    assert outcomes.count((WorkflowStatus.COMPLETED, ("approval", "execute"))) == 1
    assert outcomes.count("conflict") == 7
    completed = checkpointer.load(run_id=run_id)
    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.approval_granted is True
    assert [event.node for event in completed.events] == [
        "plan", "approval", "approval", "execute"
    ]


def test_concurrent_streaming_rejections_emit_one_decision_and_no_execution() -> None:
    """동시 거절 재전송은 한 승인 대기만 종료하고 execute update를 만들지 않는다."""
    checkpointer = MemoryCheckpointer()
    workflow = StreamingWorkflow(checkpointer=checkpointer)
    run_id = "stream-concurrent-rejection-001"
    list(
        workflow.stream(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def reject_once() -> tuple[WorkflowStatus, tuple[str, ...]] | str:
        barrier.wait(timeout=5)
        try:
            updates = tuple(workflow.resume_stream(run_id=run_id, approved=False))
        except WorkflowRunConflictError:
            return "conflict"
        return updates[-1].state.status, tuple(update.event.node for update in updates)

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: reject_once(), range(8)))

    assert outcomes.count((WorkflowStatus.REJECTED, ("approval",))) == 1
    assert outcomes.count("conflict") == 7
    rejected = checkpointer.load(run_id=run_id)
    assert rejected.status is WorkflowStatus.REJECTED
    assert rejected.approval_granted is False
    assert rejected.result is None
    assert [event.node for event in rejected.events] == ["plan", "approval", "approval"]
    assert "execute" not in [event.node for event in rejected.events]


def test_streaming_workflow_emits_no_execute_update_when_risky_action_is_rejected() -> None:
    """거절된 위험 작업은 approval 결정만 스트리밍하고 execute를 생략한다."""
    workflow = StreamingWorkflow()
    list(
        workflow.stream(
            run_id="stream-rejected-001",
            task="임시 파일을 삭제한다",
            action=ActionKind.DELETE,
        )
    )

    updates = list(workflow.resume_stream(run_id="stream-rejected-001", approved=False))

    assert [update.event.node for update in updates] == ["approval"]
    assert updates[-1].state.status is WorkflowStatus.REJECTED
    assert updates[-1].state.result is None


def test_api_adapter_keeps_risky_start_request_at_the_approval_boundary() -> None:
    """HTTP 형태의 DEPLOY 요청도 별도 사람 승인 전에는 execute를 만들지 않는다."""
    adapter = WorkflowApiAdapter()

    waiting = adapter.start(
        request=StartWorkflowRequest.model_validate(
            {
                "run_id": "api-risky-001",
                "task": "학습용 배포를 준비한다",
                "action": "deploy",
            }
        )
    )

    assert waiting.run_id == "api-risky-001"
    assert waiting.action is ActionKind.DEPLOY
    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.approval_required is True
    assert waiting.approval_granted is None
    assert [event.node for event in waiting.events] == ["plan", "approval"]
    assert "execute" not in [event.node for event in waiting.events]
    assert waiting.model_dump(mode="json")["status"] == "waiting_for_approval"


def test_api_adapter_requires_a_strict_separate_approval_request() -> None:
    """문자열 승인과 거절 결정은 위험 실행을 허용하지 않는다."""
    adapter = WorkflowApiAdapter()
    adapter.start(
        request=StartWorkflowRequest(
            run_id="api-rejected-001",
            task="학습용 메시지를 전송한다",
            action=ActionKind.SEND,
        )
    )

    with pytest.raises(ValidationError):
        ApprovalRequest.model_validate({"approved": "true"})

    rejected = adapter.resume(
        run_id="api-rejected-001",
        request=ApprovalRequest(approved=False),
    )

    assert rejected.status is WorkflowStatus.REJECTED
    assert rejected.approval_granted is False
    assert rejected.result is None
    assert [event.node for event in rejected.events] == ["plan", "approval", "approval"]
    assert "execute" not in [event.node for event in rejected.events]


def test_api_request_models_reject_extra_fields_and_blank_path_run_id() -> None:
    """HTTP 경계는 계약 밖 입력을 Workflow나 Checkpointer에 전달하지 않는다."""
    with pytest.raises(ValidationError):
        StartWorkflowRequest.model_validate(
            {
                "run_id": "api-invalid-001",
                "task": "로컬 문서를 읽는다",
                "action": "read",
                "approved": True,
            }
        )

    with pytest.raises(ValidationError):
        RunIdPath(run_id="   ")


def test_api_adapter_rejects_duplicate_start_without_replacing_pending_approval() -> None:
    """동일 run ID 재시작은 위험 작업의 기존 승인 대기 상태를 바꾸지 못한다."""
    adapter = WorkflowApiAdapter()
    waiting = adapter.start(
        request=StartWorkflowRequest(
            run_id="api-duplicate-001",
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )

    with pytest.raises(WorkflowRunConflictError, match="run_id already exists"):
        adapter.start(
            request=StartWorkflowRequest(
                run_id="api-duplicate-001",
                task="로컬 문서를 읽는다",
                action=ActionKind.READ,
            )
        )

    completed = adapter.resume(
        run_id="api-duplicate-001",
        request=ApprovalRequest(approved=True),
    )

    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert completed.action is ActionKind.DEPLOY
    assert [event.node for event in completed.events] == [
        "plan",
        "approval",
        "approval",
        "execute",
    ]


def test_memory_checkpointer_creates_a_run_once_without_replacement() -> None:
    """원자적 생성은 두 번째 시작 상태가 기존 위험 작업을 덮어쓰지 못하게 한다."""
    checkpointer = MemoryCheckpointer()
    waiting = WorkflowState.start(task="학습용 배포를 준비한다", action=ActionKind.DEPLOY)
    replacement = WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ)

    assert checkpointer.save_if_absent(run_id="atomic-start-001", state=waiting) is True
    assert checkpointer.save_if_absent(run_id="atomic-start-001", state=replacement) is False
    assert checkpointer.load(run_id="atomic-start-001") == waiting


def test_json_checkpointer_creates_a_run_once_without_replacement(tmp_path: Path) -> None:
    """로컬 JSON Checkpointer도 한 인스턴스 안에서 첫 시작 상태만 기록한다."""
    checkpointer = JsonFileCheckpointer(path=tmp_path / "atomic-checkpoints.json")
    waiting = WorkflowState.start(task="학습용 배포를 준비한다", action=ActionKind.DEPLOY)
    replacement = WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ)

    assert checkpointer.save_if_absent(run_id="atomic-file-001", state=waiting) is True
    assert checkpointer.save_if_absent(run_id="atomic-file-001", state=replacement) is False
    assert checkpointer.load(run_id="atomic-file-001") == waiting


def test_concurrent_api_starts_create_one_risky_run_and_preserve_approval_gate() -> None:
    """동시 재전송도 한 메모리 Checkpointer 안에서는 하나만 승인 대기로 만든다."""
    checkpointer = MemoryCheckpointer()
    adapter = WorkflowApiAdapter(workflow=DeterministicWorkflow(checkpointer=checkpointer))
    request = StartWorkflowRequest(
        run_id="atomic-concurrent-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )

    barrier = Barrier(8)

    def start_once() -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapter.start(request=request).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: start_once(), range(8)))

    assert outcomes.count(WorkflowStatus.WAITING_FOR_APPROVAL) == 1
    assert outcomes.count("conflict") == 7
    waiting = checkpointer.load(run_id="atomic-concurrent-001")
    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert [event.node for event in waiting.events] == ["plan", "approval"]

    completed = adapter.resume(
        run_id="atomic-concurrent-001",
        request=ApprovalRequest(approved=True),
    )

    assert completed.status is WorkflowStatus.COMPLETED
    assert [event.node for event in completed.events] == [
        "plan", "approval", "approval", "execute"
    ]


def test_concurrent_api_approvals_record_one_decision_and_one_offline_execution() -> None:
    """동시 승인 재전송도 하나만 승인 대기를 소비하고 실행 시뮬레이션을 기록한다."""
    checkpointer = MemoryCheckpointer()
    adapter = WorkflowApiAdapter(workflow=DeterministicWorkflow(checkpointer=checkpointer))
    adapter.start(
        request=StartWorkflowRequest(
            run_id="approval-concurrent-001",
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def approve_once() -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapter.resume(
                run_id="approval-concurrent-001",
                request=ApprovalRequest(approved=True),
            ).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: approve_once(), range(8)))

    assert outcomes.count(WorkflowStatus.COMPLETED) == 1
    assert outcomes.count("conflict") == 7
    completed = checkpointer.load(run_id="approval-concurrent-001")
    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.approval_granted is True
    assert [event.node for event in completed.events] == [
        "plan", "approval", "approval", "execute"
    ]


def test_checkpointers_compare_and_replace_only_the_expected_state(tmp_path: Path) -> None:
    """비교-교체 실패는 이미 변경된 위험 작업 Checkpoint를 덮어쓰지 않는다."""
    initial = WorkflowState.start(task="학습용 배포를 준비한다", action=ActionKind.DEPLOY)
    changed = initial.record(
        node="plan",
        detail="오프라인 계획",
        status=WorkflowStatus.PLANNED,
    )
    replacement = WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ)

    for checkpointer in (
        MemoryCheckpointer(),
        JsonFileCheckpointer(path=tmp_path / "compare-and-replace-checkpoints.json"),
    ):
        checkpointer.save(run_id="compare-and-replace-001", state=initial)
        assert (
            checkpointer.save_if_current(
                run_id="compare-and-replace-001",
                expected_state=initial,
                state=changed,
            )
            is True
        )
        assert (
            checkpointer.save_if_current(
                run_id="compare-and-replace-001",
                expected_state=initial,
                state=replacement,
            )
            is False
        )
        assert checkpointer.load(run_id="compare-and-replace-001") == changed


def test_concurrent_json_checkpoint_approvals_consume_one_pending_state(tmp_path: Path) -> None:
    """같은 JSON Checkpointer 인스턴스의 동시 승인은 하나만 실행 시뮬레이션을 기록한다."""
    checkpointer = JsonFileCheckpointer(path=tmp_path / "concurrent-approvals.json")
    adapter = WorkflowApiAdapter(workflow=DeterministicWorkflow(checkpointer=checkpointer))
    adapter.start(
        request=StartWorkflowRequest(
            run_id="json-approval-concurrent-001",
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def approve_once() -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapter.resume(
                run_id="json-approval-concurrent-001",
                request=ApprovalRequest(approved=True),
            ).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: approve_once(), range(8)))

    assert outcomes.count(WorkflowStatus.COMPLETED) == 1
    assert outcomes.count("conflict") == 7
    completed = checkpointer.load(run_id="json-approval-concurrent-001")
    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.approval_granted is True
    assert [event.node for event in completed.events] == [
        "plan", "approval", "approval", "execute"
    ]


def test_concurrent_json_checkpoint_starts_create_one_pending_risky_run(tmp_path: Path) -> None:
    """같은 JSON Checkpointer 인스턴스의 동시 시작은 하나의 승인 대기만 만든다."""
    checkpointer = JsonFileCheckpointer(path=tmp_path / "concurrent-starts.json")
    adapter = WorkflowApiAdapter(workflow=DeterministicWorkflow(checkpointer=checkpointer))
    request = StartWorkflowRequest(
        run_id="json-start-concurrent-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
    barrier = Barrier(8)

    def start_once() -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapter.start(request=request).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: start_once(), range(8)))

    assert outcomes.count(WorkflowStatus.WAITING_FOR_APPROVAL) == 1
    assert outcomes.count("conflict") == 7
    waiting = checkpointer.load(run_id="json-start-concurrent-001")
    assert waiting.action is ActionKind.DEPLOY
    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.approval_granted is None
    assert [event.node for event in waiting.events] == ["plan", "approval"]
    assert "execute" not in [event.node for event in waiting.events]


def test_concurrent_json_checkpoint_instances_share_a_path_lock_for_risky_starts(
    tmp_path: Path,
) -> None:
    """같은 프로세스의 독립 JSON 인스턴스도 동일 파일에서는 한 번만 run을 만든다."""
    checkpoint_path = tmp_path / "shared-path-concurrent-starts.json"
    adapters = tuple(
        WorkflowApiAdapter(
            workflow=DeterministicWorkflow(
                checkpointer=JsonFileCheckpointer(path=checkpoint_path)
            )
        )
        for _ in range(8)
    )
    request = StartWorkflowRequest(
        run_id="json-shared-path-start-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
    barrier = Barrier(8)

    def start_once(index: int) -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapters[index].start(request=request).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(start_once, range(8)))

    assert outcomes.count(WorkflowStatus.WAITING_FOR_APPROVAL) == 1
    assert outcomes.count("conflict") == 7
    waiting = JsonFileCheckpointer(path=checkpoint_path).load(
        run_id="json-shared-path-start-001"
    )
    assert waiting.action is ActionKind.DEPLOY
    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.approval_granted is None
    assert [event.node for event in waiting.events] == ["plan", "approval"]
    assert "execute" not in [event.node for event in waiting.events]


def test_concurrent_json_checkpoint_instances_share_a_path_lock_for_risky_approvals(
    tmp_path: Path,
) -> None:
    """독립 JSON 인스턴스도 같은 경로에서는 승인 대기를 한 번만 소비한다."""
    checkpoint_path = tmp_path / "shared-path-concurrent-approvals.json"
    adapters = tuple(
        WorkflowApiAdapter(
            workflow=DeterministicWorkflow(
                checkpointer=JsonFileCheckpointer(path=checkpoint_path)
            )
        )
        for _ in range(8)
    )
    run_id = "json-shared-path-approval-001"
    adapters[0].start(
        request=StartWorkflowRequest(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def approve_once(index: int) -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapters[index].resume(
                run_id=run_id,
                request=ApprovalRequest(approved=True),
            ).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(approve_once, range(8)))

    assert outcomes.count(WorkflowStatus.COMPLETED) == 1
    assert outcomes.count("conflict") == 7
    completed = JsonFileCheckpointer(path=checkpoint_path).load(run_id=run_id)
    assert completed.action is ActionKind.DEPLOY
    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.approval_granted is True
    assert [event.node for event in completed.events] == [
        "plan", "approval", "approval", "execute"
    ]


def test_concurrent_json_checkpoint_instances_share_a_path_lock_for_risky_rejections(
    tmp_path: Path,
) -> None:
    """독립 JSON 인스턴스도 같은 경로에서는 승인 대기를 한 번만 거절한다."""
    checkpoint_path = tmp_path / "shared-path-concurrent-rejections.json"
    adapters = tuple(
        WorkflowApiAdapter(
            workflow=DeterministicWorkflow(
                checkpointer=JsonFileCheckpointer(path=checkpoint_path)
            )
        )
        for _ in range(8)
    )
    run_id = "json-shared-path-rejection-001"
    adapters[0].start(
        request=StartWorkflowRequest(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def reject_once(index: int) -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapters[index].resume(
                run_id=run_id,
                request=ApprovalRequest(approved=False),
            ).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(reject_once, range(8)))

    assert outcomes.count(WorkflowStatus.REJECTED) == 1
    assert outcomes.count("conflict") == 7
    rejected = JsonFileCheckpointer(path=checkpoint_path).load(run_id=run_id)
    assert rejected.action is ActionKind.DEPLOY
    assert rejected.status is WorkflowStatus.REJECTED
    assert rejected.approval_granted is False
    assert rejected.result is None
    assert [event.node for event in rejected.events] == ["plan", "approval", "approval"]
    assert "execute" not in [event.node for event in rejected.events]


def test_json_checkpoint_path_aliases_share_a_normalized_lock_for_risky_approvals(
    tmp_path: Path,
) -> None:
    """서로 다른 경로 표기도 resolve 뒤 같은 승인 대기를 한 번만 소비한다."""
    checkpoint_path = tmp_path / "normalized-shared-approvals.json"
    alias_directory = tmp_path / "path-alias"
    alias_directory.mkdir()
    alias_path = alias_directory / ".." / checkpoint_path.name
    assert checkpoint_path != alias_path
    adapters = tuple(
        WorkflowApiAdapter(
            workflow=DeterministicWorkflow(
                checkpointer=JsonFileCheckpointer(
                    path=checkpoint_path if index % 2 == 0 else alias_path
                )
            )
        )
        for index in range(8)
    )
    run_id = "json-normalized-path-approval-001"
    adapters[0].start(
        request=StartWorkflowRequest(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def approve_once(index: int) -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapters[index].resume(
                run_id=run_id,
                request=ApprovalRequest(approved=True),
            ).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(approve_once, range(8)))

    assert outcomes.count(WorkflowStatus.COMPLETED) == 1
    assert outcomes.count("conflict") == 7
    completed = JsonFileCheckpointer(path=checkpoint_path).load(run_id=run_id)
    assert completed.action is ActionKind.DEPLOY
    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.approval_granted is True
    assert [event.node for event in completed.events] == [
        "plan", "approval", "approval", "execute"
    ]


def test_json_checkpoint_path_aliases_share_a_normalized_lock_for_risky_rejections(
    tmp_path: Path,
) -> None:
    """서로 다른 경로 표기도 resolve 뒤 같은 승인 대기를 한 번만 거절한다."""
    checkpoint_path = tmp_path / "normalized-shared-rejections.json"
    alias_directory = tmp_path / "path-alias"
    alias_directory.mkdir()
    alias_path = alias_directory / ".." / checkpoint_path.name
    assert checkpoint_path != alias_path
    adapters = tuple(
        WorkflowApiAdapter(
            workflow=DeterministicWorkflow(
                checkpointer=JsonFileCheckpointer(
                    path=checkpoint_path if index % 2 == 0 else alias_path
                )
            )
        )
        for index in range(8)
    )
    run_id = "json-normalized-path-rejection-001"
    adapters[0].start(
        request=StartWorkflowRequest(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    barrier = Barrier(8)

    def reject_once(index: int) -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapters[index].resume(
                run_id=run_id,
                request=ApprovalRequest(approved=False),
            ).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(reject_once, range(8)))

    assert outcomes.count(WorkflowStatus.REJECTED) == 1
    assert outcomes.count("conflict") == 7
    rejected = JsonFileCheckpointer(path=checkpoint_path).load(run_id=run_id)
    assert rejected.action is ActionKind.DEPLOY
    assert rejected.status is WorkflowStatus.REJECTED
    assert rejected.approval_granted is False
    assert rejected.result is None
    assert [event.node for event in rejected.events] == ["plan", "approval", "approval"]
    assert "execute" not in [event.node for event in rejected.events]


def test_json_checkpoint_path_aliases_share_a_normalized_lock_for_risky_starts(
    tmp_path: Path,
) -> None:
    """서로 다른 경로 표기도 resolve 뒤 위험 run 하나만 승인 대기로 만든다."""
    checkpoint_path = tmp_path / "normalized-shared-starts.json"
    alias_directory = tmp_path / "path-alias"
    alias_directory.mkdir()
    alias_path = alias_directory / ".." / checkpoint_path.name
    assert checkpoint_path != alias_path
    adapters = tuple(
        WorkflowApiAdapter(
            workflow=DeterministicWorkflow(
                checkpointer=JsonFileCheckpointer(
                    path=checkpoint_path if index % 2 == 0 else alias_path
                )
            )
        )
        for index in range(8)
    )
    request = StartWorkflowRequest(
        run_id="json-normalized-path-start-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
    barrier = Barrier(8)

    def start_once(index: int) -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapters[index].start(request=request).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(start_once, range(8)))

    assert outcomes.count(WorkflowStatus.WAITING_FOR_APPROVAL) == 1
    assert outcomes.count("conflict") == 7
    waiting = JsonFileCheckpointer(path=checkpoint_path).load(run_id=request.run_id)
    assert waiting.action is ActionKind.DEPLOY
    assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert waiting.approval_granted is None
    assert waiting.result is None
    assert [event.node for event in waiting.events] == ["plan", "approval"]
    assert "execute" not in [event.node for event in waiting.events]


def test_json_checkpoint_path_aliases_consume_one_mixed_approval_decision(
    tmp_path: Path,
) -> None:
    """별칭 인스턴스의 상반된 동시 결정도 하나만 기록하고 나머지는 충돌한다."""
    checkpoint_path = tmp_path / "normalized-shared-mixed-decisions.json"
    alias_directory = tmp_path / "path-alias"
    alias_directory.mkdir()
    alias_path = alias_directory / ".." / checkpoint_path.name
    assert checkpoint_path != alias_path
    adapters = tuple(
        WorkflowApiAdapter(
            workflow=DeterministicWorkflow(
                checkpointer=JsonFileCheckpointer(
                    path=checkpoint_path if index % 2 == 0 else alias_path
                )
            )
        )
        for index in range(8)
    )
    run_id = "json-normalized-path-mixed-decision-001"
    adapters[0].start(
        request=StartWorkflowRequest(
            run_id=run_id,
            task="학습용 배포를 준비한다",
            action=ActionKind.DEPLOY,
        )
    )
    decisions = (True, False, True, False, True, False, True, False)
    barrier = Barrier(len(decisions))

    def decide_once(index: int) -> WorkflowStatus | str:
        barrier.wait(timeout=5)
        try:
            return adapters[index].resume(
                run_id=run_id,
                request=ApprovalRequest(approved=decisions[index]),
            ).status
        except WorkflowRunConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=len(decisions)) as executor:
        outcomes = list(executor.map(decide_once, range(len(decisions))))

    assert outcomes.count(WorkflowStatus.COMPLETED) + outcomes.count(WorkflowStatus.REJECTED) == 1
    assert outcomes.count("conflict") == 7
    terminal = JsonFileCheckpointer(path=checkpoint_path).load(run_id=run_id)
    assert terminal.action is ActionKind.DEPLOY
    assert terminal.status in {WorkflowStatus.COMPLETED, WorkflowStatus.REJECTED}
    assert terminal.approval_granted is (terminal.status is WorkflowStatus.COMPLETED)
    if terminal.status is WorkflowStatus.COMPLETED:
        assert [event.node for event in terminal.events] == [
            "plan", "approval", "approval", "execute"
        ]
    else:
        assert [event.node for event in terminal.events] == ["plan", "approval", "approval"]
