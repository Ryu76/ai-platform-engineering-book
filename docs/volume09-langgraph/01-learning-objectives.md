# 상태형 Workflow의 학습 목표와 안전 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Graph 기반 Workflow를 State, Node, Edge, `START`, `END`로 설명한다.
- 상태를 불변 값으로 전달하고 Node가 남긴 이벤트로 전이 경로를 확인한다.
- 위험 작업을 조건 분기로 `WAITING_FOR_APPROVAL`에 중단(interrupt)한다.
- 사람의 명시적 승인 또는 거절로만 Checkpoint를 재개한다.
- 외부 API, 실제 배포, 실제 파일 삭제 없이 결정론적인 테스트를 실행한다.

## 2. 왜 필요한가

Agent Workflow는 한 번의 함수 호출보다 긴 작업을 다룹니다. 계획을 세우고, 조건에 따라 다음 작업을 고르고, 실패 또는 승인 대기 뒤에 다시 시작해야 합니다. 일반적인 `if` 문만으로도 시작할 수 있지만, 상태와 전이 기록이 흩어지면 현재 어디까지 실행했는지, 위험 작업이 정말 승인 전 중단되었는지 확인하기 어렵습니다.

Graph는 이 문제를 State와 연결 규칙으로 드러냅니다. Node는 State를 읽어 다음 State를 반환하고, Edge는 어느 Node로 이동할지 정의합니다. LangGraph는 이런 상태형 Workflow를 구성하는 라이브러리입니다. 이 첫 장은 설치되지 않은 라이브러리 API를 흉내 내지 않고, 그 핵심 경계를 오프라인 참조 구현으로 검증합니다.

## 3. 핵심 개념

- **State**: Node 사이에 전달되는 현재 작업, 승인 상태, 결과, 이벤트입니다.
- **Node**: State를 받아 검증된 새 State를 반환하는 작업 단위입니다.
- **Edge**: 한 Node의 결과가 다음 Node를 선택하는 연결입니다.
- **Conditional Edge**: `approval_required`처럼 State 조건에 따라 흐름이 갈라지는 Edge입니다.
- **START / END**: Graph 실행의 시작과 종료를 나타내는 경계입니다.
- **Interrupt**: 위험 작업이 승인 대기 상태에서 멈추고, 나중에 같은 Checkpoint에서 재개되는 지점입니다.
- **Checkpoint**: run ID에 연결된 가장 최근 State입니다. 이 장의 `MemoryCheckpointer`는 프로세스 안에서만 보관하므로 재시작하면 사라집니다.
- **결정론성**: 같은 `task`, `action`, 승인 판단에는 같은 상태와 이벤트 순서가 나오는 성질입니다.

`DELETE`, `DEPLOY`, `SEND`은 위험 작업으로 분류합니다. 이 분류는 실제 권한을 주지 않습니다. 오히려 예제가 그런 작업을 실행하지 못하도록 `execute_node()`는 외부 부작용 없이 문자열 결과만 만듭니다.

## 4. 동작 구조

```text
START
  │ WorkflowState.start(task, action)
  ▼
plan Node ── State: PENDING → PLANNED
  ▼
approval Node
  ├── read / transform ────────────────► READY ─► execute Node ─► COMPLETED (END)
  │
  └── delete / deploy / send ─────────► WAITING_FOR_APPROVAL (interrupt)
                                            │
                                사람의 명시적 결정
                                  ┌─────────┴─────────┐
                                  ▼                   ▼
                               approved             rejected
                                  │                   │
                                  ▼                   ▼
                              execute Node       REJECTED (END)
                                  │
                                  ▼
                            COMPLETED (END)
```

모든 Node는 `WorkflowEvent`를 남깁니다. 따라서 테스트는 결과뿐 아니라 `plan → approval → execute` 경로 또는 `plan → approval → approval` 거절 경로를 검사할 수 있습니다.

## 5. 실습 환경

필요한 파일은 다음 경로에 있습니다.

