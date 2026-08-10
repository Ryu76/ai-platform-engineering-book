# 제한된 재시도와 Error Node

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- 실패와 최종 실패를 상태 기반 Workflow의 서로 다른 종료 경계로 모델링한다.
- Error Node가 재시도 상한을 확인한 뒤에만 실행 Edge로 되돌아가게 한다.
- 동일한 `RetryPlan` 입력에서 동일한 시도 횟수와 이벤트 순서가 나오도록 테스트한다.
- 위험 작업의 재시도가 사람 실행 승인을 우회하지 않음을 확인한다.

## 2. 왜 필요한가

일시적 실패를 무한 반복하면 비용과 대기 시간이 증가하고, 어떤 요청이 왜 끝나지 않는지 알기 어렵습니다. 반대로 첫 실패에서 즉시 종료하면 회복 가능한 오류도 처리하지 못합니다. 제한된 재시도(Bounded Retry)는 이 두 문제 사이에 명확한 상한을 둡니다.

재시도 횟수는 Node 내부의 숨은 반복문이 아니라 State와 Error Node의 감사 이벤트로 남겨야 합니다. 그러면 성공, 재시도, 상한 소진의 각 경로를 테스트로 고정할 수 있습니다. 이 장의 실패는 실제 네트워크·API·파일 작업의 실패가 아닙니다. 호출자가 제공하는 결정론적 입력만 사용합니다.

## 3. 핵심 개념

- **시도(Attempt)**: `execute` Node가 한 번 만든 오프라인 실행 시뮬레이션입니다.
- **RetryPlan**: `failures_before_success`, `max_retries`, `source`를 갖는 불변 입력입니다.
- **Error Node**: `ERROR` 상태를 감사하고, 남은 재시도가 있으면 `READY`로 되돌리거나 없으면 `FAILED` END로 보냅니다.
- **재시도 상한**: 최초 시도 뒤 추가로 허용하는 최대 시도 수입니다. `max_retries=1`이면 최대 두 번 시도합니다.
- **최종 실패(FAILED)**: 상한을 소진한 종료 상태입니다. 추가 `execute` Edge는 없습니다.
- **승인 경계**: `DELETE`, `DEPLOY`, `SEND`는 첫 시도 전에 명시적 사람 승인을 받아야 합니다. 승인 거절은 재시도 계획과 무관하게 실행 시도를 0회로 끝냅니다.

> [!WARNING]
> 재시도는 위험 작업의 승인 정책을 완화하는 기능이 아닙니다. 이 참조 모델에서 위험 작업은 `WAITING_FOR_APPROVAL` Checkpoint에 먼저 저장됩니다. `resume(approved=True)` 전에는 첫 시도도, Error Node도 실행되지 않습니다. 모든 결과는 외부 시스템을 변경하지 않는 문자열입니다.

## 4. 동작 구조

```text
START
  │
  ▼
plan → approval Conditional Edge
          │
  ┌───────┴────────┐
  ▼                ▼
read/transform   delete/deploy/send
  │                │
  ▼                ▼
execute       WAITING_FOR_APPROVAL
  │                │ 사람 승인
  │                ▼
  │             execute
  ▼
success ─────────────────────────────► COMPLETED (END)
  │
  ▼ failure
ERROR
  │
  ▼
Error Node ── remaining retry ──► READY → execute
  │
  └── retry limit exhausted ────► FAILED (END)
```

`RetryPlan(failures_before_success=1, max_retries=1)`은 첫 `execute`를 `ERROR`로 만들고 Error Node가 한 번 재시도시킨 뒤 두 번째 `execute`를 성공시킵니다. `failures_before_success=2, max_retries=1`은 두 번째 실패 뒤 `FAILED`로 끝납니다.

## 5. 실습 환경

다음 파일을 사용합니다.

