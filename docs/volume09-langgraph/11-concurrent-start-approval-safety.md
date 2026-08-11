# 동시 시작 재전송과 승인 대기 상태 보존

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 같은 run ID의 동시 시작 요청을 하나의 생성 성공과 나머지 충돌로 구분한다.
- 동시 재전송이 위험 작업의 승인 대기 Checkpoint를 바꾸지 못함을 검사한다.
- 생성 경쟁의 결과와 위험 작업의 실행 승인을 별도 경계로 유지한다.
- 메모리와 로컬 JSON Checkpointer의 동시성 보장 범위를 운영 저장소와 구분한다.

## 2. 왜 필요한가

클라이언트 재시도, 이중 클릭, 타임아웃 뒤 재전송은 같은 시작 요청을 거의 동시에 보낼 수 있습니다. 단순한 사전 조회는 두 요청 모두 run ID가 없다고 관찰하게 만들 수 있습니다. 위험 작업에서는 나중 요청이 처음 요청의 승인 대기를 교체하거나 승인 대상과 다른 상태를 만들면 안 됩니다.

`save_if_absent()`는 같은 Checkpointer 인스턴스에서 존재 확인과 첫 저장을 하나의 Lock 경계로 묶습니다. 따라서 동시에 같은 `DEPLOY` 요청이 여러 번 도착해도 하나만 `WAITING_FOR_APPROVAL` Checkpoint를 만들고, 나머지는 `WorkflowRunConflictError`로 끝납니다.

> [!WARNING]
> 이 장의 동시성 검증은 로컬 스레드와 메모리 상태만 사용합니다. `DEPLOY`는 실제 배포를 하지 않으며, 생성 성공 뒤에도 별도의 엄격한 Boolean 승인 전에는 `execute` Node에 도달하지 않습니다.

## 3. 핵심 개념

- **동시 재전송:** 같은 논리적 시작 요청이 겹쳐 도착하는 상황입니다.
- **단일 생성자:** 같은 run ID에는 정확히 한 요청만 첫 Checkpoint를 기록합니다.
- **충돌 응답:** 나머지 요청은 기존 Checkpoint를 읽거나 바꾸지 않고 충돌 오류로 끝납니다.
- **승인 불변성:** 생성 경쟁에서 이긴 위험 작업도 승인 대기 상태일 뿐 실행 권한을 얻지 않습니다.
- **보장 범위:** `MemoryCheckpointer`는 한 프로세스의 한 인스턴스에서 Lock으로 보호합니다. `JsonFileCheckpointer`도 한 인스턴스의 스레드 범위만 보호합니다.

## 4. 동작 구조

```text
동시 요청 8개: start(atomic-concurrent-001, DEPLOY)
    ├── 요청 1 ── save_if_absent(...) -> True  -> WAITING_FOR_APPROVAL
    └── 요청 2..8 ── save_if_absent(...) -> False -> WorkflowRunConflictError

저장된 상태: plan -> approval, execute 없음
명시적 승인: resume(..., approved=True) -> approval -> execute -> COMPLETED
```

스레드가 어느 순서로 Lock을 얻는지는 중요하지 않습니다. 이 실습의 모든 동시 요청은 같은 task와 `DEPLOY` action을 사용하므로, 관찰 가능한 Checkpoint와 감사 이벤트는 항상 같습니다.

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

네트워크, HTTP 서버, 실제 배포, 외부 Checkpointer는 실행하지 않습니다.

## 6. 단계별 실습

### 6.1 같은 요청을 로컬 스레드에서 시작한다

```python
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from ai_platform.graph import (
    ActionKind,
    DeterministicWorkflow,
    MemoryCheckpointer,
    StartWorkflowRequest,
    WorkflowApiAdapter,
    WorkflowRunConflictError,
)

checkpointer = MemoryCheckpointer()
adapter = WorkflowApiAdapter(
    workflow=DeterministicWorkflow(checkpointer=checkpointer)
)
request = StartWorkflowRequest(
    run_id="atomic-concurrent-001",
    task="학습용 배포를 준비한다",
    action=ActionKind.DEPLOY,
)

barrier = Barrier(8)

def start_once() -> str:
    barrier.wait(timeout=5)
    try:
        return adapter.start(request=request).status.value
    except WorkflowRunConflictError:
        return "conflict"

with ThreadPoolExecutor(max_workers=8) as executor:
    outcomes = list(executor.map(lambda _: start_once(), range(8)))

assert outcomes.count("waiting_for_approval") == 1
assert outcomes.count("conflict") == 7
```

### 6.2 Checkpoint와 승인 경계를 확인한다

```python
from ai_platform.graph import ApprovalRequest, WorkflowStatus

waiting = checkpointer.load(run_id="atomic-concurrent-001")
assert waiting.status is WorkflowStatus.WAITING_FOR_APPROVAL
assert [event.node for event in waiting.events] == ["plan", "approval"]

completed = adapter.resume(
    run_id="atomic-concurrent-001",
    request=ApprovalRequest(approved=True),
)
assert completed.status is WorkflowStatus.COMPLETED
```

