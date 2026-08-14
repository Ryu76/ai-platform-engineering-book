# 동시 Streaming 거절과 단일 종료 기록

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 동시 거절 재전송도 하나의 승인 대기를 한 번만 소비해야 함을 설명한다.
- 거절 전이를 compare-and-swap(CAS)로 기록하고 update보다 먼저 저장한다.
- 동시 `approved=False` 요청 8개 중 하나만 `REJECTED`와 `approval` update를 기록하는지 검증한다.
- 거절된 위험 작업이 `execute` update나 결과를 만들지 않음을 확인한다.

## 2. 왜 필요한가

승인 화면의 취소·거절 버튼도 중복 전송될 수 있습니다. 단순한 `load → 전이 → save`라면 여러 consumer가 같은 `WAITING_FOR_APPROVAL` Checkpoint를 읽고 각자 거절 update를 발행하거나 마지막 저장이 감사 기록을 덮어쓸 수 있습니다. 거절은 외부 작업을 실행하지 않더라도 승인 의도의 단일 소비와 감사 순서가 필요한 종료 결정입니다.

`StreamingWorkflow.resume_stream()`은 `approved=False`에도 승인 resolution 후보를 `save_if_current()`으로 먼저 저장합니다. 첫 요청만 `REJECTED` Checkpoint와 하나의 `approval` update를 반환합니다. 후발 요청은 CAS 실패 또는 이미 종료된 상태 때문에 `WorkflowRunConflictError`로 끝나며 update를 반환하지 않습니다.

> [!WARNING]
> 이 예제는 프로세스 내 메모리 Checkpointer와 고정 입력만 사용합니다. 외부 API, 네트워크, 실제 배포·삭제·전송, 비밀값을 사용하지 않습니다. `DEPLOY`, `DELETE`, `SEND`은 엄격한 별도 Boolean 승인 없이는 계속 `WAITING_FOR_APPROVAL`에 머물며, `approved=False`는 실행 권한이 아닙니다.

## 3. 핵심 개념

- **거절 결정:** 사람의 명시적 `False`가 승인 대기를 `REJECTED` 종료 상태로 전이하는 것입니다.
- **CAS:** 현재 Checkpoint가 읽은 기대 State와 정확히 같을 때만 후보 종료 State를 저장하는 compare-and-swap입니다.
- **checkpoint-before-yield:** consumer가 `approval` update를 보기 전에 `REJECTED` State를 저장하는 규칙입니다.
- **충돌:** 먼저 기록된 종료 결정 때문에 후발 요청이 상태·감사 이벤트·update를 바꾸지 못한 결과입니다.

## 4. 동작 구조

```text
WAITING_FOR_APPROVAL Checkpoint
        |
        +-- 거절 재전송 A -- CAS 성공 --> REJECTED 저장 --> approval update
        |
        +-- 거절 재전송 B..H -- CAS 실패 또는 이미 종료됨 --> conflict, update 없음

REJECTED --> END (execute 없음)
```

## 5. 실습 환경

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/streaming_concurrent_rejection_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제의 ThreadPool은 동일 Python 프로세스에서 8개의 엄격한 Boolean 거절 재전송을 동시에 시작합니다.

## 6. 단계별 실습

### 6.1 위험 작업을 승인 대기까지 스트리밍한다

```python
list(
    workflow.stream(
        run_id="streaming-concurrent-rejection-demo-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
)
```

마지막 Checkpoint는 `WAITING_FOR_APPROVAL`이며 `execute` event와 결과가 없습니다.

### 6.2 별도의 거절 요청을 동시에 보낸다

```python
updates = tuple(
    workflow.resume_stream(
        run_id="streaming-concurrent-rejection-demo-001",
        approved=False,
    )
)
```

각 요청은 같은 대기 State를 읽을 수 있지만, `save_if_current()`에 성공한 하나만 `REJECTED` State를 저장하고 하나의 `approval` update를 반환합니다.

### 6.3 최종 감사 기록에서 실행이 없음을 확인한다

```python
terminal = checkpointer.load(run_id="streaming-concurrent-rejection-demo-001")
assert terminal.status is WorkflowStatus.REJECTED
assert [event.node for event in terminal.events] == ["plan", "approval", "approval"]
assert terminal.result is None
```

