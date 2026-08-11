# 동시 승인 재전송과 단일 오프라인 실행 기록

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 하나의 승인 대기 Checkpoint를 여러 승인 요청이 동시에 소비하려 할 때의 경쟁을 설명한다.
- 비교-교체(compare-and-swap) 저장으로 하나의 승인 결정만 기록한다.
- 중복 승인 요청을 완료 응답이나 자동 재실행 대신 충돌로 처리한다.
- 이 오프라인 모델의 실행 시뮬레이션과 실제 위험 작업의 실행 권한을 구분한다.

## 2. 왜 필요한가

승인 화면의 이중 클릭, 클라이언트 재시도, 같은 승인자의 여러 탭은 같은 run ID에 대한 승인 요청을 겹치게 만들 수 있습니다. 단순한 `load() → 결정 → save()` 흐름에서는 두 요청이 모두 같은 `WAITING_FOR_APPROVAL` 상태를 읽고 각각 실행 결과를 저장할 수 있습니다.

이 Volume은 `save_if_current()`로 읽은 상태와 현재 Checkpoint가 같을 때만 후보 상태를 기록합니다. 같은 메모리 Checkpointer 인스턴스를 공유하는 요청 중 하나만 승인 대기를 소비하고, 나머지는 `WorkflowRunConflictError`가 됩니다.

> [!WARNING]
> 이 장은 상태와 감사 이벤트만 다룹니다. `DEPLOY`는 실제 배포하지 않으며, 승인 요청이 성공해도 결과는 결정론적인 오프라인 시뮬레이션입니다. 운영 환경의 실제 위험 작업에는 인증된 승인자, 대상 버전, 만료, 멱등성 키, 트랜잭션 저장소 및 별도 실행 워커가 필요합니다.

## 3. 핵심 개념

- **승인 대기 Checkpoint:** 위험 ActionKind가 명시적 Boolean 승인 전 멈춘 불변 상태입니다.
- **비교-교체:** 저장소의 현재 상태가 읽었던 상태와 같을 때만 새 상태로 교체하는 원자적 연산입니다.
- **단일 소비자:** 같은 승인 대기 상태는 정확히 하나의 승인 요청만 소비합니다.
- **승인 충돌:** 이미 다른 요청이 상태를 소비했거나 변경했으면 후속 요청은 상태를 바꾸지 않고 충돌합니다.
- **오프라인 실행:** `execute` 이벤트와 결과는 외부 시스템을 바꾸지 않는 학습용 상태 전이입니다.

## 4. 동작 구조

```text
8개 동시 approval(approval-demo-001, approved=True)
                  |
                  v
현재 Checkpoint: WAITING_FOR_APPROVAL (plan | approval)
                  |
        save_if_current(expected=waiting)
          |                         |
          v                         v
요청 1: True                    요청 2..8: False
approval -> execute             WorkflowRunConflictError
          |
          v
COMPLETED (plan | approval | approval | execute)
```

후속 요청은 저장된 `COMPLETED` 상태를 다시 승인하거나 `execute` 이벤트를 추가하지 않습니다. API 어댑터는 더 이상 승인 대기가 아니라는 내부 오류도 충돌 계약으로 변환합니다.

## 5. 실습 환경

사용 파일은 다음과 같습니다.

- `src/ai_platform/graph/checkpointer.py`
- `src/ai_platform/graph/workflow.py`
- `src/ai_platform/graph/api.py`
- `examples/volume09/concurrent_approval_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

이 실습은 로컬 스레드와 메모리 Checkpointer만 사용합니다. HTTP 서버, 네트워크, 실제 배포, 파일 삭제, 비밀값은 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 위험 작업을 승인 대기 상태로 시작한다

```python
from ai_platform.graph import ActionKind, StartWorkflowRequest, WorkflowApiAdapter

