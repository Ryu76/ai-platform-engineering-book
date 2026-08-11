# run ID 충돌 방지와 재전송 안전성

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- Workflow run ID를 승인 상태의 안정적인 식별자로 취급한다.
- 같은 run ID의 두 번째 시작 요청을 명시적으로 거부한다.
- 재전송이 위험 작업의 승인 대기 Checkpoint를 다른 상태로 덮어쓰지 못함을 검증한다.
- 충돌 거부와 승인 재개를 서로 다른 전이로 유지한다.

## 2. 왜 필요한가

HTTP 클라이언트와 프록시는 시간 초과 뒤 시작 요청을 재전송할 수 있습니다. 시작 요청이 기존 run ID를 무조건 덮어쓰면, `DEPLOY` 승인 대기 상태가 `READ` 완료 상태나 다른 위험 작업 상태로 바뀔 수 있습니다. 이 경우 승인자가 검토한 대상과 실제 재개 대상의 연결이 깨집니다.

이 Volume의 오프라인 참조 모델은 run ID를 새 실행의 식별자이자 Checkpoint 키로 사용합니다. `WorkflowApiAdapter.start()`는 이미 저장된 ID를 발견하면 `WorkflowRunConflictError`를 발생시키고 기존 상태를 변경하지 않습니다.

## 3. 핵심 개념

- **run ID**: 한 번 시작된 Workflow의 안정적인 식별자입니다.
- **충돌(Conflict)**: 이미 Checkpoint가 있는 run ID로 새 시작을 시도한 경우입니다.
- **재전송 안전성**: 동일 시작 요청의 반복이 기존 상태·감사 이벤트·승인 대기를 바꾸지 않는 성질입니다.
- **재개(Resume)**: 기존의 `WAITING_FOR_APPROVAL` Checkpoint에 별도 승인 결정을 적용하는 전이입니다.
- **409 매핑**: 실제 HTTP route가 충돌 도메인 오류를 `409 Conflict`로 표현할 수 있는 전송 계층 선택입니다.

> [!WARNING]
> 이 장은 HTTP 서버, 네트워크, 실제 배포를 실행하지 않습니다. 충돌 거부 후 승인된 재개도 `execute`라는 결정론적 학습용 상태 전이만 만들며 외부 시스템을 변경하지 않습니다.

## 4. 동작 구조

```text
POST /workflows (run_id=deploy-001, DEPLOY)
  └── plan → approval → WAITING_FOR_APPROVAL

POST /workflows (run_id=deploy-001, READ)
  └── WorkflowRunConflictError
      기존 Checkpoint 변경 없음

POST /workflows/deploy-001/approval (approved=true)
  └── approval → execute → COMPLETED     # 오프라인 시뮬레이션
```

중요한 점은 두 번째 시작 요청이 “새로운 작업”처럼 기존 Checkpoint를 교체하지 않는다는 것입니다. 기존 `DEPLOY` 상태만 별도 승인 요청으로 재개할 수 있습니다.

## 5. 실습 환경

다음 파일을 사용합니다.

- `src/ai_platform/graph/api.py`
- `src/ai_platform/graph/workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

현재 프로젝트에는 FastAPI 서버 의존성이 없습니다. 따라서 충돌은 프레임워크 독립 도메인 오류로 검사하며, 운영 route는 승인된 별도 범위에서 HTTP 상태 코드로 변환합니다.

## 6. 단계별 실습

### 6.1 위험 작업을 한 번 시작한다

```python
from ai_platform.graph import ActionKind, StartWorkflowRequest, WorkflowApiAdapter