- `src/ai_platform/graph/state.py`
- `src/ai_platform/graph/nodes.py`
- `src/ai_platform/graph/workflow.py`
- `src/ai_platform/graph/checkpointer.py`
- `examples/volume09/single_node_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
uv sync --all-groups
```

`uv sync --all-groups`는 프로젝트 코드와 pytest, Ruff, mypy를 준비합니다. 이 장은 API 키, `.env`, 네트워크, LangGraph 패키지를 요구하지 않습니다. 현재 `pyproject.toml`에 `langgraph`는 없으므로, 설치를 위해 프로젝트 설정을 임의로 변경하지 마십시오.

## 6. 단계별 실습

### 6.1 위험 작업의 승인 중단 확인

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume09/single_node_workflow.py
```

예제는 `DEPLOY`를 선택하지만 실제 배포를 호출하지 않습니다. 첫 출력의 상태는 `waiting_for_approval`이고 결과는 `None`이어야 합니다. 이어서 코드 안의 `approved=True`가 사람의 명시적 승인 입력을 나타내며, 두 번째 출력에서만 `completed`가 됩니다.

### 6.2 Workflow 계약 테스트 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run pytest tests/unit/test_volume09_graph.py -q
```

테스트는 읽기 작업의 완료, 배포 작업의 승인 전 중단, 승인 후 재개, 거절 후 미실행, 없는 또는 완료된 Checkpoint 재개 실패, 빈 작업 입력 거부를 검사합니다. Mock, 네트워크, 실제 시스템 명령을 사용하지 않습니다.

### 6.3 정적 검사 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

첫 명령은 스타일과 잠재 오류를, 둘째 명령은 엄격한 타입 계약을 검사합니다. 실패하면 위험 작업의 승인 조건을 완화하지 말고 State 전이와 타입을 먼저 수정합니다.

## 7. 코드 설명

`WorkflowState.start()`는 빈 작업을 처음에 거부하고, ActionKind가 위험 집합에 속하는지 `approval_required`에 기록합니다. `record()`는 기존 State를 변경하지 않고 새 이벤트가 추가된 State를 반환합니다. 이 불변성은 Checkpoint에서 읽은 상태가 Node 내부에서 예상치 못하게 바뀌는 문제를 줄입니다.

```python
state = WorkflowState.start(task=task, action=action)
state = plan_node(state)
state = approval_node(state)
if state.status is WorkflowStatus.READY:
    state = execute_node(state)
```

`approval_node()`는 위험 작업을 `WAITING_FOR_APPROVAL`에 둡니다. 이 경우 `invoke()`는 `execute_node()`를 호출하지 않고 Checkpoint만 저장합니다. `resume()`은 같은 run ID를 읽은 뒤 `resolve_approval_node()`에 `approved` 값을 전달합니다. 거절이면 `REJECTED`로 끝나며, 승인일 때만 `READY → COMPLETED` Edge를 지납니다.

`execute_node()`의 결과는 `오프라인 시뮬레이션 완료: ...` 문자열뿐입니다. 이름이 `deploy`여도 배포 API, 셸 명령, 파일 시스템 변경은 발생하지 않습니다.

## 8. 정상 실행 결과

6.1 명령은 다음과 같은 구조를 출력합니다.

```text
승인 전: status=waiting_for_approval
result=None
events=plan | approval
승인 후: status=completed
result=오프라인 시뮬레이션 완료: deploy / 학습용 배포 계획을 검토한다
events=plan | approval | approval | execute
```

6.2 명령은 통과한 테스트 수와 함께 종료 코드 0을 반환합니다. 6.3의 Ruff와 mypy도 각각 오류 없음 메시지와 종료 코드 0을 반환해야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `ModuleNotFoundError: ai_platform` | 저장소 루트가 아니거나 환경이 준비되지 않았습니다. | 저장소 루트에서 `uv sync --all-groups` 후 `uv run ...`을 사용합니다. |
| `checkpoint not found` | 잘못된 run ID로 재개를 요청했습니다. | 먼저 같은 run ID로 위험 작업을 `invoke()`하여 승인 대기 Checkpoint를 만듭니다. |
| `resolve_approval_node requires a waiting state` | 이미 완료·거절된 실행 또는 안전 작업을 재개하려 했습니다. | `WAITING_FOR_APPROVAL` 상태만 한 번 승인 또는 거절합니다. |
| 실제 배포가 될까 걱정됨 | 예제의 `DEPLOY` 이름을 실제 호출로 오해했습니다. | 이 장의 `execute_node()`가 문자열만 반환하는지 확인하고, 예제를 수정해 실제 명령을 추가하지 않습니다. |
| `langgraph` import 오류 | 현 프로젝트 의존성에 패키지가 없습니다. | 이 장은 직접 구현한 참조 경로를 사용합니다. 패키지 추가는 승인된 별도 프로젝트 설정 변경으로 처리합니다. |

