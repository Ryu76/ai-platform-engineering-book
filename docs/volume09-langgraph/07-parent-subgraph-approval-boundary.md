# 부모 Workflow와 Subgraph의 승인 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- 재사용 가능한 Subgraph와 이를 호출하는 부모 Workflow의 책임을 구분한다.
- Planner → Developer → Reviewer 역할을 실행 권한 없이 Subgraph에 묶는다.
- Reviewer 통과와 사람 실행 승인이 서로 다른 결정임을 설명한다.
- 위험 작업이 Subgraph 완료 뒤에도 부모의 `WAITING_FOR_APPROVAL` interrupt에서 멈춤을 검증한다.

## 2. 왜 필요한가

큰 Workflow는 역할별 단계를 재사용하려고 Subgraph로 나눕니다. 그러나 Subgraph가 검토를 끝냈다는 이유만으로 상위 Workflow의 위험 작업을 실행하면, 역할 분리와 승인 정책이 무너집니다.

이 참조 모델은 Subgraph가 산출물 검토까지만 담당하게 합니다. 부모 `SubgraphWorkflow`만 Approval Node와 Execute Node를 호출합니다. 따라서 `DEPLOY`, `DELETE`, `SEND`는 검토 통과 뒤에도 명시적인 사람 승인 없이는 실행 시뮬레이션으로 이동하지 않습니다.

## 3. 핵심 개념

- **Subgraph**: 부모가 호출하는 재사용 가능한 내부 Workflow 조각입니다.
- **부모 Workflow**: Subgraph의 결과를 소비하고 상위 정책과 END 경로를 결정합니다.
- **검토 통과**: 초안 품질에 관한 `ReviewDecision(approved=True)`입니다. 실행 권한이 아닙니다.
- **Approval interrupt**: 위험 ActionKind를 `WAITING_FOR_APPROVAL`에서 멈추는 부모의 사람 승인 경계입니다.
- **책임 분리**: Subgraph는 `plan`, `developer`, `reviewer`만 기록하고 `approval`, `execute`는 부모가 기록합니다.

모든 Node는 외부 API, 모델 호출, 파일 변경, 배포, 전송 없이 불변 State만 전이합니다.

> [!WARNING]
> 이 장의 `DEPLOY`는 학습용 문자열 결과를 만드는 오프라인 시뮬레이션입니다. Reviewer 통과, 예제의 `approved=True`, 또는 Subgraph 완료는 실제 배포를 허가하지 않습니다. 위험 ActionKind는 사람의 명시적 승인 전까지 `execute` Node에 도달하지 않습니다.

## 4. 동작 구조

```text
risky DEPLOY
START
  │
  ▼
PlannerDeveloperReviewerSubgraph
  plan → developer → reviewer (검토 통과)
  │
  ▼
부모 SubgraphWorkflow
  approval (WAITING_FOR_APPROVAL) ── 사람 거절 ──► REJECTED → END
  │
  └── 명시적 사람 승인 ──► approval (READY) → execute (COMPLETED) → END

Subgraph reviewer 거절
  plan → developer → reviewer (REVIEW_REJECTED) → END
  └── 부모 approval·execute는 호출하지 않음
```

`PlannerDeveloperReviewerSubgraph.invoke()`는 `PENDING` State를 받아 역할 이벤트를 추가합니다. `reviewer`가 통과하면 State는 `PLANNED`를 유지합니다. 이 상태를 받은 부모만 `approval_node()`를 적용합니다.

## 5. 실습 환경

다음 파일을 사용합니다.

- `src/ai_platform/graph/workflow.py`
- `src/ai_platform/graph/nodes.py`
- `examples/volume09/subgraph_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

이 예제는 API 키, 네트워크, 데이터베이스, 실제 위험 작업을 요구하지 않습니다.

## 6. 단계별 실습

### 6.1 위험 작업을 Subgraph로 검토

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run python examples/volume09/subgraph_workflow.py
```

첫 출력은 `plan | developer | reviewer | approval`에서 끝나고 status는 `waiting_for_approval`입니다. Subgraph의 검토가 통과했어도 `execute`가 없는 것이 핵심입니다.

### 6.2 승인 뒤 부모 Workflow 재개

```python
from ai_platform.graph import ActionKind, ReviewDecision, SubgraphWorkflow

workflow = SubgraphWorkflow()
waiting = workflow.invoke(
    run_id="subgraph-demo-001",
    task="학습용 배포 초안을 검토한다",
    action=ActionKind.DEPLOY,
    review_decision=ReviewDecision(approved=True, feedback="검토 기준을 충족합니다."),
)
assert waiting.status.value == "waiting_for_approval"
assert [event.node for event in waiting.events] == [
    "plan", "developer", "reviewer", "approval"
]

completed = workflow.resume(run_id="subgraph-demo-001", approved=True)
assert completed.status.value == "completed"
assert completed.events[-1].node == "execute"
```

실제 제품의 승인에는 인증된 승인자, 정확한 대상, 영향 범위, 정책 버전과 만료 시간이 필요합니다. 이 예제의 Boolean 값은 그 보안 계약을 대체하지 않습니다.

### 6.3 계약 테스트와 정적 검사 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

테스트는 Subgraph 통과 뒤 위험 작업이 부모 Approval Node에서 대기하는지, 승인 전 `execute`가 없는지, Reviewer 거절이 부모 approval과 execute를 건너뛰는지 검증합니다.

## 7. 코드 설명

Subgraph는 실행 권한 없이 역할 전이만 수행합니다.

