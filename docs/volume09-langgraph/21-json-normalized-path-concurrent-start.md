# 정규화된 JSON 경로 별칭의 동시 시작 안전성

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 서로 다른 `Path` 표기가 정규화 뒤 같은 파일을 가리키는 시작 경쟁을 설명한다.
- 독립 Checkpointer 인스턴스가 정규화된 경로 단위 Lock 하나를 공유함을 검증한다.
- 동시 시작 재전송 하나만 위험 작업의 `WAITING_FOR_APPROVAL` Checkpoint를 생성하게 한다.
- 이 프로세스 내 파일 경계를 운영 환경의 다중 프로세스 잠금으로 오해하지 않는다.

## 2. 왜 필요한가

호출자는 같은 파일을 `checkpoints.json` 또는 `path-alias/../checkpoints.json`처럼 서로 다르게 표기할 수 있습니다. 표기 문자열 자체를 Lock 키로 쓰면 같은 파일에 서로 다른 Lock이 생겨 `save_if_absent()`의 읽기·생성 경쟁이 발생합니다. `JsonFileCheckpointer`는 생성 시 `Path.resolve()` 결과를 Lock 키와 파일 경로로 사용하므로, 같은 Python 프로세스 안에서는 이 두 표기가 하나의 Lock을 공유합니다.

위험 작업의 시작은 사람 승인 대기를 만드는 첫 기록입니다. 따라서 별칭 경로를 쓰는 중복 `DEPLOY` 시작 재전송도 하나의 `WAITING_FOR_APPROVAL`만 기록해야 하며, 충돌 요청은 기존 Action·감사 이벤트·승인 경계를 바꾸거나 `execute`로 이동해서는 안 됩니다.

> [!WARNING]
> 이 예제의 `DEPLOY`는 외부 시스템을 변경하지 않는 결정론적 상태 전이입니다. 명시적인 엄격한 Boolean 승인 전에는 `execute`로 이동하지 않으며, 예제는 실제 배포·네트워크·비밀값을 사용하지 않습니다.

## 3. 핵심 개념

- **경로 별칭:** `..` 같은 경로 구성 요소 때문에 문자열은 다르지만 같은 파일을 가리키는 `Path` 표기입니다.
- **정규화:** `Path.resolve()`로 별칭을 제거해 하나의 로컬 파일 식별자로 만드는 과정입니다.
- **경로 단위 Lock:** 정규화된 파일 식별자마다 하나만 존재하는 프로세스 내 Lock입니다.
- **원자적 생성:** run ID가 없을 때만 첫 상태를 저장하는 `save_if_absent()` 계약입니다.
- **승인 경계:** 위험 작업은 생성 성공 뒤에도 `WAITING_FOR_APPROVAL`에서 멈추며 별도 엄격한 Boolean 승인 없이는 실행하지 않는 규칙입니다.

## 4. 동작 구조

```text
checkpoints.json              path-alias/../checkpoints.json
        \                              /
         \------ Path.resolve() ------/
                         |
                         v
          하나의 path Lock + save_if_absent
                    |                  |
                    v                  v
  1개: WAITING_FOR_APPROVAL    7개: WorkflowRunConflictError
       plan, approval              기존 checkpoint 보존
       execute 없음
```

어느 스레드가 먼저 Lock을 얻는지는 고정하지 않지만, 생성 성공 수는 하나, 충돌 수는 일곱, 최종 감사 이벤트는 `plan | approval`로 고정됩니다.

## 5. 실습 환경

사용 파일은 다음과 같습니다.

- `src/ai_platform/graph/checkpointer.py`
- `src/ai_platform/graph/workflow.py`
- `src/ai_platform/graph/api.py`
- `examples/volume09/json_normalized_path_concurrent_start_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

예제는 `TemporaryDirectory`, 로컬 스레드와 메모리 계산만 사용합니다. HTTP 서버, 네트워크, 실제 위험 작업, 비밀값은 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 같은 파일의 서로 다른 표기를 만든다

```python
checkpoint_path = Path(directory) / "checkpoints.json"
alias_directory = Path(directory) / "path-alias"
alias_directory.mkdir()
alias_path = alias_directory / ".." / checkpoint_path.name
```

두 `Path` 객체는 같지 않지만, 생성자 내부의 `resolve()` 결과는 같습니다. 별칭 디렉터리를 실제로 만들어 경로 해석이 로컬 파일 시스템에서 명확하도록 합니다.

### 6.2 독립 인스턴스에 두 표기를 번갈아 주입한다

```python
JsonFileCheckpointer(
    path=checkpoint_path if index % 2 == 0 else alias_path
)
```

각 어댑터와 Checkpointer는 독립 객체입니다. 그러나 정규화된 경로가 같으므로 `save_if_absent()`는 동일 Lock 안에서 run ID의 부재를 확인하고 첫 상태만 저장합니다.

### 6.3 오프라인 시작 계약을 실행한다

```bash
uv run python examples/volume09/json_normalized_path_concurrent_start_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

