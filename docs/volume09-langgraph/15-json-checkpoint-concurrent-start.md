# 단일 JSON Checkpointer 인스턴스의 동시 시작 안전성

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 로컬 JSON Checkpoint의 영속성과 단일 인스턴스 동시 시작 보장을 구분한다.
- 같은 `JsonFileCheckpointer` 인스턴스의 동시 시작 중 하나만 run ID를 생성함을 검증한다.
- 중복 시작이 기존 위험 작업의 승인 대기를 바꾸지 못하게 한다.
- 다중 프로세스 위험 작업에 필요한 운영 저장소 경계를 설명한다.

## 2. 왜 필요한가

클라이언트는 네트워크 오류 뒤 같은 시작 요청을 재전송할 수 있습니다. `load()`로 존재 여부를 확인한 뒤 `save()`하는 방식은 두 스레드가 모두 빈 run ID를 볼 수 있는 경쟁 조건을 만듭니다. 이 참조 모델은 같은 `JsonFileCheckpointer` 인스턴스의 Lock 안에서 `save_if_absent()`를 실행해 첫 상태 기록과 중복 판정을 묶습니다.

> [!WARNING]
> 이 보장은 한 Python 프로세스 안에서 하나의 `JsonFileCheckpointer` 객체를 공유할 때만 적용됩니다. 독립 인스턴스, 여러 프로세스, 네트워크 파일 시스템, 실제 배포·삭제·전송에는 적용되지 않습니다. 예제의 `DEPLOY`는 외부 시스템을 변경하지 않는 결정론적 상태 전이입니다.

## 3. 핵심 개념

- **원자적 생성:** run ID가 없을 때만 최초 State를 기록하는 조건부 저장입니다.
- **승인 대기 Checkpoint:** 위험 작업이 `plan | approval` 뒤 `WAITING_FOR_APPROVAL`에 머무르는 저장 상태입니다.
- **재전송 충돌:** 먼저 생성된 run ID에 도착한 시작 요청은 `WorkflowRunConflictError`로 끝나며 저장 상태를 바꾸지 않습니다.
- **인스턴스 내 Lock:** 같은 Checkpointer 객체를 공유하는 스레드의 JSON 읽기·판정·파일 교체를 직렬화합니다.
- **운영 저장소:** 다중 writer의 원자적 조건부 삽입을 제공해야 하는 별도 인프라 경계입니다.

## 4. 동작 구조

```text
8개 동시 start (같은 JsonFileCheckpointer 인스턴스)
                         |
                         v
              save_if_absent + instance Lock
                    |                    |
                    v                    v
  1개: WAITING_FOR_APPROVAL      7개: WorkflowRunConflictError
  events: plan | approval        기존 JSON을 교체하지 않음
```

성공하는 스레드는 실행마다 달라도 성공 수, 충돌 수, 최종 상태와 감사 이벤트는 고정됩니다.

## 5. 실습 환경

사용 파일은 다음과 같습니다.

- `src/ai_platform/graph/checkpointer.py`
- `src/ai_platform/graph/workflow.py`
- `src/ai_platform/graph/api.py`
- `examples/volume09/json_concurrent_start_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

예제는 `TemporaryDirectory` 안의 JSON 파일, 로컬 스레드, 메모리 계산만 사용합니다. HTTP 서버, 네트워크, 실제 위험 작업, 비밀값은 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 하나의 JSON Checkpointer를 주입한다

```python
from ai_platform.graph import DeterministicWorkflow, JsonFileCheckpointer, WorkflowApiAdapter

checkpointer = JsonFileCheckpointer(path=checkpoint_path)
adapter = WorkflowApiAdapter(
    workflow=DeterministicWorkflow(checkpointer=checkpointer)
)
```

각 스레드가 Checkpointer를 새로 만들면 이 장의 인스턴스 내 Lock 계약을 검증할 수 없습니다.

### 6.2 같은 위험 시작 요청을 동시 재전송한다

```python
request = StartWorkflowRequest(
    run_id="json-start-demo-001",
    task="학습용 배포를 준비한다",
    action=ActionKind.DEPLOY,
)
```

모든 스레드는 같은 `request`와 같은 어댑터를 사용합니다. 하나만 run ID를 만들며 승인 요청은 이 단계에 포함하지 않습니다.

### 6.3 오프라인 계약을 실행한다

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run python examples/volume09/json_concurrent_start_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

`WorkflowApiAdapter.start()`는 `DeterministicWorkflow.invoke_new()`만 호출합니다. `invoke_new()`는 `WorkflowState` 후보를 만든 뒤 `save_if_absent()`가 `True`를 반환할 때만 그 상태를 새 run으로 공개합니다.

`JsonFileCheckpointer.save_if_absent()`는 인스턴스 Lock 안에서 JSON을 읽고 run ID 존재를 확인합니다. 첫 요청은 `plan | approval` 상태를 파일에 기록합니다. 뒤따르는 요청은 `False`를 반환하고 `WorkflowRunConflictError`가 되므로 원래의 `DEPLOY`, 승인 대기 상태와 감사 이벤트가 보존됩니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_concurrent_start_workflow.py
waiting_for_approval=1
conflicts=7
checkpoint=waiting_for_approval
events=plan | approval
```