```python
class PlannerDeveloperReviewerSubgraph:
    def invoke(self, *, state: WorkflowState, review_decision: ReviewDecision) -> WorkflowState:
        state = plan_node(state)
        state = developer_node(state)
        return reviewer_node(state, decision=review_decision)
```

부모는 Subgraph 결과가 `PLANNED`일 때만 승인 정책을 적용합니다.

```python
state = self._subgraph.invoke(state=state, review_decision=review_decision)
if state.status is WorkflowStatus.PLANNED:
    state = self._continue_after_subgraph(state)
```

Reviewer가 거절하면 상태는 `REVIEW_REJECTED`입니다. 조건문이 거짓이므로 부모는 `approval_node()`와 `execute_node()`를 호출하지 않습니다. 통과해도 위험 ActionKind의 `approval_node()`는 `WAITING_FOR_APPROVAL`을 기록해 중단합니다.

## 8. 정상 실행 결과

```text
Subgraph 검토 통과 후: status=waiting_for_approval
events=plan | developer | reviewer | approval
부모 Workflow의 사람 실행 승인 후: status=completed
events=plan | developer | reviewer | approval | approval | execute
```

두 번째 `approval` 이벤트는 Subgraph가 아니라 부모가 재개 시 기록한 명시적 사람 승인입니다. `execute`는 그 이벤트 뒤에만 나타납니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `plan_node requires a pending state` | 이미 시작된 State를 Subgraph 입력으로 전달했습니다. | 부모가 새 `WorkflowState.start()`를 만들고 한 번만 Subgraph를 호출하게 합니다. |
| `waiting state` 오류 | 검토 거절·완료된 run ID를 `resume()`하려 했습니다. | `checkpoint()`로 `waiting_for_approval`인지 확인한 뒤에만 재개합니다. |
| 검토 통과 뒤 `execute`가 바로 나타남 | 부모 승인 경계가 빠졌거나 ActionKind가 안전 작업입니다. | 위험 `DEPLOY`·`DELETE`·`SEND`와 Approval Node 이벤트 계약을 확인합니다. |
| Reviewer 거절 뒤 approval이 있음 | 부모가 `REVIEW_REJECTED`를 END 상태로 처리하지 않았습니다. | Subgraph 뒤의 조건을 `PLANNED` 상태에만 제한합니다. |
| 실제 배포처럼 보임 | 시뮬레이션 결과를 운영 실행으로 해석했습니다. | UI·로그에 오프라인 시뮬레이션임을 표시하고 실제 실행은 별도 승인·관측 계약으로 설계합니다. |

## 10. 응용 실습

1. 안전 `READ` ActionKind가 Subgraph 통과 뒤 `plan → developer → reviewer → approval → execute`로 완료하는 테스트를 작성합니다.
2. `JsonFileCheckpointer`를 `SubgraphWorkflow`에 주입하고, 새 인스턴스에서도 승인 대기가 유지되는 오프라인 테스트를 작성합니다.
3. 독립된 Research Subgraph를 설계하되, 부모가 위험 실행 승인 정책을 단독으로 적용하도록 이벤트와 State 계약을 작성합니다.

## 11. 실무 적용

운영 Subgraph는 입력·출력 스키마, 부모와 자식의 상태 격리, 오류 전파, retry 책임, 관측 ID, 권한 전파 범위를 명시해야 합니다. 자식의 모델 평가나 정책 추천을 실행 권한으로 취급하지 않아야 합니다.

위험 실행은 부모의 단일 정책 결정 지점에서 인증·인가, 승인자 역할, 대상·영향 범위, 정책 버전, 만료, idempotency key와 감사 로그를 검증해야 합니다. State와 이벤트에 API 키, 토큰, 개인정보를 기록하지 않습니다.

## 12. 과제

- **기본:** Subgraph와 부모 Workflow의 책임을 각각 두 가지 이상 설명합니다.
- **응용:** Reviewer 거절 시 부모 Approval Node가 호출되지 않는 테스트를 추가합니다.
- **심화:** 여러 Subgraph가 공유하는 승인 정책을 중앙 부모에 두는 상태 스키마와 감사 이벤트 계약을 설계합니다. 외부 서버나 API는 사용하지 않습니다.

## 13. 완료 체크리스트

- [ ] Subgraph가 `plan`, `developer`, `reviewer`만 담당함을 설명할 수 있다.
- [ ] Reviewer 통과가 사람 실행 승인이 아님을 확인했다.
- [ ] 위험 ActionKind가 Subgraph 통과 뒤 `waiting_for_approval`에서 멈춤을 확인했다.
- [ ] 승인 전 이벤트에 `execute`가 없음을 테스트했다.
- [ ] 명시적 승인 뒤에만 `execute`가 나타남을 확인했다.
- [ ] Reviewer 거절이 부모 `approval`과 `execute`를 건너뜀을 테스트했다.
- [ ] 예제와 테스트가 API, 네트워크, 실제 위험 작업 없이 동작함을 확인했다.

## 14. 핵심 정리

Subgraph는 재사용성을 위해 역할별 전이를 묶지만, 부모의 위험 작업 승인 정책을 우회해서는 안 됩니다. 이 장의 `PlannerDeveloperReviewerSubgraph`는 검토까지만 수행하고, `SubgraphWorkflow`는 검토 통과 뒤에도 위험 작업을 사람 승인 interrupt에서 멈춥니다. 명시적 승인 후에만 부모가 오프라인 `execute` 시뮬레이션으로 이동합니다.