adapter = WorkflowApiAdapter()
waiting = adapter.start(
    request=StartWorkflowRequest(
        run_id="approval-demo-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
)
assert waiting.status.value == "waiting_for_approval"
assert [event.node for event in waiting.events] == ["plan", "approval"]
```

### 6.2 같은 엄격한 승인 요청을 동시에 보낸다

```python
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from ai_platform.graph import ApprovalRequest, WorkflowRunConflictError

barrier = Barrier(8)

def approve_once() -> str:
    barrier.wait(timeout=5)
    try:
        return adapter.resume(
            run_id="approval-demo-001",
            request=ApprovalRequest(approved=True),
        ).status.value
    except WorkflowRunConflictError:
        return "conflict"

with ThreadPoolExecutor(max_workers=8) as executor:
    outcomes = list(executor.map(lambda _: approve_once(), range(8)))

assert outcomes.count("completed") == 1
assert outcomes.count("conflict") == 7
```

### 6.3 예제와 계약을 실행한다

```bash
uv run python examples/volume09/concurrent_approval_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

`DeterministicWorkflow.resume()`은 먼저 승인 대기 State를 읽고, `resolve_approval_node()`와 `execute_node()`가 만드는 후보 상태를 메모리에서 계산합니다. 두 Node는 외부 부작용이 없는 순수 전이입니다. 이후 `save_if_current(run_id, expected_state, state)`가 하나의 Lock 안에서 비교와 저장을 수행합니다.

`MemoryCheckpointer`는 같은 인스턴스의 스레드 범위에서 Lock으로 이 연산을 보호합니다. `JsonFileCheckpointer`도 같은 인스턴스 안에서 공개 JSON State를 비교·교체할 수 있지만, 독립 인스턴스나 프로세스 간에는 보장하지 않습니다.

`WorkflowApiAdapter.resume()`은 이미 소비된 승인 대기를 재개하려는 요청을 충돌로 공개합니다. 실제 FastAPI route는 이 오류를 HTTP 409으로 매핑할 수 있지만, 이 범위에서는 서버를 시작하지 않습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/concurrent_approval_workflow.py
completed=1
conflicts=7
checkpoint=completed
events=plan | approval | approval | execute
```

어떤 스레드가 성공하는지는 중요하지 않습니다. 성공 수, 충돌 수, 최종 상태 및 감사 이벤트는 고정됩니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `completed=2` 이상 | 승인 경로가 무조건 `save()`를 사용했을 수 있습니다. | 승인 결과는 `save_if_current()`가 성공할 때만 기록합니다. |
| `conflicts=0` | 각 요청이 다른 Checkpointer를 사용했을 수 있습니다. | 경쟁을 검사할 때 모든 요청에 같은 Checkpointer 인스턴스를 주입합니다. |
| `workflow approval is no longer pending` | 다른 요청이 먼저 승인 대기를 소비했습니다. | 기존 상태를 재개하지 말고 충돌로 처리하며, 클라이언트는 최신 상태를 조회합니다. |
| 승인 전에 `execute`가 나타남 | 시작과 재개 경계가 분리되지 않았습니다. | 위험 ActionKind는 `start()`에서 반드시 `WAITING_FOR_APPROVAL`을 반환해야 합니다. |

## 10. 응용 실습

1. 8개의 동시 `approved=False` 요청에서 하나의 `REJECTED` 상태와 7개의 충돌을 확인하는 테스트를 작성합니다.
2. 서로 다른 `run_id` 8개를 동시에 승인해 각각 한 번씩 완료되는지 확인합니다.
3. JSON Checkpointer의 단일 인스턴스에서 비교-교체 계약을 테스트합니다. 별도 인스턴스나 프로세스 동시성은 실행하지 않습니다.

## 11. 실무 적용

운영 승인에는 Boolean만으로 충분하지 않습니다. 승인자 인증·권한, 승인 대상의 정확한 버전과 영향 범위, 승인 만료, 취소, 불변 감사 로그, 요청 멱등성 키 및 정책 변경 이력을 함께 저장해야 합니다.

실제 실행은 Checkpoint 비교-교체와 같은 데이터베이스 트랜잭션 또는 메시지 outbox로 예약한 뒤, 승인된 대상만 실행하는 분리된 워커가 수행해야 합니다. 외부 배포·삭제·전송을 State 계산 뒤에 즉시 호출하면 프로세스 장애와 중복 실행을 막을 수 없습니다.

## 12. 과제

- **기본:** `load() → save()`가 동시 승인에서 두 결과를 기록할 수 있는 순서를 설명합니다.
- **응용:** `save_if_current()`가 기존 상태와 다른 후보를 거부하는 단위 테스트를 작성합니다.
- **심화:** 승인자 신원, 대상 버전, 만료 시간, 멱등성 키를 포함한 운영용 승인 레코드 스키마를 설계합니다. 외부 저장소나 배포는 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] 동시 시작과 동시 승인의 경쟁 지점을 구분할 수 있다.
- [ ] 비교-교체가 하나의 승인 대기 상태를 한 번만 소비함을 확인했다.
- [ ] 중복 승인 요청이 `execute` 이벤트를 추가하지 않음을 확인했다.
- [ ] 위험 작업이 별도 strict Boolean 승인 전에는 대기 상태에 머묾을 확인했다.
- [ ] 메모리·JSON Checkpointer의 인스턴스 내 스레드 보장 범위를 설명할 수 있다.
- [ ] 예제, 테스트, 정적 검사를 오프라인으로 통과시켰다.

## 14. 핵심 정리

동시 승인 재전송은 시작 재전송과 별도의 경쟁 조건입니다. 이 Volume의 오프라인 참조 모델은 Checkpointer의 비교-교체 연산으로 하나의 `WAITING_FOR_APPROVAL` 상태를 한 번만 소비하고, 나머지 요청은 충돌로 끝냅니다. 이는 실제 위험 작업 실행의 완전한 보장은 아니며, 운영 환경에서는 승인 정책·트랜잭션·멱등성·분리된 실행 경계를 추가해야 합니다.
