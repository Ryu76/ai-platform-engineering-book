# 상태 업데이트 Streaming과 승인 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- 상태 Streaming과 LLM 토큰 Streaming의 차이를 설명한다.
- 완료된 Node 전이를 순서와 상태가 있는 `StreamUpdate`로 관찰한다.
- 위험 작업의 초기 스트림에 `execute` 업데이트가 없음을 검증한다.
- 명시적인 사람 승인 뒤에만 재개 스트림이 `execute`로 이동함을 확인한다.

## 2. 왜 필요한가

장시간 Workflow에서는 최종 결과만 보면 현재 어디에서 멈췄는지 알기 어렵습니다. Node별 상태 업데이트를 보면 계획, 승인 대기, 완료를 구분해 UI나 로그에 표시할 수 있습니다.

그러나 Streaming은 실행 권한이 아닙니다. `DEPLOY`, `DELETE`, `SEND`처럼 위험한 작업에서 `execute`가 곧 나타난다면 사용자는 승인 전 실제 실행으로 오해할 수 있습니다. 따라서 상태를 빨리 보여 주는 것과 실행을 허가하는 것을 분리해야 합니다.

## 3. 핵심 개념

- **상태 Streaming**: 완료된 Node 전이 후의 `WorkflowState` 스냅샷을 순서대로 전달합니다.
- **StreamUpdate**: `run_id`, 최신 불변 State, 그 전이를 만든 마지막 감사 이벤트를 묶은 값입니다.
- **Checkpoint-before-yield**: 업데이트를 구독자에게 전달하기 전에 State를 Checkpointer에 저장하는 규칙입니다.
- **approval interrupt**: 위험 작업의 초기 스트림을 `WAITING_FOR_APPROVAL`에서 끝내는 안전한 중단점입니다.
- **재개 스트림**: `resume_stream(..., approved=True)`가 승인 이벤트를 기록한 뒤에만 `execute` 업데이트를 추가합니다.

이 구현은 네트워크 스트림, 모델 토큰, 시간 지연을 사용하지 않습니다. 같은 입력은 같은 이벤트 순서와 상태를 만듭니다.

> [!WARNING]
> 스트림에 표시된 계획이나 결과는 실제 외부 작업의 진행률이 아닙니다. 이 장의 `execute` Node는 문자열 결과만 만드는 오프라인 시뮬레이션입니다. 위험 ActionKind는 사람의 명시적 승인 전까지 `execute` 업데이트를 만들지 않으며, 실제 삭제·배포·전송도 수행하지 않습니다.

## 4. 동작 구조

```text
safe READ
START → plan (PLANNED) → approval (READY) → execute (COMPLETED) → END
           │                   │                    │
           └──── StreamUpdate, Checkpoint 저장 ──────┘

risky DEPLOY
START → plan (PLANNED) → approval (WAITING_FOR_APPROVAL)
                                      │
                              초기 스트림 종료
                                      │ 사람 승인
                                      ▼
                   approval (READY) → execute (COMPLETED) → END
                         재개 스트림에서만 출력
```

각 `StreamUpdate.event.sequence`은 State의 이벤트 수와 함께 1부터 증가합니다. 구독자는 출력 순서가 아닌 이 순번과 `state.status`를 함께 검사해야 합니다.

## 5. 실습 환경

다음 파일을 사용합니다.

- `src/ai_platform/graph/state.py`
- `src/ai_platform/graph/workflow.py`
- `examples/volume09/streaming_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

패키지 설치 뒤에도 이 예제는 API 키, 네트워크, 데이터베이스, 실제 배포를 요구하지 않습니다.

## 6. 단계별 실습

### 6.1 위험 작업의 초기 상태 스트림 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run python examples/volume09/streaming_workflow.py
```

초기 출력에는 `plan`, `approval`만 나타나며 Checkpoint는 `waiting_for_approval`입니다. `execute`가 없다는 사실이 승인 경계의 핵심 확인 항목입니다.

### 6.2 승인 뒤 재개 스트림 읽기

예제는 교육 목적으로 코드 안에서 `approved=True`를 전달합니다. 실제 제품에서는 인증된 승인자와 대상·영향 범위·만료 정책을 별도로 검증해야 합니다.

```python
from ai_platform.graph import ActionKind, StreamingWorkflow

workflow = StreamingWorkflow()
initial_updates = list(
    workflow.stream(
        run_id="streaming-demo-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
)
assert [update.event.node for update in initial_updates] == ["plan", "approval"]

approved_updates = list(
    workflow.resume_stream(run_id="streaming-demo-001", approved=True)
)
assert [update.event.node for update in approved_updates] == ["approval", "execute"]
```

### 6.3 계약 테스트와 정적 검사 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

테스트는 안전 작업의 고정 순서, 위험 작업의 승인 전 `execute` 부재, 승인 뒤 재개, 거절 뒤 `execute` 부재를 검증합니다.

## 7. 코드 설명

`StreamingWorkflow.stream()`은 `plan_node()`와 `approval_node()` 뒤에 각각 `_save_and_update()`를 호출합니다. 이 함수는 Checkpointer에 먼저 저장한 다음 State의 마지막 이벤트를 `StreamUpdate`로 반환합니다.

```python
state = approval_node(state)
yield self._save_and_update(run_id=run_id, state=state)
if state.status is WorkflowStatus.READY:
    state = execute_node(state)
    yield self._save_and_update(run_id=run_id, state=state)
```

