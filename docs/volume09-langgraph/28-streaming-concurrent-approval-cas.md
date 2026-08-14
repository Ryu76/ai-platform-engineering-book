# 동시 Streaming 승인과 단일 오프라인 실행 기록

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- Streaming 재개 요청이 같은 승인 대기를 동시에 읽을 수 있음을 설명한다.
- 각 상태 전이를 compare-and-swap(CAS)로 저장해야 하는 이유를 설명한다.
- 동시 승인 중 정확히 하나만 `approval`, `execute` update를 내보내는지 검증한다.
- 위험 작업이 엄격한 Boolean 승인 전에는 계속 중단됨을 확인한다.

## 2. 왜 필요한가

Stream consumer가 여러 승인 재전송을 보낼 수 있습니다. 단순한 `load → 전이 → save`라면 둘 이상의 consumer가 같은 `WAITING_FOR_APPROVAL` Checkpoint를 읽고 각자 `execute` update를 내보낼 수 있습니다. 이 참조 모델의 `execute`는 외부 부작용 없는 시뮬레이션이지만, 실제 위험 실행으로 확장할 때는 중복 실행의 안전 문제가 됩니다.

`StreamingWorkflow.resume_stream()`은 승인 전이와 실행 전이를 각각 `save_if_current()`로 저장합니다. 첫 요청만 저장에 성공해 update를 yield하고, 나머지는 어떤 update도 yield하기 전에 `WorkflowRunConflictError`로 끝납니다.

> [!WARNING]
> 이 예제는 프로세스 내 메모리 Checkpointer와 고정 입력만 사용합니다. 외부 API, 네트워크, 실제 배포·삭제·전송, 비밀값을 사용하지 않습니다. `DEPLOY`, `DELETE`, `SEND`은 계속 별도의 엄격한 Boolean 승인이 있어야만 `execute` Node로 갈 수 있습니다.

## 3. 핵심 개념

- **Streaming 재개:** 중단된 Checkpoint에 사람 결정을 적용하고 저장된 Node update를 순서대로 전달하는 과정입니다.
- **CAS:** 현재 Checkpoint가 읽었던 기대 State와 정확히 같을 때만 새 State를 기록하는 compare-and-swap입니다.
- **충돌:** 다른 요청이 먼저 승인 대기를 소비했음을 뜻하며, 후발 요청은 상태나 감사 로그를 바꾸지 않습니다.
- **checkpoint-before-yield:** consumer에 update를 보이기 전에 해당 State를 Checkpointer에 기록하는 규칙입니다.

## 4. 동작 구조

```text
WAITING_FOR_APPROVAL Checkpoint
        |
        +-- 승인 재전송 A -- CAS 성공 --> READY 저장 --> approval update
        |                                      |
        |                                      +--> CAS 성공 --> COMPLETED 저장 --> execute update
        |
        +-- 승인 재전송 B..H -- CAS 실패 또는 이미 종료됨 --> conflict, update 없음
```

## 5. 실습 환경

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/streaming_concurrent_approval_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제의 ThreadPool은 같은 프로세스에서 8개 승인 재전송을 동시에 시작합니다.

## 6. 단계별 실습

### 6.1 위험 작업을 승인 대기까지 스트리밍한다

```python
list(
    workflow.stream(
        run_id="streaming-concurrent-approval-demo-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
)
```

이 단계의 마지막 Checkpoint는 `WAITING_FOR_APPROVAL`이고 `execute` event가 없습니다.

### 6.2 별도의 엄격한 Boolean 승인 요청을 동시에 보낸다

```python
updates = tuple(
    workflow.resume_stream(
        run_id="streaming-concurrent-approval-demo-001",
        approved=True,
    )
)
```

각 요청은 먼저 `expected_state`를 읽고 `READY` 상태를 후보로 만듭니다. `save_if_current()`에 성공한 요청만 `approval` update를 반환합니다.

### 6.3 실행 update도 별도 CAS로 저장한다

```python
if state.status is WorkflowStatus.READY:
    expected_state = state
    state = execute_node(state)
    if not checkpointer.save_if_current(
        run_id=run_id,
        expected_state=expected_state,
        state=state,
    ):
        raise WorkflowRunConflictError("workflow checkpoint changed")
```