- `src/ai_platform/graph/state.py`
- `src/ai_platform/graph/nodes.py`
- `src/ai_platform/graph/workflow.py`
- `examples/volume09/retry_error_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

이 실습은 `langgraph` 패키지, API 키, 네트워크, 실제 저장소, 배포 도구를 요구하지 않습니다. 현재 프로젝트 의존성을 바꾸지 않고 LangGraph의 State, Conditional Edge, Error Node 개념을 직접 구현한 참조 모델을 사용합니다.

## 6. 단계별 실습

### 6.1 회복 가능한 한 번의 실패 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run python examples/volume09/retry_error_workflow.py
```

예제는 안전한 `TRANSFORM` 작업을 첫 번째 시도에서만 실패하도록 고정합니다. Error Node는 `1/1` 재시도를 허용하고, 두 번째 시도는 완료됩니다. 외부 파일을 수정하거나 네트워크에 연결하지 않습니다.

### 6.2 상한 소진 경로 확인

```python
from ai_platform.graph import ActionKind, RetryPlan, RetryWorkflow

failed = RetryWorkflow().invoke(
    run_id="retry-failed-001",
    task="로컬 문자열을 변환한다",
    action=ActionKind.TRANSFORM,
    retry_plan=RetryPlan(failures_before_success=2, max_retries=1),
)

assert failed.status == "failed"
assert failed.attempt_count == 2
assert [event.node for event in failed.events] == [
    "plan", "approval", "execute", "error", "execute", "error"
]
```

두 번째 `error` 이벤트가 최종 실패를 기록합니다. 그 뒤에는 추가 `execute`가 없으므로 무한 반복이 발생하지 않습니다.

### 6.3 위험 작업의 승인 경계 확인

```python
from ai_platform.graph import ActionKind, RetryPlan, RetryWorkflow

workflow = RetryWorkflow()
waiting = workflow.invoke(
    run_id="retry-risky-001",
    task="학습용 배포를 준비한다",
    action=ActionKind.DEPLOY,
    retry_plan=RetryPlan(failures_before_success=1, max_retries=1),
)
assert waiting.status == "waiting_for_approval"
assert waiting.attempt_count == 0

rejected = workflow.resume(run_id="retry-risky-001", approved=False)
assert rejected.status == "rejected"
assert rejected.attempt_count == 0
```

승인 거절은 시도와 Error Node를 모두 건너뜁니다. 학습용 `DEPLOY`도 실제 배포 명령을 실행하지 않습니다.

### 6.4 계약 테스트와 정적 검사 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

테스트는 회복 성공, 재시도 상한의 최종 실패, 위험 작업의 승인 전 무시행, 음수 재시도 입력 거부를 확인합니다.

## 7. 코드 설명

`RetryPlan`은 외부 오류를 재현하려고 네트워크를 끊는 대신, 필요한 실패 횟수를 입력으로 고정합니다.

```python
retry_plan=RetryPlan(failures_before_success=1, max_retries=1)
```

`retry_execute_node()`는 `attempt_count`를 하나 증가시킨 뒤 해당 시도가 실패해야 하는지 State로 판단합니다. 실패는 `ERROR`로만 전이하며 결과를 만들지 않습니다. `error_node()`만 다음 Edge를 선택합니다.

```python
while state.status is WorkflowStatus.READY:
    state = retry_execute_node(state)
    if state.status is WorkflowStatus.ERROR:
        state = error_node(state)
```

`error_node()`는 사용한 재시도가 상한 미만일 때만 `READY`를 반환합니다. 상한에 도달하면 `FAILED`를 반환하므로 `while` 조건이 거짓이 됩니다. 이 구조는 종료 조건을 코드와 이벤트 순서 모두에서 확인하게 합니다.

## 8. 정상 실행 결과

6.1의 출력은 다음과 같습니다.

```text
status=completed
attempts=2
events=plan | approval | execute | error | execute
```

