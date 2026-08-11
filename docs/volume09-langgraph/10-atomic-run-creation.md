# 원자적 run 생성과 승인 Checkpoint 보존

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- run ID 존재 확인과 첫 Checkpoint 저장을 하나의 생성 연산으로 취급한다.
- 조회 뒤 저장하는 분리된 처리의 경쟁 조건을 설명한다.
- 중복 시작이 위험 작업의 승인 대기 상태를 바꾸지 못하게 한다.
- 메모리·로컬 JSON Checkpointer의 보장 범위와 운영 저장소의 추가 요구사항을 구분한다.

## 2. 왜 필요한가

이전 장의 충돌 검사는 기존 run ID를 거부했습니다. 그러나 `load()`로 부재를 확인한 뒤 `save()`하는 두 단계 사이에 다른 요청이 같은 ID를 저장할 수 있습니다. 두 요청이 모두 "없다"고 판단하면 나중 요청이 승인 대기 중인 `DEPLOY` 상태를 덮어쓸 수 있습니다.

사람 승인은 특정 작업과 상태에 묶여야 합니다. 따라서 새 실행을 만들 때는 존재 확인과 최초 저장을 분리하지 않아야 합니다. 이 참조 모델은 `Checkpointer.save_if_absent()`로 첫 상태를 한 번만 기록합니다.

> [!WARNING]
> 이 장의 모든 전이는 오프라인·결정론적입니다. `DEPLOY`, `DELETE`, `SEND`는 실제 배포·삭제·전송을 하지 않습니다. 원자적 생성은 승인 없이 `execute`로 이동하게 하지 않습니다.

## 3. 핵심 개념

- **경쟁 조건(race condition)**: 둘 이상의 시작 요청이 같은 상태를 동시에 관찰해 잘못된 전이를 만드는 문제입니다.
- **원자적 생성(atomic create)**: "없으면 저장"을 중간 관찰이 가능한 두 단계가 아닌 하나의 연산으로 처리하는 방식입니다.
- **생성 성공 여부**: `save_if_absent()`는 첫 저장이면 `True`, 기존 ID가 있으면 `False`를 반환합니다.
- **Checkpoint 보존**: `False`일 때 기존 action, 감사 이벤트, 승인 대기 상태를 수정하지 않습니다.
- **보장 범위**: `MemoryCheckpointer`는 프로세스 내 Lock을 사용합니다. `JsonFileCheckpointer`의 생성 보장은 한 인스턴스의 스레드 범위입니다.

## 4. 동작 구조

```text
요청 A: start(run_id=deploy-001, DEPLOY)
    └── save_if_absent(... WAITING_FOR_APPROVAL) -> True
        └── 기존 상태: DEPLOY 승인 대기

요청 B: start(run_id=deploy-001, READ)
    └── save_if_absent(... COMPLETED) -> False
        └── WorkflowRunConflictError
            기존 DEPLOY Checkpoint 변경 없음

명시적 승인: resume(deploy-001, approved=True)
    └── approval -> execute -> COMPLETED  # 오프라인 시뮬레이션
```

`WorkflowApiAdapter.start()`는 먼저 `checkpoint()`를 조회하지 않습니다. `DeterministicWorkflow.invoke_new()`가 초기 상태를 만든 뒤 Checkpointer의 원자적 생성 결과만으로 새 실행 또는 충돌을 결정합니다.

## 5. 실습 환경

사용 파일은 다음과 같습니다.

- `src/ai_platform/graph/checkpointer.py`
- `src/ai_platform/graph/workflow.py`
- `src/ai_platform/graph/api.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

FastAPI 서버, 데이터베이스, 네트워크는 실행하지 않습니다. 현재 `JsonFileCheckpointer`는 학습용 로컬 파일 저장소이므로 여러 프로세스·여러 인스턴스에서 공유하지 않습니다.

## 6. 단계별 실습

### 6.1 첫 상태만 생성한다

```python
from ai_platform.graph import ActionKind, MemoryCheckpointer, WorkflowState

checkpointer = MemoryCheckpointer()
waiting = WorkflowState.start(task="학습용 배포를 준비한다", action=ActionKind.DEPLOY)
replacement = WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ)

assert checkpointer.save_if_absent(run_id="atomic-demo-001", state=waiting) is True
assert checkpointer.save_if_absent(run_id="atomic-demo-001", state=replacement) is False
assert checkpointer.load(run_id="atomic-demo-001") == waiting
```

### 6.2 API 어댑터에서 충돌을 확인한다

```python
import pytest
from ai_platform.graph import (
    ActionKind,
    StartWorkflowRequest,
    WorkflowApiAdapter,
    WorkflowRunConflictError,
)

adapter = WorkflowApiAdapter()
request = StartWorkflowRequest(
    run_id="atomic-api-001",
    task="학습용 배포를 준비한다",
    action=ActionKind.DEPLOY,
)
waiting = adapter.start(request=request)

with pytest.raises(WorkflowRunConflictError, match="run_id already exists"):
    adapter.start(request=request)