## 10. 응용 실습

1. `ActionKind.TRANSFORM`을 실행하고, 승인 없이 `COMPLETED`로 끝나는 이벤트 순서를 테스트로 고정합니다.
2. 위험 ActionKind를 하나 더 추가한 뒤 `RISKY_ACTIONS`에 포함하지 않았을 때 생기는 보안 결함을 설명하고, 실패하는 테스트를 먼저 작성합니다.
3. `MemoryCheckpointer`를 영속 저장소로 교체한다고 가정하고 run ID 소유권, 암호화, 보존 기간, 삭제 요청을 설계합니다. 실제 저장소 연결은 하지 않습니다.

## 11. 실무 적용

실무의 위험도는 ActionKind 이름만으로 판단할 수 없습니다. 대상 환경, 변경 범위, 요청자 권한, 승인자 역할, 시간 제한을 함께 검증해야 합니다. 승인 화면은 승인 대상의 요약과 예상 영향, 되돌리기 방법을 보여야 하며, 단순한 "계속" 버튼이 되어서는 안 됩니다.

Checkpoint를 영속화하면 재개 가능성은 높아지지만 개인정보·토큰·도구 인수도 보존될 수 있습니다. 민감 정보를 최소화하고, 접근 제어와 만료 정책을 적용하며, 체크포인트가 변경 불가능한 감사 기록인지 별도로 결정해야 합니다. Volume 10에서는 이 흐름의 성공률과 승인 정책을 오프라인 평가 데이터로 측정합니다.

## 12. 과제

- **기본:** State, Node, Edge, Checkpoint가 각각 어떤 문제를 줄이는지 한 문장씩 작성합니다.
- **응용:** `SEND` 작업이 승인 대기 중일 때 출력하면 안 되는 정보 세 가지를 정하고, 이벤트 `detail`에 넣지 않는 테스트를 설계합니다.
- **심화:** 재시도 가능한 읽기 오류와 사람 승인이 필요한 배포 오류를 구분하는 조건 분기표를 작성합니다. 재시도 횟수 상한과 최종 Error Node도 포함합니다.

## 13. 완료 체크리스트

- [ ] State, Node, Edge, `START`, `END`를 구분해 설명할 수 있다.
- [ ] 위험 작업이 승인 전 `execute` Node에 도달하지 않음을 확인했다.
- [ ] 승인과 거절이 서로 다른 종료 경로를 만든다는 것을 확인했다.
- [ ] run ID로 Checkpoint를 읽고 재개하는 이유를 설명할 수 있다.
- [ ] 모든 기본 실습이 외부 API·네트워크·실제 배포·실제 삭제 없이 동작함을 확인했다.
- [ ] `uv run pytest tests/unit/test_volume09_graph.py -q`가 통과했다.
- [ ] 실제 API 키, 회사 자료, 개인정보를 예제 입력이나 이벤트에 넣지 않았다.

## 14. 핵심 정리

상태형 Workflow의 핵심은 작업을 자동으로 많이 실행하는 것이 아니라, 현재 상태와 다음 전이를 검증 가능하게 만드는 것입니다. 이 장의 참조 구현은 위험 작업을 승인 대기에 멈추고, 명시적인 사람 결정 뒤에만 오프라인 시뮬레이션을 완료합니다. 다음 장에서는 이 안전 경계를 유지한 채 조건 분기와 여러 Node를 확장합니다.