adapter = WorkflowApiAdapter()
waiting = adapter.start(
    request=StartWorkflowRequest(
        run_id="conflict-demo-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
)
assert waiting.status.value == "waiting_for_approval"
```

### 6.2 같은 ID의 두 번째 시작을 거부한다

```python
import pytest
from ai_platform.graph import WorkflowRunConflictError

with pytest.raises(WorkflowRunConflictError, match="run_id already exists"):
    adapter.start(
        request=StartWorkflowRequest(
            run_id="conflict-demo-001",
            task="로컬 문서를 읽는다",
            action=ActionKind.READ,
        )
    )
```

### 6.3 기존 위험 작업만 명시적 승인으로 재개한다

```python
from ai_platform.graph import ApprovalRequest

completed = adapter.resume(
    run_id="conflict-demo-001",
    request=ApprovalRequest(approved=True),
)
assert completed.action is ActionKind.DEPLOY
assert [event.node for event in completed.events] == [
    "plan", "approval", "approval", "execute"
]
```

### 6.4 계약 검사 실행

```bash
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

어댑터는 새 상태를 만들기 전에 Checkpointer에서 같은 ID를 조회합니다.

```python
try:
    self._workflow.checkpoint(run_id=run_id)
except KeyError:
    return
raise WorkflowRunConflictError(f"run_id already exists: {run_id}")
```

`KeyError`는 아직 저장된 실행이 없음을 뜻하므로 시작을 허용합니다. 저장된 실행이 있으면 `invoke()`를 호출하지 않으므로 plan 이벤트, 작업 내용, action, 승인 상태가 바뀌지 않습니다. Checkpointer 손상 같은 다른 오류는 충돌 없음으로 취급하지 않고 호출자에게 전파합니다.

## 8. 정상 실행 결과

```text
첫 시작: waiting_for_approval
중복 시작: WorkflowRunConflictError: run_id already exists: conflict-demo-001
승인 재개: completed
이벤트: plan | approval | approval | execute
```

중복 시작 시 새 `READ`의 `execute` 이벤트가 생기지 않는 것이 계약입니다. 재개 결과의 action이 원래 `DEPLOY`인 것도 상태 보존을 확인합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `run_id already exists` | 이미 같은 ID의 Checkpoint가 있습니다. | 새 실행에는 새 run ID를 사용하거나, 기존 작업이면 적절한 재개 API를 사용합니다. |
| `checkpoint not found` | 시작하지 않은 ID를 재개했습니다. | 먼저 한 번만 시작해 승인 대기 Checkpoint를 만듭니다. |
| `waiting state` | 완료·거절 상태를 다시 승인하려 했습니다. | `waiting_for_approval`인 위험 작업만 한 번 재개합니다. |
| Checkpointer 읽기 오류 | 저장소가 손상되었거나 입력이 유효하지 않습니다. | 오류를 무시해 새 실행으로 덮어쓰지 말고 저장소 복구 절차를 적용합니다. |

## 10. 응용 실습

1. 완료된 안전 작업 ID를 다시 시작할 때도 같은 충돌 계약이 적용되는 테스트를 작성합니다.
2. `JsonFileCheckpointer`를 주입한 새 어댑터 인스턴스가 기존 run ID 충돌을 거부하는 테스트를 작성합니다.
3. 운영 API의 idempotency key와 run ID의 역할을 분리하는 설계를 작성합니다. 실제 서버나 저장소를 실행하지 않습니다.

## 11. 실무 적용

운영 시스템에서는 run ID의 생성 주체, 테넌트 범위, 보존 기간, 재시도 정책을 명확히 해야 합니다. HTTP idempotency key는 동일한 요청을 같은 결과로 돌려주는 계약일 수 있지만, run ID 충돌 거부는 기존 승인 상태를 교체하지 않는 최소 안전 정책입니다. 둘을 같은 문자열이나 같은 정책으로 가정하지 않아야 합니다.

충돌 오류를 409로 매핑하더라도 응답에 민감한 Checkpoint 내용이나 승인자 정보를 포함하지 않아야 합니다. 실제 승인 엔드포인트는 인증된 주체, 권한, 대상, 영향 범위, 정책 버전과 만료를 독립적으로 검증해야 합니다.

## 12. 과제

- **기본:** 위험 작업의 run ID를 다시 시작하면 안 되는 이유를 설명합니다.
- **응용:** 중복 시작 뒤 기존 `DEPLOY`만 재개되는 테스트를 작성합니다.
- **심화:** 다중 테넌트 환경에서 run ID 충돌 범위를 설계하되, 실제 데이터베이스나 HTTP 서버를 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] 같은 run ID의 시작 요청이 `WorkflowRunConflictError`를 내는 것을 확인했다.
- [ ] 충돌 요청이 기존 승인 대기 상태를 덮어쓰지 않음을 확인했다.
- [ ] 충돌 뒤에도 원래 위험 action만 명시적 승인으로 재개됨을 확인했다.
- [ ] 충돌 처리 중 `execute`가 자동으로 생기지 않음을 확인했다.
- [ ] 테스트와 정적 검사가 오프라인으로 통과함을 확인했다.

## 14. 핵심 정리

사람 승인은 특정 작업·대상·상태에 연결되어야 합니다. 따라서 새 시작 요청이 기존 run ID의 Checkpoint를 덮어쓰게 하면 안 됩니다. `WorkflowApiAdapter`는 중복 시작을 명시적으로 거부하고 기존 상태를 보존하며, 위험 작업은 별도의 명시적 승인 재개 뒤에만 오프라인 `execute` 전이로 진행합니다.