assert waiting.status.value == "waiting_for_approval"
```

### 6.3 오프라인 계약을 검사한다

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

`MemoryCheckpointer`는 하나의 Lock 안에서 존재 여부와 저장을 처리합니다.

```python
with self._lock:
    if run_id in self._states:
        return False
    self._states[run_id] = state
    return True
```

`WorkflowApiAdapter.start()`는 `invoke_new()`만 호출합니다. `invoke_new()`는 `save_if_absent()`가 `False`를 반환하면 `WorkflowRunConflictError`를 발생시킵니다. 따라서 중복 요청은 일반 `save()`로 기존 상태를 대체하지 않습니다.

초기 Node 전이를 메모리에서 만드는 동안 외부 부작용은 없습니다. 실제 서비스에서는 위험한 예약·승인 대상·작업 생성까지 데이터베이스 트랜잭션 또는 신뢰할 수 있는 분산 잠금의 같은 원자적 경계에 넣어야 합니다.

## 8. 정상 실행 결과

```text
첫 생성: True
두 번째 생성: False
저장된 action: deploy
API 중복 시작: WorkflowRunConflictError: run_id already exists: atomic-api-001
```

두 번째 상태가 `READ`여도 저장된 state가 원래 `DEPLOY`인 것이 확인 기준입니다. 승인 전에는 `execute` 이벤트가 생기지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `run_id already exists` | 이전 실행의 Checkpoint가 있습니다. | 새 작업에는 새 run ID를 사용하거나 기존 작업의 적절한 재개 경로를 사용합니다. |
| 같은 ID가 덮어써짐 | `save_if_absent()` 대신 `save()`로 시작 상태를 기록했을 수 있습니다. | 신규 시작에는 `invoke_new()`과 원자적 생성 계약을 사용합니다. |
| 여러 프로세스에서 JSON 충돌 | 로컬 파일 인스턴스 Lock은 프로세스 간 잠금을 제공하지 않습니다. | 운영 환경에서는 트랜잭션 격리 또는 분산 잠금을 제공하는 저장소를 사용합니다. |
| 승인 전 `execute` 이벤트 | 승인 Node 또는 상태 검사 우회 여부를 확인합니다. | 위험 action은 승인 대기 Checkpoint에서 명시적 `resume(..., approved=True)`만 허용합니다. |

## 10. 응용 실습

1. 완료된 안전 작업의 run ID도 `save_if_absent()`로 교체되지 않는 테스트를 작성합니다.
2. 동일 `JsonFileCheckpointer` 인스턴스에 두 상태를 생성해 첫 상태만 복원되는 테스트를 작성합니다.
3. 운영 데이터베이스에서 run ID의 유일 제약 조건과 승인 대상 버전을 같은 트랜잭션으로 설계합니다. 실제 데이터베이스를 실행하지 않습니다.

## 11. 실무 적용

원자적 생성은 단일 프로세스의 Lock만으로 끝나지 않습니다. 여러 API 인스턴스가 있는 운영 환경에서는 run ID의 테넌트 범위, 유일 제약, 트랜잭션 격리, 재시도 응답, Checkpoint 보존 기간을 설계해야 합니다.

`JsonFileCheckpointer`는 문서 학습용입니다. 여러 프로세스나 독립 인스턴스의 동시 쓰기를 안전하게 처리하지 않으므로 승인 기록이나 운영 작업 큐에 사용하면 안 됩니다. 운영 승인에는 인증된 승인자, 대상·영향 범위·정책 버전 검증, 만료, 감사 보존을 별도로 적용해야 합니다.

## 12. 과제

- **기본:** 조회 후 저장을 분리하면 왜 같은 run ID가 덮어써질 수 있는지 설명합니다.
- **응용:** 첫 `DEPLOY` 상태와 두 번째 `READ` 상태로 `save_if_absent()` 보존 테스트를 작성합니다.
- **심화:** 여러 서비스 인스턴스에서 run 생성과 승인 대상 버전을 묶는 트랜잭션 설계를 작성합니다. 실제 외부 저장소는 사용하지 않습니다.

## 13. 완료 체크리스트

- [ ] 원자적 생성과 단순 저장의 차이를 설명할 수 있다.
- [ ] 중복 시작이 기존 위험 작업 Checkpoint를 바꾸지 않음을 확인했다.
- [ ] 중복 요청이 `WorkflowRunConflictError`로 끝남을 확인했다.
- [ ] 위험 작업이 별도 명시적 승인 전 `execute`하지 않음을 확인했다.
- [ ] 메모리와 로컬 JSON Checkpointer의 보장 범위를 구분했다.
- [ ] 테스트와 정적 검사를 오프라인으로 통과시켰다.

## 14. 핵심 정리

사람 승인의 안전성은 run ID가 가리키는 상태가 바뀌지 않는다는 전제에 의존합니다. 신규 시작은 존재 확인과 저장을 분리하지 말고 원자적 생성으로 처리해야 합니다. 이 Volume의 참조 모델은 `save_if_absent()`로 기존 Checkpoint를 보존하지만, 운영 환경에서는 다중 인스턴스에 맞는 트랜잭션 저장소와 별도의 승인 정책이 필요합니다.
