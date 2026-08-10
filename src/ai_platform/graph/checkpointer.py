"""오프라인 Workflow를 위한 메모리·로컬 파일 Checkpoint 경계."""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from threading import Lock
from typing import Protocol
from uuid import uuid4

from ai_platform.graph.state import (
    ActionKind,
    RouteKind,
    WorkflowEvent,
    WorkflowState,
    WorkflowStatus,
)


class Checkpointer(Protocol):
    """Workflow가 상태를 저장·재개할 때 사용하는 최소 계약이다."""

    def save(self, *, run_id: str, state: WorkflowState) -> None:
        """run ID의 최신 상태를 저장한다."""

    def load(self, *, run_id: str) -> WorkflowState:
        """run ID의 최신 상태를 읽는다."""


class MemoryCheckpointer:
    """불변 WorkflowState를 run ID별로 저장하는 프로세스 내 Checkpointer다.

    프로세스가 종료되면 값도 사라진다. 영속 저장소, 인증, 보존 정책은
    ``JsonFileCheckpointer`` 장에서 별도로 다룬다.
    """

    def __init__(self) -> None:
        """비어 있는 Checkpoint 저장소를 만든다."""
        self._states: dict[str, WorkflowState] = {}
        self._lock = Lock()

    def save(self, *, run_id: str, state: WorkflowState) -> None:
        """비어 있지 않은 run ID에 최신 상태를 기록한다."""
        _validate_run_id(run_id)
        with self._lock:
            self._states[run_id] = state

    def load(self, *, run_id: str) -> WorkflowState:
        """run ID의 상태를 반환하고 없으면 명확하게 실패한다."""
        _validate_run_id(run_id)
        with self._lock:
            try:
                return self._states[run_id]
            except KeyError as error:
                raise KeyError(f"checkpoint not found: {run_id}") from error


class JsonFileCheckpointer:
    """명시한 로컬 JSON 파일에 공개적인 WorkflowState만 저장한다.

    이 학습용 저장소는 네트워크·데이터베이스·암호화를 사용하지 않는다. ``run_id``와
    상태의 텍스트 필드에서 흔한 비밀값 표식을 거부하며, 파일은 같은 디렉터리의 임시
    파일을 원자적으로 교체해 기록한다. 따라서 실제 자격 증명, 개인정보, 운영 승인
    기록을 저장하는 용도로 사용하면 안 된다.
    """

    _SCHEMA_VERSION = 1

    def __init__(self, *, path: Path) -> None:
        """기존 디렉터리 안의 단일 Checkpoint 파일 경로를 검증한다."""
        if path.exists() and not path.is_file():
            raise ValueError("checkpoint path must be a file")
        if not path.parent.is_dir():
            raise ValueError("checkpoint parent directory must already exist")
        self._path = path
        self._lock = Lock()

    def save(self, *, run_id: str, state: WorkflowState) -> None:
        """공개 상태를 결정론적 JSON으로 원자적으로 저장한다."""
        _validate_run_id(run_id)
        _validate_public_state(state)
        with self._lock:
            checkpoints = self._read_checkpoints()
            checkpoints[run_id] = _state_to_payload(state)
            payload = {
                "schema_version": self._SCHEMA_VERSION,
                "checkpoints": checkpoints,
            }
            temporary_path = self._path.with_name(
                f".{self._path.name}.{uuid4().hex}.tmp"
            )
            try:
                temporary_path.write_text(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8",
                )
                temporary_path.replace(self._path)
            finally:
                if temporary_path.exists():
                    temporary_path.unlink()

    def load(self, *, run_id: str) -> WorkflowState:
        """저장된 공개 상태를 엄격히 검증해 복원한다."""
        _validate_run_id(run_id)
        with self._lock:
            checkpoints = self._read_checkpoints()
            try:
                payload = checkpoints[run_id]
            except KeyError as error:
                raise KeyError(f"checkpoint not found: {run_id}") from error
        return _payload_to_state(payload)

    def _read_checkpoints(self) -> dict[str, object]:
        """파일이 없으면 빈 저장소를, 있으면 검증된 JSON 객체를 반환한다."""
        if not self._path.exists():
            return {}
        try:
            raw_payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("checkpoint file is not valid JSON") from error
        if not isinstance(raw_payload, dict):
            raise ValueError("checkpoint file must contain an object")
        if raw_payload.get("schema_version") != self._SCHEMA_VERSION:
            raise ValueError("unsupported checkpoint schema version")
        checkpoints = raw_payload.get("checkpoints")
        if not isinstance(checkpoints, dict):
            raise ValueError("checkpoint file must contain a checkpoints object")
        for stored_run_id in checkpoints:
            if not isinstance(stored_run_id, str):
                raise ValueError("checkpoint run_id must be a string")
            _validate_run_id(stored_run_id)
        return checkpoints


def _validate_run_id(run_id: str) -> None:
    """공백·비밀값 표식이 있는 run ID를 저장소 경계에서 거부한다."""
    if not run_id.strip():
        raise ValueError("run_id must not be empty")
    _reject_suspected_secret(run_id, field="run_id")


def _validate_public_state(state: WorkflowState) -> None:
    """파일에 쓸 텍스트가 학습용 공개 데이터인지 보수적으로 확인한다."""
    texts = [state.task, state.retry_source]
    texts.extend(event.node for event in state.events)
    texts.extend(event.detail for event in state.events)
    if state.result is not None:
        texts.append(state.result)
    for text in texts:
        _reject_suspected_secret(text, field="checkpoint state")


