# State Reducer와 결정론적 감사 이벤트 병합

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- State Reducer가 여러 Node 업데이트를 하나의 상태 필드로 병합하는 이유를 설명한다.
- 로컬 Node 이벤트를 연속된 전역 감사 순서로 결정론적으로 병합한다.
- 순서가 모호하거나 손상된 이벤트 입력을 Reducer 경계에서 거부한다.
- 병렬 Node의 도착 순서와 위험 작업의 승인 순서를 혼동하지 않는다.

## 2. 왜 필요한가

여러 Node가 같은 `events` State 필드를 갱신하면 단순 대입은 앞선 감사 기록을 덮어쓸 수 있습니다. LangGraph의 Reducer는 이런 필드의 병합 방식을 명시하는 개념입니다. 이 Volume의 참조 모델은 `reduce_events()`로 각 Node의 로컬 이벤트를 기존 이벤트 뒤에 붙이고, 전체 sequence를 1부터 연속되게 만듭니다.

> [!WARNING]
> Reducer가 병렬 실행의 도착 순서를 안전한 승인 순서로 바꾸지는 않습니다. 이 학습용 모델은 외부 병렬 작업을 시작하지 않으며, 비결정적 입력은 호출자가 안정적인 순서로 정한 뒤 Reducer에 전달해야 합니다. `delete`, `deploy`, `send`은 이벤트 병합과 무관하게 명시적 승인 전에는 실행되지 않습니다.

## 3. 핵심 개념

- **Reducer:** 같은 State 필드의 기존 값과 Node 업데이트를 합치는 순수 함수입니다.
- **기존 이벤트:** 이미 저장된 전역 감사 로그입니다. sequence는 1부터 빈틈없이 이어져야 합니다.
- **로컬 업데이트:** 한 Node 또는 정렬이 끝난 Node 묶음이 만든 이벤트입니다. 입력 sequence는 다시 1부터 시작합니다.
- **정규화:** Reducer가 로컬 sequence에 기존 로그 길이를 더해 전역 sequence를 만듭니다.
- **결정성:** 동일한 기존 로그와 동일한 정렬된 업데이트는 언제나 같은 결과를 만듭니다.

## 4. 동작 구조

```text
existing events                 local Node updates
1: plan                         1: approval
                                2: execute
       \                         /
        \---- reduce_events ----/
                  |
                  v
global audit events: 1: plan | 2: approval | 3: execute
```

`WorkflowState.record()`도 이 Reducer를 사용합니다. 따라서 일반 Workflow의 `plan → approval → execute` 이벤트는 직접 tuple을 이어 붙이는 숨은 규칙이 아니라, 테스트 가능한 병합 계약을 거칩니다.

## 5. 실습 환경

사용 파일은 다음과 같습니다.

- `src/ai_platform/graph/state.py`
- `examples/volume09/reducer_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

이 실습은 메모리 안의 불변 값만 병합합니다. 네트워크, HTTP 서버, 실제 배포, 파일 삭제, 비밀값은 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 로컬 이벤트를 병합한다

```python
from ai_platform.graph import WorkflowEvent, reduce_events

existing_events = (
    WorkflowEvent(sequence=1, node="plan", detail="오프라인 계획"),
)
local_node_updates = (
    WorkflowEvent(sequence=1, node="approval", detail="안전 작업 확인"),
    WorkflowEvent(sequence=2, node="execute", detail="오프라인 완료"),
)

merged_events = reduce_events(existing_events, local_node_updates)
assert [event.sequence for event in merged_events] == [1, 2, 3]
assert [event.node for event in merged_events] == ["plan", "approval", "execute"]
```

### 6.2 손상된 순서를 거부한다

```python
from ai_platform.graph import WorkflowEvent, reduce_events

invalid_updates = (
    WorkflowEvent(sequence=2, node="approval", detail="순서 오류"),
)

try:
    reduce_events((), invalid_updates)
except ValueError as error:
    assert "event updates" in str(error)
```

### 6.3 예제와 계약을 실행한다

```bash
uv run python examples/volume09/reducer_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

`reduce_events(existing, updates)`는 두 tuple을 받아 둘 다 1부터 연속된 sequence인지 먼저 확인합니다. 업데이트는 로컬 로그이므로 항상 1부터 시작해야 합니다. 확인이 끝나면 `dataclasses.replace()`로 업데이트의 sequence만 기존 길이만큼 이동합니다. 원래 이벤트 객체와 기존 State는 변경하지 않습니다.