`execute`는 거절 결정 뒤의 가능한 경로가 아닙니다.

## 7. 코드 설명

`resume_stream()`은 먼저 `resolve_approval_node(expected_state, approved=False)`로 후보 `REJECTED` State를 만듭니다. 이 State는 `READY`가 아니므로 execute 분기로 들어가지 않습니다. CAS 저장이 성공한 뒤에만 마지막 `approval` event를 담은 `StreamUpdate`를 yield합니다.

이미 종료된 Checkpoint에서 resolution Node가 내는 waiting-state 오류는 `WorkflowRunConflictError`로 정규화됩니다. 따라서 caller는 CAS 실패와 늦은 재전송을 모두 충돌로 처리하고, 자동 재시도로 거절 결정을 덮어쓰지 않아야 합니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/streaming_concurrent_rejection_workflow.py
rejected=1
conflicts=7
events=plan | approval | approval
```

`rejected=1`은 하나의 종료 결정을 저장했다는 뜻이며 실제 배포·삭제·전송이 수행된 것은 아닙니다.

## 9. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `workflow approval is no longer pending` | 먼저 도착한 요청이 대기를 종료했습니다. | 충돌로 처리하고 최신 Checkpoint를 조회합니다. |
| `checkpoint changed before approval was recorded` | 읽은 State와 CAS 시점의 State가 달라졌습니다. | 거절을 재시도해 덮어쓰지 말고 승인 의도와 최신 상태를 다시 확인합니다. |
| `execute` update가 나타남 | 테스트 대상이 거절 경로가 아니거나 계약이 훼손됐습니다. | `approved=False`, 최종 상태, 감사 이벤트 순서를 점검합니다. |

## 10. 응용 실습

1. 승인·거절 요청을 섞어 하나의 종료 상태만 남는지 확인합니다.
2. JSON Checkpointer를 주입해 같은 프로세스와 정규화된 로컬 경로에서 이 거절 CAS 계약을 검증합니다.
3. consumer가 conflict에서 받은 update 수가 0인지 명시하는 회귀 테스트를 작성합니다.

## 11. 실무 적용

이 CAS 보장은 `MemoryCheckpointer`의 프로세스 내 Lock 및 `JsonFileCheckpointer`의 같은 프로세스·정규화된 동일 로컬 경로 Lock 범위에 한정됩니다. 여러 프로세스, 여러 호스트, 네트워크 파일 시스템에서는 트랜잭션 저장소나 분산 compare-and-swap이 필요합니다.

CAS는 사람의 신원, 권한, 재인증, 승인 만료, 실제 외부 작업의 멱등성을 제공하지 않습니다. 실제 위험 작업은 별도의 인증·인가·권한 분리·감사 보관·멱등성 키를 설계해야 합니다.

## 12. 과제

- **기본:** 거절 경로에도 CAS와 checkpoint-before-yield가 필요한 이유를 설명합니다.
- **응용:** 늦은 거절 재전송이 update를 만들지 않는 테스트를 작성합니다.
- **심화:** 승인·거절을 하나의 versioned decision record로 모델링하는 트랜잭션 스키마를 설계합니다.

## 13. 완료 체크리스트

- [ ] 위험 작업이 초기 Stream에서 `WAITING_FOR_APPROVAL`에 멈췄다.
- [ ] 동시 거절 재전송 8개 중 하나만 `REJECTED`를 기록했다.
- [ ] 나머지 7개가 update 없이 충돌했다.
- [ ] 최종 감사 이벤트가 `plan | approval | approval`이고 `execute`가 없는지 확인했다.
- [ ] 외부 API·실제 위험 작업 없이 예제와 테스트를 통과시켰다.

## 14. 핵심 정리

거절도 승인 대기를 소비하는 종료 전이입니다. 거절 후보를 CAS로 저장한 뒤에만 update를 내보내면 하나의 대기 Checkpoint는 하나의 거절 감사 기록만 만듭니다. 이 로컬 계약은 실제 위험 작업의 인증·분산 멱등성·트랜잭션을 대체하지 않으며, 위험 ActionKind에는 계속 엄격한 별도 Boolean 승인이 필요합니다.