`uv run pytest tests/unit/test_volume09_graph.py -q`는 통과 테스트 수와 종료 코드 0을 반환해야 합니다. Ruff와 mypy도 오류 없이 종료되어야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `failures_before_success must not be negative` | 실패 횟수가 음수입니다. | 0 이상의 결정론적 값을 전달합니다. |
| `max_retries must not be negative` | 재시도 상한이 음수입니다. | 0 이상으로 지정합니다. `0`은 최초 시도 뒤 재시도를 허용하지 않습니다. |
| `error_node requires an error state` | Error Node를 성공 또는 승인 대기 상태에서 직접 호출했습니다. | 실패한 `execute`의 `ERROR` 상태에만 연결합니다. |
| `FAILED` 뒤에도 `execute`가 보임 | 최종 실패 뒤 Edge가 추가됐습니다. | `error_node()`가 `FAILED`를 반환하면 반복을 끝내도록 복원합니다. |
| 위험 작업이 승인 전에 시도됨 | `approval_node()` 결과를 검사하지 않았습니다. | `WAITING_FOR_APPROVAL`을 Checkpoint에 저장하고 `resume(approved=True)` 뒤에만 실행합니다. |

## 10. 응용 실습

1. `RetryPlan.source`를 감사 이벤트에 기록하도록 테스트 우선으로 확장합니다. 실제 오류 메시지나 비밀값은 저장하지 않습니다.
2. `max_retries=0`에서 첫 실패가 즉시 `FAILED`로 끝나는 테스트를 작성합니다.
3. `FAILED` 상태의 작업을 별도 사람 검토 큐로 보낸다고 가정하고, 실제 큐 연결 없이 필요한 State 필드를 설계합니다.

## 11. 실무 적용

운영 환경에서는 오류를 재시도 가능, 영구 실패, 사용자 입력 오류, 권한 오류로 분류해야 합니다. 재시도 대상에는 지수 백오프, 지터, 시간 제한, 호출 예산, idempotency key를 함께 설계합니다. 단, 권한 부족·검증 실패·승인 거절을 자동 재시도하면 정책 우회가 될 수 있습니다.

위험한 실제 작업은 재시도마다 대상, 영향 범위, idempotency, 승인 만료를 확인해야 합니다. 승인 한 번이 여러 실제 부작용을 포괄하는지 정책으로 명시해야 하며, 이 오프라인 참조 모델의 단일 승인 경계를 그대로 운영에 복사해서는 안 됩니다.

## 12. 과제

- **기본:** `max_retries=0`과 `max_retries=1`의 최대 시도 횟수를 이벤트 순서로 설명합니다.
- **응용:** 재시도 가능한 오류와 즉시 `FAILED`로 끝내야 하는 오류를 각각 세 가지씩 분류합니다.
- **심화:** 승인 만료, idempotency key, 재시도 예산을 포함한 위험 배포 Workflow를 다이어그램으로 설계합니다. 실제 배포나 API 호출은 하지 않습니다.

## 13. 완료 체크리스트

- [ ] `RetryPlan`의 실패 횟수와 재시도 상한의 차이를 설명할 수 있다.
- [ ] Error Node가 상한 안에서만 `READY`로 돌아감을 확인했다.
- [ ] 상한 소진 뒤 `FAILED`에 도달하고 추가 시도가 없음을 확인했다.
- [ ] 위험 작업이 사람 승인 전 시도 0회임을 확인했다.
- [ ] 예제와 테스트가 API, 네트워크, 실제 파일 변경, 배포 없이 동작함을 확인했다.
- [ ] `uv run pytest tests/unit/test_volume09_graph.py -q`를 통과했다.

## 14. 핵심 정리

제한된 재시도는 실패를 숨기는 반복문이 아니라 상태 전이와 종료 조건을 명시하는 정책입니다. 이 장의 `RetryWorkflow`는 결정론적 실패 입력, 감사 가능한 Error Node, 재시도 상한, `FAILED` END를 제공하며 위험 작업은 승인 전 첫 시도조차 시작하지 못하게 합니다.