여덟 스레드는 Barrier 뒤에 같은 엄격한 `StartWorkflowRequest`를 보냅니다. 각 Workflow는 `plan → approval`으로 계산한 `DEPLOY`의 `WAITING_FOR_APPROVAL` 후보를 만들지만, 정규화된 경로의 공유 Lock 안에서 `save_if_absent()`에 성공한 하나만 그 후보를 기록합니다.

첫 요청은 `approval_granted=None`, 결과 없는 승인 대기와 `plan | approval`만 기록합니다. 나머지 요청은 run ID가 이미 존재함을 확인해 `WorkflowRunConflictError`로 끝납니다. 따라서 기존 Action·승인 대기·감사 이벤트는 바뀌지 않고 `execute`가 추가되지 않습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_normalized_path_concurrent_start_workflow.py
waiting_for_approval=1
conflicts=7
checkpoint=waiting_for_approval
approval_granted=None
events=plan | approval
```

`execute`와 결과가 모두 없다는 점은 시작 성공도 실제 위험 작업을 수행하지 않고 별도 승인 interrupt만 만든다는 뜻입니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `waiting_for_approval=2` 이상 | Lock 키가 원래 문자열이고 정규화되지 않았을 수 있습니다. | 생성 시 `path.resolve()`를 Lock 조회와 파일 경로에 모두 사용합니다. |
| `conflicts=0` | 같은 run ID를 쓰지 않았거나 동시 시작 Barrier가 없을 수 있습니다. | 하나의 `StartWorkflowRequest`와 `Barrier(8)`을 사용합니다. |
| `execute`가 있음 | 위험 ActionKind가 아니거나 승인 처리가 시작 경로에 섞였을 수 있습니다. | `ActionKind.DEPLOY`와 별도 `ApprovalRequest` 경계를 확인합니다. |
| 프로세스마다 결과가 다름 | Lock 범위를 벗어났습니다. | 운영 저장소의 조건부 삽입 또는 트랜잭션을 사용합니다. |

## 10. 응용 실습

1. 두 별칭을 각각 `save_if_current()`에 사용해도 승인 대기 하나만 소비되는 이유를 설명합니다.
2. 별칭 인스턴스의 동시 시작 뒤 하나만 명시적으로 거절되고 나머지 거절 재전송은 충돌하는 테스트를 작성합니다.
3. 심볼릭 링크, 여러 프로세스, 네트워크 파일 시스템이 이 학습용 `resolve()`·Lock 보장을 확장하지 못하는 이유를 설명합니다.

## 11. 실무 적용

`Path.resolve()`는 한 프로세스 안의 단순한 로컬 경로 별칭을 하나의 Lock 키로 만드는 학습용 장치입니다. 심볼릭 링크 정책, 권한, 파일 교체, 다중 프로세스와 여러 호스트의 경쟁까지 안전하게 조정하는 운영 잠금은 아닙니다.

운영의 run 생성은 인증된 호출자, 요청 본문 해시, 멱등성 키, 대상 버전 및 보존 정책을 포함한 데이터베이스 고유 제약 또는 조건부 삽입으로 처리해야 합니다. 실제 배포·삭제·전송에는 승인 소비와 분리된 실행 워커, transaction outbox 및 대상 시스템의 멱등성 보장이 별도로 필요합니다.

## 12. 과제

- **기본:** `checkpoints.json`과 `path-alias/../checkpoints.json`이 하나의 Lock 키가 되는 단계를 설명합니다.
- **응용:** 별칭 인스턴스의 동시 시작 뒤 하나의 승인 대기만 남는 계약 테스트를 확장합니다.
- **심화:** 다중 프로세스의 run 생성과 위험 실행을 위한 데이터베이스 제약·트랜잭션·outbox 설계를 작성합니다. 외부 저장소나 배포는 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] 서로 다른 경로 표기와 정규화된 파일 식별자를 구분할 수 있다.
- [ ] 정규화 뒤 같은 경로의 독립 인스턴스가 Lock을 공유함을 확인했다.
- [ ] 동시 시작 중 하나만 `WAITING_FOR_APPROVAL`을 기록함을 확인했다.
- [ ] 충돌 요청이 승인 대기 Checkpoint와 감사 이벤트를 바꾸지 않음을 확인했다.
- [ ] 엄격한 별도 Boolean 승인 전에는 `execute`가 없음을 확인했다.
- [ ] 예제, 테스트, 정적 검사를 오프라인으로 통과시켰다.

## 14. 핵심 정리

`JsonFileCheckpointer`는 경로 문자열이 아니라 `Path.resolve()`로 정규화한 파일 식별자를 Lock 키로 사용합니다. 따라서 하나의 Python 프로세스에서 `..`를 포함한 서로 다른 로컬 경로 표기도 같은 JSON Checkpoint의 동시 시작을 하나만 기록하게 합니다. 이 참조 모델은 실제 위험 작업이나 다중 프로세스 exactly-once 보장을 제공하지 않으므로, 운영 환경에는 인증·트랜잭션·멱등성·분리된 실행 경계가 필요합니다.