`execute`가 없다는 것은 별도의 엄격한 Boolean 승인 전에는 외부 부작용 없는 실행 시뮬레이션도 시작하지 않았음을 뜻합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `waiting_for_approval=2` 이상 | 조건부 생성 대신 무조건 `save()`를 사용했을 수 있습니다. | `save_if_absent()`의 성공 결과 뒤에만 시작 State를 반환합니다. |
| `conflicts=0` | 요청마다 run ID가 다르거나 같은 Checkpointer 객체를 공유하지 않았을 수 있습니다. | 하나의 run ID와 하나의 `JsonFileCheckpointer` 인스턴스를 사용합니다. |
| JSON 손상 오류 | 실습 파일을 수동으로 수정했거나 유효하지 않은 파일을 사용했을 수 있습니다. | 새 임시 디렉터리를 사용하고 스키마 검증 오류를 해결합니다. |
| 별도 프로세스에서 결과가 다름 | 이 장의 Lock 범위를 벗어났습니다. | 운영 저장소의 조건부 삽입 또는 트랜잭션을 별도로 설계합니다. |

## 10. 응용 실습

1. 같은 run ID로 `READ`와 `DEPLOY` 시작 요청을 동시에 제출할 때 최초 요청의 Action만 남는 이유를 설명합니다.
2. 서로 다른 run ID 8개를 하나의 JSON Checkpointer 인스턴스로 시작해 각각 승인 대기가 되는지 확인합니다.
3. 독립 인스턴스·프로세스 보장을 주장하지 않는 이유를 파일 시스템 경쟁 관점에서 설명합니다. 실제 다중 프로세스 경쟁은 실행하지 않습니다.

## 11. 실무 적용

운영 시작 요청에는 다중 writer를 지원하는 저장소의 unique key와 원자적 조건부 삽입이 필요합니다. run ID에는 요청 멱등성 키, 요청자·대상 버전·정책 버전·만료 시간·불변 감사 정보를 연결해야 합니다.

조건부 run 생성만으로 실제 위험 작업의 exactly-once 실행을 보장할 수는 없습니다. 승인 소비, 실행 명령 발행, 대상 시스템 멱등성 키, outbox 및 장애 복구를 서로 분리해 설계해야 합니다.

## 12. 과제

- **기본:** `load()` 뒤 `save()`하는 시작 흐름의 경쟁 조건을 두 스레드의 순서로 설명합니다.
- **응용:** 같은 인스턴스의 동시 시작 뒤 `execute` 이벤트가 없음을 확인하는 테스트를 확장합니다.
- **심화:** 데이터베이스 unique constraint, 조건부 삽입, 실행 outbox를 포함하는 위험 작업 시작 설계를 작성합니다. 외부 저장소나 배포는 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] JSON 영속성과 인스턴스 내 동시 시작 보장을 구분할 수 있다.
- [ ] 같은 JSON Checkpointer 인스턴스에서 동시 시작 하나만 run ID를 생성함을 확인했다.
- [ ] 충돌 시작이 기존 위험 Action과 승인 대기를 바꾸지 않음을 확인했다.
- [ ] 엄격한 별도 Boolean 승인 전에는 `execute`가 없음을 확인했다.
- [ ] 다중 인스턴스·프로세스에 운영용 조건부 삽입이 필요함을 설명할 수 있다.
- [ ] 예제, 테스트, 정적 검사를 오프라인으로 통과시켰다.

## 14. 핵심 정리

`JsonFileCheckpointer.save_if_absent()`는 한 인스턴스가 공유하는 스레드 범위에서 run ID의 최초 생성을 한 번으로 제한합니다. 이 오프라인 참조 모델에서 중복 시작은 기존 승인 대기를 덮어쓰지 않고 충돌로 끝납니다. 실제 위험 작업에는 인증, 다중 writer 트랜잭션, 멱등성, 분리된 실행 경계가 추가로 필요합니다.
