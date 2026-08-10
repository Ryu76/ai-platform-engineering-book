# Planner-Developer-Reviewer Workflow와 검토·실행 승인 분리

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Planner, Developer, Reviewer 역할을 상태 전이로 분리한다.
- Reviewer의 품질 판정과 위험 작업의 사람 실행 승인을 구분한다.
- Reviewer 거절이 `approval`, `execute`를 거치지 않고 종료되는 이유를 설명한다.
- 같은 입력과 검토 판정에서 같은 이벤트 순서가 나오는 오프라인 테스트를 실행한다.

## 2. 왜 필요한가

한 Agent가 계획·구현·검토·실행 판단을 모두 하면 어떤 단계에서 문제가 발견됐는지 알기 어렵고, 코드 검토 통과가 배포 권한으로 잘못 해석될 수 있습니다. 역할을 Node로 분리하면 검토 거절을 실행 전에 끝낼 수 있고, 위험 작업에는 별도의 사람 승인을 계속 적용할 수 있습니다.

이 장의 Reviewer는 네트워크나 LLM을 호출하지 않습니다. 호출자가 전달한 불변 `ReviewDecision`만 사용합니다. `approved=True`는 학습용 초안의 검토 통과일 뿐 `DEPLOY`, `DELETE`, `SEND`의 실행 권한이 아닙니다.

## 3. 핵심 개념

- **Planner Node**: 작업의 오프라인 계획을 만들고 감사 이벤트를 남깁니다.
- **Developer Node**: 계획을 바탕으로 실제 파일을 수정하지 않는 구현 초안을 준비합니다.
- **Reviewer Node**: `ReviewDecision`의 통과·거절과 근거를 기록합니다.
- **ReviewDecision**: `approved`, 빈 값이 아닌 `feedback`, `source`를 가진 결정론적 검토 입력입니다.
- **검토 거절 END**: `REVIEW_REJECTED`는 품질 기준 미충족으로 끝난 상태이며 실행 승인 거절과 다릅니다.
- **실행 승인**: 위험 ActionKind에만 필요한 별도의 사람 결정입니다.

> [!WARNING]
> Reviewer가 통과시켜도 위험 작업은 자동 실행되지 않습니다. `WAITING_FOR_APPROVAL` Checkpoint에서 명시적으로 `resume(approved=True)`를 호출해야 하며, 그때도 `execute`는 외부 변경 없이 문자열만 만듭니다.

## 4. 동작 구조

```text
START
  │
  ▼
Planner ─► Developer ─► Reviewer
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
       review rejected         review approved
              │                     │
              ▼                     ▼
     REVIEW_REJECTED (END)      approval Conditional Edge
                              ┌─────────┴─────────┐
                              ▼                   ▼
                         read/transform    delete/deploy/send
                              │                   │
                              ▼                   ▼
                         execute → END   WAITING_FOR_APPROVAL
                                                   │ 사람 승인
                                                   ▼
                                              execute → END
```

`PlannerDeveloperReviewerWorkflow.invoke()`는 `plan → developer → reviewer`를 항상 같은 순서로 실행합니다. Reviewer 거절이면 이후 Node를 호출하지 않습니다. 통과한 경우에만 기존 `approval_node()` 정책을 적용하므로 검토와 권한 부여가 섞이지 않습니다.

## 5. 실습 환경

파일 위치는 다음과 같습니다.

- `src/ai_platform/graph/state.py`
- `src/ai_platform/graph/nodes.py`
- `src/ai_platform/graph/workflow.py`
- `examples/volume09/planner_developer_reviewer_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

이 실습은 `langgraph`, API 키, 네트워크, 실제 저장소 또는 배포 도구를 요구하지 않습니다. 프로젝트 설정이나 의존성을 바꾸지 않습니다.

## 6. 단계별 실습

### 6.1 검토 통과 뒤의 별도 실행 승인 확인

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run python examples/volume09/planner_developer_reviewer_workflow.py
```

첫 출력은 `waiting_for_approval`이며 `plan | developer | reviewer | approval`까지만 표시합니다. 두 번째 출력은 명시적 사람 승인 뒤 `completed`와 `execute`를 표시합니다. 예제는 배포 명령을 실행하지 않습니다.

### 6.2 Reviewer 거절 경로 확인

```python
from ai_platform.graph import ActionKind, PlannerDeveloperReviewerWorkflow, ReviewDecision

state = PlannerDeveloperReviewerWorkflow().invoke(
    run_id="review-rejected-001",
    task="학습용 변경 초안을 검토한다",
    action=ActionKind.DEPLOY,
    review_decision=ReviewDecision(approved=False, feedback="영향 범위가 빠졌습니다."),
)
assert state.status == "review_rejected"
assert [event.node for event in state.events] == ["plan", "developer", "reviewer"]
```

거절 경로에는 `approval`과 `execute` 이벤트가 없습니다. 검토 반려를 실행 승인 거절로 바꾸거나 자동 재시도하지 않는 것이 이 슬라이스의 안전 계약입니다.

### 6.3 계약 테스트와 정적 검사 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

