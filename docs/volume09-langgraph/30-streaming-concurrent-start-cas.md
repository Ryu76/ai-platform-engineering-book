# 동시 Streaming 시작과 단일 승인 대기 기록

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- Streaming 시작 요청의 재전송이 기존 위험 run을 덮어쓰면 안 되는 이유를 설명한다.
- 첫 `plan` Checkpoint를 원자적으로 생성하는 `stream_new()` 경계를 사용한다.
- 동시 위험 Streaming 시작 8개 중 하나만 `WAITING_FOR_APPROVAL` update를 기록하는지 검증한다.
- 충돌한 시작 요청이 `execute` update, 결과, 추가 감사 이벤트를 만들지 않음을 확인한다.

## 2. 왜 필요한가

사용자는 네트워크 지연이나 화면 중복 클릭 때문에 같은 시작 요청을 여러 번 보낼 수 있습니다. 일반적인 `stream()`의 `save()`는 학습용 순차 흐름에는 적합하지만, 새 run인지 확인하고 기록하는 작업을 원자적으로 묶지 않습니다. 따라서 동시 producer가 같은 run ID를 시작하면 위험 작업의 입력·감사 기록·승인 대기를 서로 덮어쓸 수 있습니다.

`StreamingWorkflow.stream_new()`은 첫 `plan` State를 `save_if_absent()`로 기록합니다. 먼저 성공한 producer만 plan update와 뒤의 approval update를 반환합니다. 후발 요청은 첫 update를 만들기 전에 `WorkflowRunConflictError`로 끝나므로 기존 위험 Checkpoint는 보존됩니다.

> [!WARNING]
> 이 예제는 하나의 Python 프로세스 안의 `MemoryCheckpointer`와 고정 입력만 사용합니다. 외부 API, 네트워크, 실제 배포·삭제·전송, 비밀값을 사용하지 않습니다. `DEPLOY`, `DELETE`, `SEND`은 명시적인 별도 Boolean 승인 없이는 `execute` Node에 도달하지 않습니다.

## 3. 핵심 개념

- **새 Streaming run:** 아직 존재하지 않는 run ID에 첫 상태 update를 기록하는 producer입니다.
- **원자적 생성:** `save_if_absent()`가 run ID 부재 확인과 첫 저장을 하나의 Lock 범위에서 수행하는 계약입니다.
- **checkpoint-before-yield:** 성공 producer는 consumer에 plan update를 보이기 전에 plan Checkpoint를 저장합니다.
- **시작 충돌:** 이미 생성된 run ID에 대한 후발 요청이 상태나 update를 바꾸지 못한 결과입니다.

## 4. 동작 구조

```text
동일 run_id의 Streaming 시작 A..H
             |
             +-- A -- save_if_absent 성공 --> PLAN 저장 --> plan update
             |                                      |
             |                                      +--> WAITING_FOR_APPROVAL 저장 --> approval update
             |
             +-- B..H -- save_if_absent 실패 --> conflict, update 없음

WAITING_FOR_APPROVAL --> 별도 명시적 Boolean 승인 전까지 execute 없음
```

## 5. 실습 환경

다음 명령은 Git Bash 또는 WSL 터미널에서 프로젝트 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/streaming_concurrent_start_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제의 `ThreadPoolExecutor`는 동일 Python 프로세스에서 8개의 같은 run ID 시작을 동시에 시도합니다. 파일·네트워크·외부 서비스는 만들거나 호출하지 않습니다.

## 6. 단계별 실습

### 6.1 공유 Checkpointer를 준비한다

```python
checkpointer = MemoryCheckpointer()
workflow = StreamingWorkflow(checkpointer=checkpointer)
```

같은 Checkpointer가 run ID별 원자적 생성 상태를 보관합니다. 프로세스 종료 뒤에는 상태가 사라집니다.

### 6.2 신규 전용 Streaming API를 사용한다

```python
updates = tuple(
    workflow.stream_new(
        run_id="streaming-concurrent-start-demo-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
)
```

성공한 요청은 `plan`, `approval` 순서의 update를 받습니다. 위험 작업의 최종 State는 아직 `WAITING_FOR_APPROVAL`입니다.

### 6.3 충돌과 승인 경계를 확인한다

```python
checkpoint = checkpointer.load(run_id="streaming-concurrent-start-demo-001")
assert checkpoint.status is WorkflowStatus.WAITING_FOR_APPROVAL
assert [event.node for event in checkpoint.events] == ["plan", "approval"]
assert checkpoint.result is None
```