따라서 첫 승인 저장 뒤 Checkpoint가 바뀌면, stale consumer는 `execute` update도 내보내지 못합니다.

## 7. 코드 설명

`resume_stream()`은 승인 resolution 실패가 이미 소비된 대기를 뜻할 때도 `WorkflowRunConflictError`로 변환합니다. CAS 실패와 이미 종료된 Checkpoint를 caller가 같은 재전송 충돌로 다룰 수 있게 하기 위해서입니다.

성공한 consumer는 `approval → execute` 순서의 두 update를 받습니다. 거절 요청은 `REJECTED` Checkpoint와 `approval` update만 남기며 `execute`는 만들지 않습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/streaming_concurrent_approval_workflow.py
completed=1
conflicts=7
events=plan | approval | approval | execute
```

`completed=1`은 하나의 오프라인 시뮬레이션만 기록되었음을 뜻합니다. 실제 배포가 수행된 것은 아닙니다.

## 9. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `workflow approval is no longer pending` | 먼저 도착한 재전송이 대기를 소비했습니다. | 충돌 응답을 성공으로 재해석하지 말고 최신 Checkpoint를 조회합니다. |
| `checkpoint changed before approval was recorded` | 읽은 State와 CAS 시점의 State가 달라졌습니다. | 자동 재시도 전에 사람 승인 의도와 최신 상태를 다시 확인합니다. |
| `execute` update가 없음 | 거절되었거나 approval 대기가 아직 해결되지 않았습니다. | 명시적 `approved=True` 여부와 이벤트 순서를 점검합니다. |

## 10. 응용 실습

1. 같은 8개 요청을 모두 `approved=False`로 바꿔 하나의 `REJECTED`만 남는지 확인합니다.
2. 승인·거절 요청을 섞고 하나의 종료 상태만 기록되는 테스트를 작성합니다.
3. JSON Checkpointer를 주입해 같은 프로세스와 정규화된 경로에서 같은 계약을 검증합니다.

## 11. 실무 적용

이 CAS 보장은 `MemoryCheckpointer`의 프로세스 내 Lock 및 `JsonFileCheckpointer`의 같은 프로세스·정규화된 동일 로컬 경로 Lock 범위에 한정됩니다. 여러 프로세스, 여러 호스트, 네트워크 파일 시스템에서는 트랜잭션 저장소나 분산 compare-and-swap이 필요합니다.

CAS는 사람의 신원, 권한, 재인증, 승인 만료, 실제 외부 작업의 멱등성을 제공하지 않습니다. 실제 위험 작업은 이 Stream 계약과 별도로 인증·인가·권한 분리·감사 보관·멱등성 키를 설계해야 합니다.

## 12. 과제

- **기본:** 승인 update와 실행 update를 둘 다 CAS해야 하는 이유를 설명합니다.
- **응용:** conflict consumer가 어떤 update도 관찰하지 않는 회귀 테스트를 작성합니다.
- **심화:** 트랜잭션 DB의 version column으로 이 CAS 계약을 구현하는 방법을 설계합니다.

## 13. 완료 체크리스트

- [ ] 위험 작업이 초기 Stream에서 `WAITING_FOR_APPROVAL`에 멈췄다.
- [ ] 동시 승인 재전송 8개 중 하나만 완료했다.
- [ ] 나머지 7개가 update를 내보내지 않고 충돌했다.
- [ ] 최종 감사 이벤트가 `plan | approval | approval | execute`인지 확인했다.
- [ ] 외부 API·실제 위험 작업 없이 예제와 테스트를 통과시켰다.

## 14. 핵심 정리

Streaming update도 저장된 상태 전이입니다. 동시 재개에서 승인과 실행 전이를 각각 CAS로 기록하면, 하나의 대기 Checkpoint는 하나의 결정과 하나의 오프라인 실행 update만 만듭니다. 이 로컬 계약은 실제 위험 작업의 인증·분산 멱등성·트랜잭션을 대체하지 않으며, 위험 ActionKind에는 계속 엄격한 별도 Boolean 승인이 필요합니다.
