# 동일 JSON 경로의 독립 Checkpointer 동시 시작 안전성

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 같은 Python 프로세스에서 같은 JSON 경로를 여는 독립 Checkpointer 인스턴스의 경쟁을 설명한다.
- 경로 단위 공유 Lock으로 위험 작업 run ID가 한 번만 생성됨을 검증한다.
- 중복 시작이 기존 `DEPLOY` 승인 대기와 감사 이벤트를 바꾸지 못하게 한다.
- 프로세스 간 동시성 및 실제 위험 작업에 여전히 운영 저장소가 필요한 이유를 구분한다.

## 2. 왜 필요한가

웹 요청마다 `JsonFileCheckpointer(path=...)`를 새로 만드는 어댑터는 같은 파일을 가리켜도 인스턴스별 Lock만으로는 읽기·판정·교체를 직렬화할 수 없습니다. 이 참조 모델은 정규화된 JSON 경로마다 프로세스 전역 Lock 하나를 공유합니다. 따라서 같은 Python 프로세스에서 독립적으로 생성된 인스턴스도 `save_if_absent()`의 조건부 run 생성을 함께 보호합니다.

> [!WARNING]
> 이 보장은 **하나의 Python 프로세스**와 정규화된 **같은 로컬 파일 경로**에만 적용됩니다. 여러 프로세스, 여러 호스트, 네트워크 파일 시스템과 실제 배포·삭제·전송에는 적용되지 않습니다. 예제의 `DEPLOY`는 외부 시스템을 변경하지 않는 결정론적 상태 전이입니다.

## 3. 핵심 개념

- **경로 단위 Lock:** 같은 정규화 `Path`를 쓰는 모든 `JsonFileCheckpointer` 인스턴스가 공유하는 프로세스 내 Lock입니다.
- **조건부 생성:** `save_if_absent()`가 run ID가 없을 때만 최초 State를 저장하는 연산입니다.
- **독립 인스턴스:** 각 요청이 별도로 만들었지만 같은 JSON 파일 경로를 가진 Checkpointer입니다.
- **승인 대기 Checkpoint:** 위험 작업이 `plan | approval` 뒤 `WAITING_FOR_APPROVAL`에 머무르는 저장 상태입니다.
- **운영 저장소 경계:** 프로세스 밖 동시 writer에는 unique key와 조건부 삽입 또는 트랜잭션이 필요한 경계입니다.

## 4. 동작 구조

```text
8개 동시 start (독립 인스턴스, 동일 정규화 JSON 경로)
                              |
                              v
                path Lock + save_if_absent
                       |                    |
                       v                    v
  1개: WAITING_FOR_APPROVAL       7개: WorkflowRunConflictError
  events: plan | approval         기존 JSON을 교체하지 않음
```

어느 스레드가 먼저 Lock을 얻는지는 고정하지 않지만, 성공 수, 충돌 수, 최종 State 및 감사 이벤트는 결정론적으로 고정됩니다.

## 5. 실습 환경

사용 파일은 다음과 같습니다.

- `src/ai_platform/graph/checkpointer.py`
- `src/ai_platform/graph/workflow.py`
- `src/ai_platform/graph/api.py`
- `examples/volume09/json_shared_path_concurrent_start_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

예제는 `TemporaryDirectory` 안의 JSON 파일, 로컬 스레드, 메모리 계산만 사용합니다. HTTP 서버, 네트워크, 실제 위험 작업, 비밀값은 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 같은 경로로 독립 인스턴스를 만든다

```python
adapters = tuple(
    WorkflowApiAdapter(
        workflow=DeterministicWorkflow(
            checkpointer=JsonFileCheckpointer(path=checkpoint_path)
        )
    )
    for _ in range(8)
)
```

인스턴스는 여덟 개지만 `checkpoint_path.resolve()`는 같으므로 모두 같은 경로 단위 Lock을 얻습니다.

### 6.2 같은 위험 시작 요청을 동시에 보낸다

```python
request = StartWorkflowRequest(
    run_id="json-shared-path-start-demo-001",
    task="학습용 배포를 준비한다",
    action=ActionKind.DEPLOY,
)
```

승인 요청은 시작 요청과 분리됩니다. 시작 요청만으로는 `execute` Node에 도달할 수 없습니다.

### 6.3 오프라인 계약을 실행한다

```bash
uv run python examples/volume09/json_shared_path_concurrent_start_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