위 조건은 안전 작업만 같은 스트림에서 `execute`로 보냅니다. 위험 작업은 `WAITING_FOR_APPROVAL`이므로 함수가 끝납니다. `resume_stream()`은 Checkpoint를 읽은 뒤 `resolve_approval_node()`를 호출합니다. 거절이면 `REJECTED` 업데이트 하나만, 승인이라면 `READY`와 `COMPLETED` 업데이트를 차례로 만듭니다.

## 8. 정상 실행 결과

예제의 출력은 다음과 같은 순서를 가집니다.

```text
initial_stream
1:plan status=planned detail='학습용 배포를 준비한다' 작업에 대한 오프라인 계획을 만들었습니다.
2:approval status=waiting_for_approval detail=deploy 작업은 사람 승인을 기다립니다.
checkpoint=waiting_for_approval
approved_resume_stream
3:approval status=ready detail=사람 승인을 받았습니다. 실행 시뮬레이션으로 이동합니다.
4:execute status=completed detail=외부 시스템을 변경하지 않는 결정론적 실행 결과를 만들었습니다.
```

초기 스트림과 Checkpoint에 `execute`가 없는 것이 정상입니다. 승인 재개 뒤에만 sequence 4의 `execute`가 나타납니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `checkpoint not found` | 스트림을 끝까지 소비하지 않았거나 run ID가 다릅니다. | `list(workflow.stream(...))`처럼 초기 스트림을 소비하고 같은 run ID를 사용합니다. |
| `waiting state` 오류 | 완료·거절된 실행을 다시 재개하려 했습니다. | `checkpoint()`로 상태를 확인하고 대기 상태에만 승인 결정을 적용합니다. |
| 초기 스트림에 `execute`가 있음 | 위험 ActionKind가 아닌 입력을 사용했거나 안전 경계가 변경됐습니다. | `DEPLOY`, `DELETE`, `SEND` 입력과 이벤트 순서 계약 테스트를 확인합니다. |
| 순번이 기대와 다름 | 여러 Node의 업데이트를 한 목록으로 합치지 않았습니다. | 각 Update의 `event.sequence`과 해당 `state.events`를 함께 검사합니다. |
| 실제 진행률처럼 보임 | 상태 Streaming을 외부 작업 완료 신호로 해석했습니다. | 이 예제는 오프라인 시뮬레이션임을 UI와 로그에 표시하고 실제 작업은 별도 관측 계약을 설계합니다. |

## 10. 응용 실습

1. 안전 `READ` 작업의 세 업데이트에서 `state.status`가 `planned`, `ready`, `completed`인지 테스트합니다.
2. JSON 파일 Checkpointer를 `StreamingWorkflow`에 주입하고, 승인 대기 뒤 새 인스턴스에서 `resume_stream()`하는 오프라인 테스트를 작성합니다.
3. StreamUpdate를 JSON으로 표시하는 순수 변환 함수를 작성하되, task·event detail에 비밀값을 넣지 않는 입력 검증을 추가합니다.

## 11. 실무 적용

운영 Streaming은 연결 해제, 재연결, 중복 전달, 이벤트 보존, 순서 보장 범위, 테넌트 분리, 인증·인가, 감사 로그 무결성을 설계해야 합니다. 구독자가 업데이트를 받았다는 사실은 위험 작업의 승인 기록이 아닙니다.

위험 실행에는 승인자 신원, 정책 버전, 정확한 대상, 영향 범위, 만료 시간, idempotency key를 검증해야 합니다. 상태 이벤트에 API 키나 개인정보를 넣지 말고, 출력 채널별 마스킹과 접근 제어를 적용해야 합니다.

## 12. 과제

- **기본:** 상태 Streaming과 토큰 Streaming의 차이를 두 가지 이상 설명합니다.
- **응용:** 위험 작업의 초기 스트림에 `execute`가 없음을 확인하는 테스트를 추가합니다.
- **심화:** 재연결 가능한 운영 이벤트 인터페이스의 event ID, 보존 기간, 중복 제거, 승인 감사 경계를 설계합니다. 실제 서버나 외부 API는 사용하지 않습니다.

## 13. 완료 체크리스트

- [ ] `StreamUpdate`가 State와 마지막 이벤트를 함께 전달하는 이유를 설명할 수 있다.
- [ ] 안전 작업의 `plan → approval → execute` 상태 순서를 확인했다.
- [ ] 위험 작업의 초기 스트림이 `waiting_for_approval`에서 멈춤을 확인했다.
- [ ] 초기 스트림에 `execute`가 없음을 테스트했다.
- [ ] 승인 뒤 재개 스트림에서만 `execute`가 나타남을 확인했다.
- [ ] 거절 뒤에는 `execute`가 나타나지 않음을 확인했다.
- [ ] 예제와 테스트가 API, 네트워크, 실제 위험 작업 없이 동작함을 확인했다.

## 14. 핵심 정리

상태 Streaming은 Workflow가 완료한 Node 전이를 관찰 가능하게 하지만 실행 권한을 주지 않습니다. 이 장의 `StreamingWorkflow`는 매 업데이트를 Checkpoint에 먼저 저장하고 고정된 순서로 내보냅니다. 위험 작업은 초기 스트림에서 승인 대기 상태로 끝나며, 명시적 사람 승인 뒤의 재개 스트림에서만 오프라인 `execute` 시뮬레이션에 도달합니다.