후발 요청은 `WorkflowRunConflictError`를 받으며 update가 없습니다. 자동 재시도로 run을 덮어쓰지 말고 최신 Checkpoint를 조회해야 합니다.

## 7. 코드 설명

`stream_new()`은 `WorkflowState.start()`와 `plan_node()`로 후보 State를 만들고, 첫 `plan` State에만 `save_if_absent()`를 적용합니다. 이 호출이 실패하면 generator는 첫 `yield` 전에 충돌을 발생시킵니다.

생성에 성공한 producer는 저장된 plan update를 내보낸 뒤 기존 Streaming 흐름과 같은 방식으로 Approval Node를 저장하고 update를 냅니다. 위험 ActionKind는 Approval Node가 `WAITING_FOR_APPROVAL`을 만들기 때문에 `execute` 분기에 들어가지 않습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/streaming_concurrent_start_workflow.py
waiting=1
conflicts=7
events=plan | approval
```

`waiting=1`은 하나의 학습용 상태 전이만 기록됐다는 뜻입니다. 실제 배포나 외부 시스템 변경이 수행된 것은 아닙니다.

## 9. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `run_id already exists` | 먼저 도착한 시작이 run을 생성했습니다. | 충돌로 처리하고 최신 Checkpoint를 읽습니다. |
| `checkpoint not found` | 시작 generator를 소비하지 않았거나 잘못된 run ID를 사용했습니다. | `stream_new()` 결과를 끝까지 소비하고 run ID를 확인합니다. |
| `execute` update가 나타남 | 위험 작업 대신 안전 ActionKind를 사용했거나 계약이 훼손됐습니다. | `ActionKind.DEPLOY`, 최종 상태, 이벤트 순서를 점검합니다. |

## 10. 응용 실습

1. 같은 run ID로 서로 다른 위험 task를 동시에 보내도 첫 task만 Checkpoint에 남는지 확인합니다.
2. 안전 ActionKind에 `stream_new()`를 적용해 하나의 완료 스트림만 기록되는지 검증합니다.
3. `JsonFileCheckpointer`의 같은 프로세스·정규화된 경로 Lock 범위에서 동일 계약을 테스트합니다.

## 11. 실무 적용

이 원자적 생성 보장은 `MemoryCheckpointer`의 프로세스 내 Lock 및 `JsonFileCheckpointer`의 같은 프로세스·정규화된 동일 로컬 경로 Lock 범위에 한정됩니다. 여러 프로세스, 여러 호스트, 네트워크 파일 시스템에서는 트랜잭션 저장소 또는 분산 compare-and-swap이 필요합니다.

또한 run ID 충돌 방지는 사용자의 신원·권한, 승인 만료, 외부 작업의 멱등성, 실제 실행 권한을 제공하지 않습니다. 실제 위험 작업에는 별도 인증·인가·재인증·감사 보관·멱등성 키가 필요합니다.

## 12. 과제

- **기본:** `save()` 대신 `save_if_absent()`가 필요한 경쟁 조건을 설명합니다.
- **응용:** conflict 요청의 update 수가 0인 회귀 테스트를 작성합니다.
- **심화:** 다중 프로세스에서 run 생성과 승인 결정을 보장할 versioned transaction 스키마를 설계합니다.

## 13. 완료 체크리스트

- [ ] 동시 위험 Streaming 시작 8개 중 하나만 성공했다.
- [ ] 성공한 요청의 update 순서가 `plan | approval`이다.
- [ ] 나머지 7개 요청이 update 없이 충돌했다.
- [ ] 최종 Checkpoint가 `WAITING_FOR_APPROVAL`이고 `execute`와 결과가 없다.
- [ ] 외부 API·실제 위험 작업 없이 예제와 테스트를 통과시켰다.

## 14. 핵심 정리

Streaming 시작도 run ID를 생성하는 상태 전이입니다. 첫 plan Checkpoint를 원자적으로 만들고 저장 뒤에만 update를 내보내면 동시 재전송은 하나의 위험 승인 대기만 만듭니다. 이 로컬 계약은 실제 위험 작업의 인증·분산 트랜잭션·멱등성을 대체하지 않으며, 위험 ActionKind에는 계속 엄격한 별도 Boolean 승인이 필요합니다.
