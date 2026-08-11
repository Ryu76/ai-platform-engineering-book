# 동일 JSON 경로의 독립 Checkpointer 동시 승인 안전성

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 같은 Python 프로세스에서 같은 JSON 경로를 여는 독립 Checkpointer 인스턴스의 승인 경쟁을 설명한다.
- 경로 단위 공유 Lock과 비교-교체로 하나의 승인 대기만 소비됨을 검증한다.
- 중복 승인 요청이 추가 `execute` 이벤트나 상태 변경을 만들지 못하게 한다.
- 프로세스 간 승인 소비와 실제 위험 작업에 운영 저장소가 필요한 이유를 구분한다.

## 2. 왜 필요한가

요청마다 `JsonFileCheckpointer(path=...)`를 새로 만드는 어댑터는 동일 파일을 가리켜도 인스턴스별 Lock만으로는 동시 승인을 안전하게 처리할 수 없습니다. 이 참조 모델은 정규화된 JSON 경로마다 프로세스 전역 Lock 하나를 공유합니다. 따라서 독립 인스턴스도 `save_if_current()`의 읽기·비교·교체를 함께 직렬화하여 하나의 `WAITING_FOR_APPROVAL` Checkpoint만 소비합니다.

> [!WARNING]
> 이 보장은 **하나의 Python 프로세스**와 정규화된 **같은 로컬 파일 경로**에만 적용됩니다. 여러 프로세스, 여러 호스트, 네트워크 파일 시스템과 실제 배포·삭제·전송에는 적용되지 않습니다. 예제의 `DEPLOY`는 외부 시스템을 변경하지 않는 결정론적 상태 전이입니다.

## 3. 핵심 개념

- **경로 단위 Lock:** 같은 정규화 `Path`를 쓰는 모든 `JsonFileCheckpointer` 인스턴스가 공유하는 프로세스 내 Lock입니다.
- **비교-교체:** 현재 State가 읽어 둔 승인 대기 State와 같을 때만 승인·실행 시뮬레이션 후보를 저장하는 연산입니다.
- **독립 인스턴스:** 각 요청이 별도로 만들었지만 같은 JSON 파일 경로를 가진 Checkpointer입니다.
- **승인 소비:** 엄격한 별도 Boolean `approved=True` 요청이 `WAITING_FOR_APPROVAL`을 한 번만 `COMPLETED`로 전이하는 과정입니다.
- **운영 저장소 경계:** 프로세스 밖 동시 writer에는 트랜잭션 compare-and-swap과 실행 멱등성이 필요한 경계입니다.

## 4. 동작 구조

```text
JSON: WAITING_FOR_APPROVAL (plan | approval)
                              |
                              v
  8개 동시 approval (독립 인스턴스, 동일 정규화 JSON 경로)
                              |
                              v
                  path Lock + save_if_current
                       |                    |
                       v                    v
  1개: COMPLETED                   7개: WorkflowRunConflictError
  approval | execute               기존 JSON을 교체하지 않음
```

어느 스레드가 먼저 Lock을 얻는지는 고정하지 않지만, 성공 수, 충돌 수, 최종 State 및 감사 이벤트는 결정론적으로 고정됩니다.

## 5. 실습 환경

사용 파일은 다음과 같습니다.

- `src/ai_platform/graph/checkpointer.py`
- `src/ai_platform/graph/workflow.py`
- `src/ai_platform/graph/api.py`
- `examples/volume09/json_shared_path_concurrent_approval_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

예제는 `TemporaryDirectory` 안의 JSON 파일, 로컬 스레드, 메모리 계산만 사용합니다. HTTP 서버, 네트워크, 실제 위험 작업, 비밀값은 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 별도 승인 요청 전까지 위험 작업을 대기시킨다

```python
adapters[0].start(
    request=StartWorkflowRequest(
        run_id="json-shared-path-approval-demo-001",
        task="학습용 배포를 준비한다",
        action=ActionKind.DEPLOY,
    )
)
```

시작 요청은 `plan | approval`만 기록합니다. `execute`는 명시적이고 엄격한 Boolean 승인 요청 전에는 존재하지 않습니다.

### 6.2 같은 경로의 독립 인스턴스로 승인 재전송을 보낸다

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

인스턴스는 여덟 개지만 `checkpoint_path.resolve()`가 같으므로 모두 같은 경로 단위 Lock을 얻습니다.

### 6.3 오프라인 계약을 실행한다

```bash
uv run python examples/volume09/json_shared_path_concurrent_approval_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