`JsonFileCheckpointer.__init__()`은 경로를 `resolve()`한 뒤 모듈 수준 경로 Lock 레지스트리에서 Lock을 가져옵니다. `save_if_absent()`는 이 공유 Lock 안에서 JSON을 읽고 run ID의 부재를 확인한 뒤 임시 파일 교체를 수행합니다.

그 결과 첫 요청만 `plan | approval` 상태를 기록합니다. 이후 요청은 `False`를 받아 `WorkflowRunConflictError`가 되므로 기존 Action, 승인 대기와 이벤트는 보존됩니다. `execute`는 별도의 엄격한 Boolean 승인 전에는 추가되지 않습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_shared_path_concurrent_start_workflow.py
waiting_for_approval=1
conflicts=7
checkpoint=waiting_for_approval
events=plan | approval
```

이 결과는 프로세스 내 공유 경로 Lock 계약만 보입니다. 실제 배포를 수행했다는 뜻이 아닙니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `waiting_for_approval=2` 이상 | 인스턴스가 같은 정규화 경로 Lock을 공유하지 않을 수 있습니다. | `path.resolve()` 기반 Lock 조회와 동일 파일 경로를 확인합니다. |
| `conflicts=0` | 요청마다 run ID가 다르거나 동시 실행이 시작되지 않았을 수 있습니다. | 하나의 run ID와 `Barrier(8)`을 사용합니다. |
| JSON 손상 오류 | 실습 파일을 수동으로 변경했거나 유효하지 않은 파일을 사용했을 수 있습니다. | 새 임시 디렉터리를 사용하고 스키마 검증 오류를 해결합니다. |
| 다른 프로세스에서 결과가 다름 | 프로세스 내 Lock 범위를 벗어났습니다. | 운영 저장소의 조건부 삽입 또는 트랜잭션을 사용합니다. |

## 10. 응용 실습

1. 독립 인스턴스 여덟 개로 동일 run ID의 안전 `READ` 시작을 실행했을 때도 하나만 생성되는지 확인합니다.
2. 같은 경로의 독립 인스턴스가 같은 위험 run을 승인할 때 필요한 프로세스 내 비교-교체 보장을 설명합니다.
3. 프로세스 간 정확한 run 생성에 데이터베이스 unique constraint가 필요한 이유를 설명합니다. 실제 다중 프로세스 경쟁은 실행하지 않습니다.

## 11. 실무 적용

이 Lock은 단일 프로세스 학습용 보호 장치입니다. 운영 환경은 모든 writer가 공유하는 데이터베이스 unique key 또는 조건부 삽입으로 run ID를 만들고, 승인 소비에는 트랜잭션 compare-and-swap을 사용해야 합니다.

실제 위험 작업은 승인 State 저장과 분리된 워커에서 실행해야 합니다. 실행 명령에는 멱등성 키, 대상 버전, 승인자·정책·만료 기록, outbox 및 장애 복구가 필요합니다.

## 12. 과제

- **기본:** 인스턴스별 Lock만 있을 때 두 인스턴스가 같은 빈 JSON 파일을 읽을 수 있는 순서를 설명합니다.
- **응용:** 동일 경로 독립 인스턴스의 동시 거절이 한 번만 기록되는 테스트를 설계합니다.
- **심화:** 다중 프로세스 run 생성과 승인 소비를 위한 데이터베이스 제약·트랜잭션·outbox 설계를 작성합니다. 외부 저장소나 배포는 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] 동일 JSON 경로와 동일 Checkpointer 인스턴스의 보장 범위를 구분할 수 있다.
- [ ] 같은 프로세스의 독립 인스턴스가 run ID 하나만 생성함을 확인했다.
- [ ] 충돌 시작이 기존 위험 Action·승인 대기·감사 이벤트를 바꾸지 않음을 확인했다.
- [ ] 엄격한 별도 Boolean 승인 전에는 `execute`가 없음을 확인했다.
- [ ] 다중 프로세스·호스트에는 운영 저장소가 필요함을 설명할 수 있다.
- [ ] 예제, 테스트, 정적 검사를 오프라인으로 통과시켰다.

## 14. 핵심 정리

`JsonFileCheckpointer`의 경로 단위 공유 Lock은 한 Python 프로세스에서 같은 정규화 JSON 파일을 여는 독립 인스턴스까지 조건부 run 생성을 확장합니다. 중복 위험 시작은 기존 승인 대기를 바꾸지 않고 충돌로 끝납니다. 이 참조 모델은 실제 위험 작업이나 프로세스 간 exactly-once 보장을 제공하지 않으므로, 운영 환경에는 인증·트랜잭션·멱등성·분리된 실행 경계가 추가로 필요합니다.
