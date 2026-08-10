"""재시작 학습을 위한 메모리 내 Checkpoint 경계."""
from __future__ import annotations

from threading import Lock

from ai_platform.graph.state import WorkflowState


class MemoryCheckpointer:
    """불변 WorkflowState를 run ID별로 저장하는 오프라인 Checkpointer다.

    프로세스가 종료되면 값도 사라진다. 영속 저장소, 인증, 보존 정책은 이후 장에서
    별도로 설계해야 하며 이 학습용 구현은 민감정보를 저장하지 않는다.
    """

    def __init__(self) -> None:
        """비어 있는 Checkpoint 저장소를 만든다."""
        self._states: dict[str, WorkflowState] = {}
        self._lock = Lock()

    def save(self, *, run_id: str, state: WorkflowState) -> None:
        """비어 있지 않은 run ID에 최신 상태를 기록한다."""
        if not run_id.strip():
            raise ValueError("run_id must not be empty")
        with self._lock:
            self._states[run_id] = state

    def load(self, *, run_id: str) -> WorkflowState:
        """run ID의 상태를 반환하고 없으면 명확하게 실패한다."""
        with self._lock:
            try:
                return self._states[run_id]
            except KeyError as error:
                raise KeyError(f"checkpoint not found: {run_id}") from error