def _reject_suspected_secret(value: str, *, field: str) -> None:
    """일반적인 자격 증명 접두사·키 할당 표식을 거부한다."""
    secret_pattern = re.compile(
        r"(?i)(?:\b(?:api[_-]?key|password|secret|token)\s*[:=]|\b(?:bearer\s+|sk-|ghp_))"
    )
    if secret_pattern.search(value):
        raise ValueError(f"{field} must not contain suspected sensitive data")


def _state_to_payload(state: WorkflowState) -> dict[str, object]:
    """불변 State를 JSON 기본 타입만 사용하는 명시적 스키마로 변환한다."""
    return {
        "task": state.task,
        "action": state.action.value,
        "status": state.status.value,
        "approval_required": state.approval_required,
        "approval_granted": state.approval_granted,
        "review_approved": state.review_approved,
        "selected_route": (
            None if state.selected_route is None else state.selected_route.value
        ),
        "result": state.result,
        "events": [asdict(event) for event in state.events],
        "retry_failures_before_success": state.retry_failures_before_success,
        "retry_max_retries": state.retry_max_retries,
        "retry_source": state.retry_source,
        "attempt_count": state.attempt_count,
    }


def _payload_to_state(payload: object) -> WorkflowState:
    """신뢰하지 않는 JSON payload를 검증해 불변 State로 변환한다."""
    if not isinstance(payload, dict):
        raise ValueError("checkpoint state must be an object")
    required_fields = {
        "task",
        "action",
        "status",
        "approval_required",
        "approval_granted",
        "review_approved",
        "selected_route",
        "result",
        "events",
        "retry_failures_before_success",
        "retry_max_retries",
        "retry_source",
        "attempt_count",
    }
    if set(payload) != required_fields:
        raise ValueError("checkpoint state has an unexpected schema")

    task = _require_str(payload["task"], field="task")
    retry_source = _require_str(payload["retry_source"], field="retry_source")
    action = _parse_enum(ActionKind, payload["action"], field="action")
    status = _parse_enum(WorkflowStatus, payload["status"], field="status")
    selected_route_raw = payload["selected_route"]
    selected_route = (
        None
        if selected_route_raw is None
        else _parse_enum(RouteKind, selected_route_raw, field="selected_route")
    )
    result = payload["result"]
    if result is not None:
        result = _require_str(result, field="result")
    events = _payload_to_events(payload["events"])
    state = WorkflowState(
        task=task,
        action=action,
        status=status,
        approval_required=_require_bool(payload["approval_required"], field="approval_required"),
        approval_granted=_require_optional_bool(
            payload["approval_granted"], field="approval_granted"
        ),
        review_approved=_require_optional_bool(
            payload["review_approved"], field="review_approved"
        ),
        selected_route=selected_route,
        result=result,
        events=events,
        retry_failures_before_success=_require_non_negative_int(
            payload["retry_failures_before_success"],
            field="retry_failures_before_success",
        ),
        retry_max_retries=_require_non_negative_int(
            payload["retry_max_retries"], field="retry_max_retries"
        ),
        retry_source=retry_source,
        attempt_count=_require_non_negative_int(
            payload["attempt_count"], field="attempt_count"
        ),
    )
    _validate_public_state(state)
    return state


def _payload_to_events(payload: object) -> tuple[WorkflowEvent, ...]:
    """이벤트 배열과 연속된 감사 순서를 검증한다."""
    if not isinstance(payload, list):
        raise ValueError("checkpoint events must be a list")
    events: list[WorkflowEvent] = []
    for expected_sequence, raw_event in enumerate(payload, start=1):
        if not isinstance(raw_event, dict) or set(raw_event) != {"sequence", "node", "detail"}:
            raise ValueError("checkpoint event has an unexpected schema")
        sequence = _require_non_negative_int(raw_event["sequence"], field="event sequence")
        if sequence != expected_sequence:
            raise ValueError("checkpoint event sequence must be contiguous")
        events.append(
            WorkflowEvent(
                sequence=sequence,
                node=_require_str(raw_event["node"], field="event node"),
                detail=_require_str(raw_event["detail"], field="event detail"),
            )
        )
    return tuple(events)


def _require_str(value: object, *, field: str) -> str:
    """JSON 문자열을 확인한다."""
    if not isinstance(value, str):
        raise ValueError(f"checkpoint {field} must be a string")
    return value


def _require_bool(value: object, *, field: str) -> bool:
    """JSON 불리언을 확인한다."""
    if not isinstance(value, bool):
        raise ValueError(f"checkpoint {field} must be a boolean")
    return value


def _require_optional_bool(value: object, *, field: str) -> bool | None:
    """JSON 불리언 또는 null을 확인한다."""
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"checkpoint {field} must be a boolean or null")
    return value


def _require_non_negative_int(value: object, *, field: str) -> int:
    """bool과 구분되는 0 이상의 JSON 정수를 확인한다."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"checkpoint {field} must be a non-negative integer")
    return value


def _parse_enum[T: (ActionKind, RouteKind, WorkflowStatus)](
    enum_type: type[T], value: object, *, field: str
) -> T:
    """JSON 문자열을 허용된 상태 열거형으로 변환한다."""
    if not isinstance(value, str):
        raise ValueError(f"checkpoint {field} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise ValueError(f"checkpoint {field} is invalid") from error