테스트는 안전 작업의 역할 순서, Reviewer 거절의 조기 종료, 위험 작업의 별도 승인, 빈 검토 감사 필드 거부를 검사합니다.

## 7. 코드 설명

`ReviewDecision`은 검토 결과를 API 호출 결과가 아닌 입력 값으로 고정합니다. 빈 `feedback` 또는 `source`는 감사 가능한 판정이 아니므로 Node 전에 `ValueError`로 거부합니다.

```python
state = plan_node(state)
state = developer_node(state)
state = reviewer_node(state, decision=review_decision)
if state.status is WorkflowStatus.PLANNED:
    state = self._continue_after_review(state)
```

`reviewer_node()`는 거절 때 `REVIEW_REJECTED`를 반환합니다. 통과일 때는 `PLANNED`를 유지하여 `approval_node()`로 갈 수 있게 합니다. 그 뒤 위험 ActionKind는 기존과 동일하게 `WAITING_FOR_APPROVAL`에서 중단됩니다.

## 8. 정상 실행 결과

6.1의 출력 구조는 다음과 같습니다.

```text
검토 통과 후: status=waiting_for_approval
events=plan | developer | reviewer | approval
사람 실행 승인 후: status=completed
events=plan | developer | reviewer | approval | approval | execute
```

`uv run pytest tests/unit/test_volume09_graph.py -q`는 통과 테스트 수와 종료 코드 0을 반환해야 합니다. Ruff와 mypy도 오류 없이 종료되어야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `review feedback must not be empty` | Reviewer 근거가 빈 문자열입니다. | 실제 비밀이나 개인정보 없이, 학습용 검토 근거를 입력합니다. |
| `review source must not be empty` | 판정 출처가 없습니다. | 결정론적 출처 이름을 제공하고 외부 호출을 추가하지 않습니다. |
| `resolve_approval_node requires a waiting state` | Reviewer가 거절했거나 안전 작업이 이미 끝났습니다. | 검토 통과한 위험 작업의 `WAITING_FOR_APPROVAL` Checkpoint만 재개합니다. |
| `execute`가 Reviewer 거절 뒤에 보임 | 거절 상태를 무시하는 흐름이 추가됐습니다. | `REVIEW_REJECTED`에서는 `_continue_after_review()`를 호출하지 않도록 복원합니다. |

## 10. 응용 실습

1. Reviewer 피드백을 민감정보 없이 120자로 제한하는 입력 검증을 테스트 우선으로 설계합니다.
2. 안전한 `READ` 작업의 검토 통과 이벤트 순서를 테스트로 고정합니다.
3. 검토 반려 사유를 수정 요청 큐에 전달한다고 가정하고, 실제 큐 연결 없이 필요한 State 필드를 설계합니다.

## 11. 실무 적용

실무 Reviewer가 LLM, 정적 분석기 또는 사람이라도 검토 판정은 배포 권한이 아닙니다. 배포 승인에는 대상 환경, 변경 범위, 롤백, 승인자 역할, 만료 시간을 별도 정책으로 확인해야 합니다. 검토 근거와 실행 승인의 감사 로그도 접근 권한·보존 기간을 다르게 설계해야 합니다.

재시도는 검토 거절을 자동으로 통과시키는 수단이 되어서는 안 됩니다. 다음 장에서 제한된 재시도와 Error Node를 도입할 때도 재시도 상한과 최종 실패 경로를 명시하고, 위험 행위는 계속 사람 승인을 요구해야 합니다.

## 12. 과제

- **기본:** Planner, Developer, Reviewer가 각자 남겨야 할 감사 정보를 한 항목씩 작성합니다.
- **응용:** 검토 통과와 실행 승인을 분리하지 않았을 때의 실패 시나리오를 작성합니다.
- **심화:** Reviewer 거절 뒤 수정 요청을 한 번만 재시도하는 상태 전이와 Error Node를 다이어그램으로 설계합니다. 실제 도구 호출은 하지 않습니다.

## 13. 완료 체크리스트

- [ ] Planner → Developer → Reviewer 순서를 이벤트로 확인했다.
- [ ] Reviewer 거절이 `approval`, `execute` 없이 끝남을 확인했다.
- [ ] Reviewer 통과가 위험 작업의 실행 승인이 아님을 설명할 수 있다.
- [ ] 위험 작업이 별도 사람 승인 전 `execute`에 도달하지 않음을 확인했다.
- [ ] 예제와 테스트가 API, 네트워크, 실제 파일 변경, 배포 없이 동작함을 확인했다.
- [ ] `uv run pytest tests/unit/test_volume09_graph.py -q`를 통과했다.

## 14. 핵심 정리

역할 분리는 Agent 수를 늘리는 것이 아니라 책임과 종료 경계를 검증 가능하게 만드는 방법입니다. 이 장의 Planner-Developer-Reviewer 참조 Workflow는 검토 거절을 실행 전에 끝내고, 검토 통과한 위험 작업도 별도의 사람 승인 없이는 실행 시뮬레이션으로 보내지 않습니다.