각 `DeterministicWorkflow.resume()`은 저장된 승인 대기 State에서 승인·실행 시뮬레이션 후보를 계산합니다. 후보는 외부 부작용이 없는 불변 값입니다. `JsonFileCheckpointer.save_if_current()`는 경로 단위 공유 Lock 안에서 JSON을 읽고 기대 State를 비교한 뒤, 일치할 때만 임시 파일 교체를 수행합니다.

첫 요청만 `COMPLETED` State와 `plan | approval | approval | execute`를 기록합니다. 나머지 요청은 이미 바뀐 State를 기대했으므로 `False` 또는 이미 소비된 승인 대기 오류를 받아 `WorkflowRunConflictError`로 끝납니다. 중복 요청은 기존 Action·감사 이벤트를 변경하거나 두 번째 `execute`를 추가할 수 없습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_shared_path_concurrent_approval_workflow.py
completed=1
conflicts=7
checkpoint=completed
events=plan | approval | approval | execute
```

`execute`는 로컬 State 이벤트일 뿐 실제 배포를 수행하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `completed=2` 이상 | 독립 인스턴스가 같은 정규화 경로 Lock을 공유하지 않거나 무조건 저장을 사용했을 수 있습니다. | `path.resolve()` 기반 Lock 조회와 `save_if_current()`를 확인합니다. |
| `conflicts=0` | 요청이 동시에 시작되지 않았거나 run ID가 다를 수 있습니다. | 하나의 run ID와 `Barrier(8)`을 사용합니다. |
| JSON 손상 오류 | 실습 파일을 수동으로 변경했거나 유효하지 않은 파일을 사용했을 수 있습니다. | 새 임시 디렉터리를 사용하고 스키마 검증 오류를 해결합니다. |
| 다른 프로세스에서 결과가 다름 | 프로세스 내 Lock 범위를 벗어났습니다. | 운영 저장소의 compare-and-swap 또는 트랜잭션을 사용합니다. |

## 10. 응용 실습

1. 독립 인스턴스 여덟 개로 동시 `approved=False` 요청을 실행했을 때 하나의 `REJECTED`만 기록되는지 확인합니다.
2. 하나의 독립 인스턴스가 이미 완료된 run을 재개하려 할 때 충돌로 끝나는 이유를 설명합니다.
3. 프로세스 간 승인 소비와 실제 실행에 데이터베이스 제약·트랜잭션·outbox가 필요한 이유를 설명합니다. 실제 다중 프로세스 경쟁은 실행하지 않습니다.

## 11. 실무 적용

이 Lock은 단일 프로세스 학습용 보호 장치입니다. 운영 환경은 모든 writer가 공유하는 데이터베이스 조건부 갱신으로 승인을 소비하고, 인증된 승인자·정책·만료·취소·대상 버전·멱등성 키를 기록해야 합니다.

조건부 State 저장만으로 실제 배포·삭제·전송의 exactly-once 실행을 보장하지 않습니다. 실제 위험 작업은 transaction outbox, 분리된 실행 워커, 대상 시스템의 멱등성 키 및 장애 복구 절차를 추가해야 합니다.

## 12. 과제

- **기본:** 두 독립 인스턴스가 같은 승인 대기 State를 읽은 뒤 하나만 비교-교체에 성공하는 순서를 설명합니다.
- **응용:** 같은 경로의 독립 인스턴스가 동시 거절을 한 번만 기록하는 테스트를 작성합니다.
- **심화:** 다중 프로세스 승인 소비와 실행을 위한 데이터베이스 제약·트랜잭션·outbox 설계를 작성합니다. 외부 저장소나 배포는 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] 동일 JSON 경로와 동일 Checkpointer 인스턴스의 보장 범위를 구분할 수 있다.
- [ ] 같은 프로세스의 독립 인스턴스가 승인 대기 하나만 소비함을 확인했다.
- [ ] 충돌 승인 요청이 기존 Action·감사 이벤트·완료 상태를 바꾸지 않음을 확인했다.
- [ ] 엄격한 별도 Boolean 승인 전에는 `execute`가 없음을 확인했다.
- [ ] 다중 프로세스·호스트에는 운영 저장소가 필요함을 설명할 수 있다.
- [ ] 예제, 테스트, 정적 검사를 오프라인으로 통과시켰다.

## 14. 핵심 정리

`JsonFileCheckpointer`의 경로 단위 공유 Lock은 한 Python 프로세스에서 같은 정규화 JSON 파일을 여는 독립 인스턴스까지 승인 Checkpoint의 비교-교체를 확장합니다. 동시 명시적 승인 중 하나만 오프라인 완료를 기록하고 중복 요청은 충돌로 끝납니다. 이 참조 모델은 실제 위험 작업이나 프로세스 간 exactly-once 보장을 제공하지 않으므로, 운영 환경에는 인증·트랜잭션·멱등성·분리된 실행 경계가 추가로 필요합니다.
