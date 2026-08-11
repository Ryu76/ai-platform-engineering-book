# 단일 JSON Checkpointer 인스턴스의 동시 승인 안전성

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 로컬 JSON Checkpoint의 영속성과 다중 인스턴스 동시성 보장을 구분한다.
- 같은 `JsonFileCheckpointer` 인스턴스에서 동시 승인 요청 하나만 Checkpoint를 소비함을 검증한다.
- 비교-교체 저장 실패를 중복 완료가 아닌 충돌로 처리한다.
- 실제 위험 작업에 필요한 운영용 트랜잭션 경계를 설명한다.

## 2. 왜 필요한가

JSON 파일은 프로세스 재시작 뒤에도 상태를 보존하지만, 파일이 존재한다는 사실만으로 동시 승인이 안전해지지는 않습니다. 이 참조 모델은 한 `JsonFileCheckpointer` 인스턴스의 Lock 안에서 현재 JSON State 비교와 파일 교체를 묶습니다. 따라서 같은 인스턴스를 공유하는 8개 승인 재전송 가운데 하나만 `WAITING_FOR_APPROVAL`을 소비합니다.

> [!WARNING]
> 이 보장은 한 Python 프로세스 안의 한 Checkpointer 인스턴스에만 적용됩니다. 독립 인스턴스, 여러 프로세스, 네트워크 파일 시스템 또는 실제 배포·삭제·전송에는 적용되지 않습니다. `DEPLOY` 결과는 외부 시스템을 변경하지 않는 결정론적 오프라인 시뮬레이션입니다.

## 3. 핵심 개념

- **영속 Checkpoint:** 공개 Workflow State를 로컬 JSON 파일에 저장해 새 인스턴스에서도 복원하는 학습용 저장소입니다.
- **인스턴스 내 Lock:** 같은 `JsonFileCheckpointer` 객체를 공유하는 스레드의 읽기·비교·파일 교체를 직렬화합니다.
- **비교-교체:** 현재 State가 승인 대기 State와 정확히 같을 때만 승인 후보 State를 기록합니다.
- **충돌:** 다른 요청이 먼저 승인 대기를 소비했으면 후속 요청은 상태를 변경하지 않고 `WorkflowRunConflictError`가 됩니다.
- **운영 저장소:** 다중 프로세스 실행에는 데이터베이스 compare-and-swap 또는 트랜잭션이 필요한 별도 경계입니다.

## 4. 동작 구조

```text
8개 동시 approval (같은 JsonFileCheckpointer 인스턴스)
                         |
                         v
JSON: WAITING_FOR_APPROVAL (plan | approval)
                         |
              instance Lock + save_if_current
                    |                    |
                    v                    v
          1개: COMPLETED          7개: conflict
          approval | execute      JSON을 다시 쓰지 않음
```

성공하는 스레드는 실행마다 달라도 성공 수, 충돌 수, 최종 State와 감사 이벤트는 고정됩니다.

## 5. 실습 환경

사용 파일은 다음과 같습니다.

- `src/ai_platform/graph/checkpointer.py`
- `src/ai_platform/graph/workflow.py`
- `examples/volume09/json_concurrent_approval_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

예제는 `TemporaryDirectory` 안의 로컬 JSON 파일, 로컬 스레드, 메모리 계산만 사용합니다. HTTP 서버, 네트워크, 실제 위험 작업, 비밀값은 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 같은 JSON Checkpointer를 모든 요청에 주입한다

```python
from ai_platform.graph import DeterministicWorkflow, JsonFileCheckpointer, WorkflowApiAdapter

checkpointer = JsonFileCheckpointer(path=checkpoint_path)
adapter = WorkflowApiAdapter(
    workflow=DeterministicWorkflow(checkpointer=checkpointer)
)
```

각 스레드가 새 `JsonFileCheckpointer`를 만들면 이 장의 인스턴스 내 Lock 계약을 검사하지 못합니다.

### 6.2 위험 작업을 승인 대기로 시작한다

```python
from ai_platform.graph import ActionKind, StartWorkflowRequest