`WorkflowState.record()`는 새 이벤트를 sequence `1`인 로컬 업데이트로 만들고 Reducer에 넘깁니다. Reducer가 전역 sequence를 계산하므로 모든 Node가 같은 감사 병합 규칙을 사용합니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/reducer_workflow.py
events=plan | approval | execute
sequences=1 | 2 | 3
```

`approval`과 `execute`는 예제용 안전 작업 이벤트일 뿐 실제 실행을 뜻하지 않습니다. 위험 ActionKind의 경우에는 Approval Node가 별도 사람 결정을 기록하기 전 `execute` 이벤트를 만들지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `existing events must have a contiguous sequence` | 저장된 감사 로그가 1부터 시작하지 않거나 중간 번호가 비었습니다. | Checkpoint 복원 전에 이벤트 스키마와 순서를 검증하고 손상된 상태를 재개하지 않습니다. |
| `event updates must have a contiguous sequence` | Node가 전역 sequence를 직접 전달했거나 업데이트 순서가 정해지지 않았습니다. | 업데이트는 로컬 sequence `1..n`으로 만들고 안정적인 정렬 뒤 Reducer에 전달합니다. |
| 병렬 결과의 이벤트 순서가 실행마다 다름 | 여러 결과의 도착 순서가 비결정적입니다. | Reducer 전에 명시적 정렬 키 또는 단일 조정 Node를 설계합니다. |
| 승인 전에 `execute`가 나타남 | 이벤트 Reducer와 Approval Node의 책임을 혼동했습니다. | 위험 action은 Approval Node와 별도 strict Boolean 승인 요청을 먼저 통과시킵니다. |

## 10. 응용 실습

1. 빈 `updates`를 병합해 기존 이벤트가 바뀌지 않는 테스트를 작성합니다.
2. 두 개의 완료된 로컬 Node 업데이트 묶음을 고정된 Node 이름순으로 정렬한 뒤 병합하는 순수 함수를 작성합니다.
3. 실제 병렬 실행 없이, 서로 다른 도착 순서가 왜 서로 다른 감사 로그가 될 수 있는지 표로 설명합니다.

## 11. 실무 적용

운영 Graph에서는 어떤 State 필드가 대입이고 어떤 필드가 Reducer 병합인지 명시해야 합니다. 메시지나 이벤트처럼 누적해야 하는 필드는 idempotency key, 중복 제거, 정렬 기준, 보존 정책도 함께 설계합니다.

감사 이벤트 순서는 승인 권한을 부여하지 않습니다. 위험 작업에는 인증된 승인자, 승인 대상 버전, 만료 시간, 변경 영향, 권한 분리를 확인하는 별도 정책과 저장소 트랜잭션이 필요합니다. 이 오프라인 Reducer는 그 정책을 대신하지 않습니다.

## 12. 과제

- **기본:** State 필드를 단순 대입할 때 감사 이벤트가 유실되는 사례를 설명합니다.
- **응용:** `reduce_events()`가 기존 이벤트를 변경하지 않는 이유를 불변 객체 관점에서 설명합니다.
- **심화:** 다중 worker가 만든 이벤트를 하나의 안정적 순서로 병합할 저장소 스키마와 정렬 키를 설계합니다. 외부 저장소는 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] Reducer와 State 대입의 차이를 설명할 수 있다.
- [ ] 로컬 이벤트가 전역 연속 sequence로 병합됨을 확인했다.
- [ ] 손상된 기존 로그와 업데이트가 거부됨을 확인했다.
- [ ] 비결정적 병렬 도착 순서를 Reducer가 해결하지 않음을 구분했다.
- [ ] 위험 작업의 Approval 경계가 이벤트 병합과 별도임을 확인했다.
- [ ] 예제, 테스트, 정적 검사를 오프라인으로 통과시켰다.

## 14. 핵심 정리

Reducer는 여러 Node 업데이트가 같은 State 필드를 안전하고 예측 가능하게 공유하도록 만드는 명시적 병합 규칙입니다. 이 Volume의 `reduce_events()`는 검증된 로컬 감사 이벤트를 기존 로그 뒤에 붙여 연속된 전역 sequence를 만듭니다. 결정론적 순서는 입력을 먼저 안정화할 때만 보장되며, 이벤트 병합은 위험 작업의 사람 승인을 대체하지 않습니다.