이 학습용 확인은 Checkpointer를 직접 읽어 저장된 상태를 비교합니다. 실제 HTTP route는 응답과 권한 검증을 통해 상태를 다뤄야 하며, 내부 구현에 의존하면 안 됩니다.

### 6.3 오프라인 계약을 검사한다

```bash
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

`WorkflowApiAdapter.start()`는 `DeterministicWorkflow.invoke_new()`만 호출합니다. `invoke_new()`는 먼저 초기 상태를 순수하게 만들고, `save_if_absent()`가 `False`를 반환할 때만 충돌 오류를 발생시킵니다. 초기 상태 계산과 충돌은 실제 배포·삭제·전송을 만들지 않습니다.

`MemoryCheckpointer.save_if_absent()`는 하나의 `Lock` 안에서 dictionary 존재 확인과 상태 저장을 처리합니다. 따라서 같은 인스턴스를 공유하는 여러 스레드는 두 개의 성공 응답을 관찰할 수 없습니다.

## 8. 정상 실행 결과

```text
생성 성공: 1
충돌: 7
Checkpoint 상태: waiting_for_approval
Checkpoint events: plan | approval
명시적 승인 뒤 상태: completed
```

초기 동시 요청의 실행 순서는 달라도, 성공 수·충돌 수·승인 전 이벤트 순서는 위 계약으로 고정됩니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| 생성 성공이 둘 이상 | 시작 경로가 `save()` 또는 분리된 조회를 사용했을 수 있습니다. | 새 run 생성은 `invoke_new()`와 `save_if_absent()`만 사용합니다. |
| 승인 전에 `execute` 발생 | 생성 충돌 처리와 승인 재개를 혼동했을 수 있습니다. | 위험 action은 별도 `ApprovalRequest(approved=True)`로만 재개합니다. |
| JSON을 여러 인스턴스가 공유 | 인스턴스별 Lock은 프로세스 간 동기화를 하지 않습니다. | 운영 환경에서는 유일 제약과 트랜잭션을 가진 저장소를 사용합니다. |
| 충돌이 HTTP 성공으로 변환됨 | 전송 계층에서 충돌 오류 매핑이 빠졌을 수 있습니다. | 실제 route에서는 `WorkflowRunConflictError`를 409 Conflict로 명시적으로 매핑합니다. |

## 10. 응용 실습

1. 같은 `READ` 요청을 동시 시작해도 정확히 한 완료 Checkpoint만 생성되는 테스트를 작성합니다.
2. 같은 `MemoryCheckpointer`를 공유하는 두 Adapter가 한 run ID에 하나만 성공하는 테스트를 작성합니다.
3. 운영 데이터베이스의 유일 제약 위반을 idempotent 409 또는 기존 상태 응답으로 매핑하는 정책을 설계합니다. 실제 데이터베이스나 서버는 실행하지 않습니다.

## 11. 실무 적용

이 Lock은 단일 프로세스·단일 Checkpointer 인스턴스의 학습 계약입니다. 다중 worker, 다중 API 인스턴스, 컨테이너 재시작이 있는 서비스에서는 저장소의 run ID 유일 제약과 생성·승인 대상 기록을 같은 트랜잭션 경계에 넣어야 합니다.

실제 위험 작업의 승인은 인증된 승인자, 승인 대상의 버전·영향 범위, 만료, 감사 보존, 권한 분리를 추가로 검증해야 합니다. 생성 충돌 방지는 이 정책을 대체하지 않으며, 승인 전 실행을 허용하지 않습니다.

## 12. 과제

- **기본:** 왜 동시 요청 모두가 사전 `load()`에서 부재를 볼 수 있는지 설명합니다.
- **응용:** 동시 `DEPLOY` 시작 후 승인 전 `execute`가 없음을 검사합니다.
- **심화:** 다중 인스턴스에서 run 생성과 승인 대상 버전을 묶을 데이터베이스 트랜잭션을 설계합니다. 실제 외부 저장소는 사용하지 않습니다.

## 13. 완료 체크리스트

- [ ] 같은 run ID의 동시 시작에서 정확히 하나만 생성됨을 확인했다.
- [ ] 나머지 요청이 기존 Checkpoint를 바꾸지 않고 충돌함을 확인했다.
- [ ] 위험 작업이 생성 성공 뒤에도 승인 대기임을 확인했다.
- [ ] 명시적 승인 전 `execute`가 없음을 확인했다.
- [ ] Checkpointer 인스턴스의 동시성 보장 범위를 구분했다.
- [ ] 테스트와 정적 검사를 오프라인으로 통과시켰다.

## 14. 핵심 정리

동시 재전송 안전성은 시작 요청의 수가 아니라 run ID당 첫 상태가 하나만 기록되는지로 판단합니다. 이 Volume의 `MemoryCheckpointer`는 하나의 Lock 안에서 원자적 생성을 보장하고, 위험 작업은 그 성공 후에도 독립적인 사람 승인 경계에서 멈춥니다. 운영 환경에서는 저장소 수준의 유일 제약과 트랜잭션으로 같은 계약을 확장해야 합니다.