waiting = adapter.start(
    request=StartWorkflowRequest(
        run_id="json-approval-demo-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
)
assert waiting.status.value == "waiting_for_approval"
assert [event.node for event in waiting.events] == ["plan", "approval"]
```

### 6.3 동시 승인을 검증한다

```bash
uv run python examples/volume09/json_concurrent_approval_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

`DeterministicWorkflow.resume()`은 저장된 승인 대기 State를 읽어 승인·실행 시뮬레이션 후보를 만듭니다. 이 후보는 외부 부작용이 없는 불변 값입니다. `JsonFileCheckpointer.save_if_current()`는 하나의 인스턴스 Lock 안에서 파일을 읽고 기대 State를 비교한 뒤, 일치할 때만 임시 파일을 원자적으로 교체합니다.

후속 스레드는 이전 `WAITING_FOR_APPROVAL` State를 기대하지만 파일에는 이미 `COMPLETED` State가 있으므로 `False`를 받습니다. Workflow는 이를 `WorkflowRunConflictError`로 변환하며, 기존 JSON과 `execute` 이벤트를 덮어쓰지 않습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_concurrent_approval_workflow.py
completed=1
conflicts=7
checkpoint=completed
events=plan | approval | approval | execute
```

`execute`는 로컬 State 이벤트일 뿐 실제 배포를 수행하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `completed=2` 이상 | 승인 결과가 비교-교체가 아닌 무조건 저장으로 기록될 수 있습니다. | `save_if_current()` 성공 뒤에만 후보 State를 반환합니다. |
| `conflicts=0` | 모든 요청이 같은 Checkpointer 객체를 공유하지 않았을 수 있습니다. | 테스트와 예제에서 하나의 `JsonFileCheckpointer` 인스턴스를 주입합니다. |
| JSON 손상 오류 | 실습 파일을 수동으로 수정했거나 유효하지 않은 파일을 사용했을 수 있습니다. | 새 임시 디렉터리를 사용하고 Checkpointer의 스키마 검증 오류를 해결합니다. |
| 별도 프로세스에서 결과가 다름 | 이 장의 Lock 범위를 벗어났습니다. | 운영 저장소의 트랜잭션 또는 프로세스 간 잠금을 별도로 설계합니다. |

## 10. 응용 실습

1. 8개의 동시 `approved=False` 요청에서 하나의 `REJECTED`와 7개의 충돌을 확인합니다.
2. 서로 다른 run ID 8개를 같은 JSON Checkpointer 인스턴스로 승인해 각각 한 번씩 완료되는지 확인합니다.
3. 독립 인스턴스·프로세스 보장을 주장하지 않는 이유를 파일 시스템 경쟁 관점에서 설명합니다. 실제 다중 프로세스 경쟁은 실행하지 않습니다.

## 11. 실무 적용

운영 승인에는 로컬 JSON 파일 대신 다중 writer를 지원하는 저장소의 원자적 조건부 갱신이 필요합니다. 승인 레코드에는 인증된 승인자, 대상 버전, 요청 멱등성 키, 만료, 취소, 정책 버전과 불변 감사 정보를 함께 저장해야 합니다.

조건부 상태 저장만으로 실제 배포·삭제·전송의 exactly-once 실행을 보장할 수는 없습니다. 트랜잭션 outbox, 분리된 실행 워커, 대상 시스템의 멱등성 키 및 장애 복구 절차를 추가해야 합니다.

## 12. 과제

- **기본:** `save()`가 아닌 `save_if_current()`가 필요한 두 승인 요청의 순서를 설명합니다.
- **응용:** 같은 인스턴스에서 동시 거절을 검증하는 단위 테스트를 작성합니다.
- **심화:** 데이터베이스 조건부 갱신과 outbox를 포함하는 실제 위험 작업 승인·실행 설계를 작성합니다. 외부 저장소나 배포는 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] JSON 영속성과 인스턴스 내 동시성 보장을 구분할 수 있다.
- [ ] 같은 JSON Checkpointer 인스턴스의 동시 승인 하나만 성공함을 확인했다.
- [ ] 충돌 요청이 `execute` 이벤트를 추가하지 않음을 확인했다.
- [ ] 위험 작업이 strict Boolean 승인 전에는 승인 대기에 머묾을 확인했다.
- [ ] 다중 인스턴스·프로세스에 운영용 트랜잭션이 필요함을 설명할 수 있다.
- [ ] 예제, 테스트, 정적 검사를 오프라인으로 통과시켰다.

## 14. 핵심 정리

`JsonFileCheckpointer`는 영속성을 제공하지만, 동시성 보장은 같은 인스턴스의 Lock 범위에 한정됩니다. 이 오프라인 참조 모델은 그 범위에서 비교-교체로 하나의 승인 대기를 한 번만 소비하고 나머지 재전송을 충돌로 끝냅니다. 실제 위험 작업에는 이 학습용 파일 저장소를 넘어서는 인증, 트랜잭션, 멱등성, 분리된 실행 경계가 필요합니다.
